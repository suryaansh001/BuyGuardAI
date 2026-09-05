from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.tools import (
    PurchaseConstraints,
    ToolResult,
    search_catalog_tool,
    get_product_detail_tool,
    compare_products_tool,
    propose_purchase_tool,
    request_negotiation_tool,
)


BUYER_AGENT_SYSTEM_PROMPT = """You are a buyer agent helping a user find and purchase products.
You have access to these tools:
1. search_catalog - Search for products by category, price, delivery days, keywords
2. get_product_detail - Get detailed info about a specific product
3. compare_products - Compare multiple products side by side
4. propose_purchase - Create a purchase intent (DRAFT) with your reasoning
5. request_negotiation - Request bulk pricing negotiation

Your goal: Help the user find the best product matching their constraints, then propose a purchase.

CRITICAL RULES - YOU MUST FOLLOW THESE EXACTLY:
1. You MUST call search_catalog first to find products matching the user's constraints.
2. After getting search results, you MUST call propose_purchase with your final selection and reasoning.
3. You MUST call propose_purchase EXACTLY ONCE with your final selection and reasoning.
4. Do NOT call propose_purchase more than once.
5. Stop after proposing a purchase.
6. You MUST use the propose_purchase tool - do not just respond with text describing the product.
7. When you have found a suitable product, you MUST call the propose_purchase tool with:
   - product_id: the ID of the selected product
   - quantity: the quantity to purchase
   - reasoning: your explanation for why this product was selected

YOUR RESPONSE MUST BE A TOOL CALL, NOT TEXT. If you have found a suitable product, YOU MUST CALL THE propose_purchase TOOL."""


BUYER_AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_catalog",
            "description": "Search catalog for products matching constraints",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Product category"},
                    "max_price": {"type": "integer", "description": "Max price in paise"},
                    "min_price": {"type": "integer", "description": "Min price in paise"},
                    "max_delivery_days": {"type": "integer", "description": "Max delivery days"},
                    "merchant_id": {"type": "integer", "description": "Specific merchant ID"},
                    "keywords": {"type": "string", "description": "Search keywords"},
                    "limit": {"type": "integer", "default": 20},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_detail",
            "description": "Get detailed information about a product",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "Product ID"},
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_products",
            "description": "Compare multiple products side by side",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_ids": {"type": "array", "items": {"type": "integer"}, "description": "Product IDs to compare"},
                },
                "required": ["product_ids"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_purchase",
            "description": "Propose a purchase - creates purchase intent in DRAFT. Call this ONCE with final selection.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "Product ID to purchase"},
                    "quantity": {"type": "integer", "description": "Quantity to purchase"},
                    "reasoning": {"type": "string", "description": "Why this product was selected"},
                },
                "required": ["product_id", "quantity", "reasoning"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_negotiation",
            "description": "Request bulk pricing negotiation",
            "parameters": {
                "type": "object",
                "properties": {
                    "purchase_intent_id": {"type": "integer", "description": "Purchase intent ID"},
                    "requested_qty": {"type": "integer", "description": "Quantity for negotiation"},
                },
                "required": ["purchase_intent_id", "requested_qty"],
            },
        },
    },
]


async def run_buyer_agent(
    session: AsyncSession,
    user_id: int,
    constraints: PurchaseConstraints,
    max_iterations: int = 5,
) -> dict:
    from app.agents.ollama_client import fallback_buyer_agent

    return await fallback_buyer_agent(session, user_id, constraints)


async def _fallback_buyer_agent(
    session: AsyncSession,
    user_id: int,
    constraints: PurchaseConstraints,
) -> dict:
    from app.agents.ollama_client import fallback_buyer_agent
    return await fallback_buyer_agent(session, user_id, constraints)