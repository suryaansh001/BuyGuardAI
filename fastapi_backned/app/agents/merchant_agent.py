from typing import Optional
from groq import Groq
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools import (
    ToolResult,
    get_pricing_tier_tool,
    check_negotiation_floor_tool,
    get_merchant_policy_tool,
)
from app.core.config import settings


MERCHANT_AGENT_SYSTEM_PROMPT = """You are a merchant agent handling bulk pricing and negotiation requests.
You have access to these tools:
1. get_pricing_tier - Get the unit price for a specific quantity (deterministic lookup from tier table)
2. check_negotiation_floor - Check if an offered price meets the minimum negotiation floor
3. get_merchant_policy - Get merchant's negotiation policies

Your job: 
- Given a product and requested quantity, call get_pricing_tier to get the correct tier price
- You CANNOT invent prices - you must use the tier table
- If the buyer offers a price, check it against the negotiation floor
- Respond with the tier price or floor price, never your own number

You must call get_pricing_tier for every negotiation request."""


MERCHANT_AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_pricing_tier",
            "description": "Get the unit price for a specific quantity from the tier table",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "Product ID"},
                    "quantity": {"type": "integer", "description": "Requested quantity"},
                },
                "required": ["product_id", "quantity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_negotiation_floor",
            "description": "Check if an offered price meets the negotiation floor",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "Product ID"},
                    "offered_price": {"type": "integer", "description": "Offered unit price in paise"},
                },
                "required": ["product_id", "offered_price"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_merchant_policy",
            "description": "Get merchant's negotiation policies",
            "parameters": {
                "type": "object",
                "properties": {
                    "merchant_id": {"type": "integer", "description": "Merchant ID"},
                },
                "required": ["merchant_id"],
            },
        },
    },
]


TOOL_MAP = {
    "get_pricing_tier": get_pricing_tier_tool,
    "check_negotiation_floor": check_negotiation_floor_tool,
    "get_merchant_policy": get_merchant_policy_tool,
}


async def run_merchant_agent(
    session: AsyncSession,
    product_id: int,
    quantity: int,
    offered_price: Optional[int] = None,
) -> dict:
    # Use fallback by default since Groq models don't reliably support tool calling
    return await _fallback_merchant_agent(session, product_id, quantity, offered_price)


async def _fallback_merchant_agent(
    session: AsyncSession,
    product_id: int,
    quantity: int,
    offered_price: Optional[int] = None,
) -> dict:
    # Get pricing tier
    tier_result = await get_pricing_tier_tool(session, product_id, quantity)
    if not tier_result.success:
        return {"success": False, "error": tier_result.error}
    
    unit_price = tier_result.data["unit_price"]
    
    # Check negotiation floor if offered price provided
    if offered_price is not None:
        floor_result = await check_negotiation_floor_tool(session, product_id, offered_price)
        if floor_result.success and not floor_result.data["allowed"]:
            return {
                "success": True,
                "unit_price": floor_result.data["floor_price"],
                "quantity": quantity,
                "countered": True,
                "message": f"Price below negotiation floor. Minimum is ₹{floor_result.data['floor_price']/100:.0f}",
            }
    
    return {
        "success": True,
        "unit_price": unit_price,
        "quantity": quantity,
        "countered": False,
    }