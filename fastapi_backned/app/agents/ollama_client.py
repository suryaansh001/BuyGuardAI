import json
import inspect
import httpx
from typing import Optional, Dict, Any, List
from app.core.config import settings


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=120.0)

    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        format_json: bool = False,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/chat"
        
        data = {
            "model": model,
            "messages": messages,
            "stream": False,
            "temperature": temperature,
        }
        
        if tools:
            data["tools"] = tools
        if tool_choice:
            data["tool_choice"] = tool_choice
        if format_json:
            data["format"] = "json"
        
        response = await self.client.post(url, json=data)
        response.raise_for_status()
        return response.json()

    async def close(self):
        await self.client.aclose()


async def get_ollama_client() -> OllamaClient:
    return OllamaClient()


def _normalize_tool_arguments(tool_args: Any) -> Any:
    if isinstance(tool_args, str):
        tool_args = json.loads(tool_args)

    if isinstance(tool_args, dict):
        # Handle common LLM tool call formats
        if set(tool_args.keys()) == {"object"} and isinstance(tool_args["object"], dict):
            tool_args = tool_args["object"]
        elif set(tool_args.keys()) == {"arguments"} and isinstance(tool_args["arguments"], dict):
            tool_args = tool_args["arguments"]
        # Handle case where args are wrapped in "object" key with nested dict
        elif "object" in tool_args and isinstance(tool_args["object"], dict):
            tool_args = tool_args["object"]
        elif "arguments" in tool_args and isinstance(tool_args["arguments"], dict):
            tool_args = tool_args["arguments"]

    return tool_args


def _filter_tool_arguments(tool_fn, tool_args: Any) -> Dict[str, Any]:
    if tool_fn is None or not isinstance(tool_args, dict):
        return tool_args

    signature = inspect.signature(tool_fn)
    allowed_names = {
        parameter.name
        for parameter in signature.parameters.values()
        if parameter.name != "session"
        and parameter.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    }
    return {key: value for key, value in tool_args.items() if key in allowed_names}


async def create_ollama_intent_parser(user_text: str) -> dict:
    client = await get_ollama_client()
    try:
        response = await client.chat_completion(
            model="llama3.2:latest",
            messages=[
                {"role": "system", "content": """You are an intent parser for an AI commerce agent. 
Parse the user's natural language purchase request into structured constraints.

Extract these fields:
- category: One of "Electronics", "Books", "Office supplies" (or null if not specified)
- max_price: Maximum price in paise (1 INR = 100 paise). Convert from rupees if mentioned.
- min_price: Minimum price in paise (optional)
- keywords: Search keywords from the request
- max_delivery_days: Maximum delivery time in days (optional)
- quantity: Number of units (default 1)

Rules:
- If user says "under ₹5000", max_price = 500000 (paise)
- If user says "within 4 days", max_delivery_days = 4
- If category not mentioned, set to null
- Return ONLY the JSON object, no extra text."""},
                {"role": "user", "content": user_text},
            ],
            temperature=0,
            format_json=True,
            max_tokens=500,
        )
        
        content = response["message"]["content"]
        data = json.loads(content)
        
        # Handle keywords as list or string
        if isinstance(data.get("keywords"), list):
            data["keywords"] = " ".join(data["keywords"])
        
        return data
    except Exception as e:
        raise RuntimeError(f"Intent parsing failed: {e}")
    finally:
        await client.close()


async def run_buyer_agent_ollama(
    session,
    user_id: int,
    constraints,
    max_iterations: int = 5,
) -> dict:
    from app.agents.tools import (
        search_catalog_tool, get_product_detail_tool, compare_products_tool,
        propose_purchase_tool, request_negotiation_tool, ToolResult
    )
    from app.agents.buyer_agent import BUYER_AGENT_SYSTEM_PROMPT, BUYER_AGENT_TOOLS
    
    client = await get_ollama_client()

    try:
        # Convert constraints to dict for the prompt
        constraints_dict = {
            "category": constraints.category,
            "max_price": constraints.max_price,
            "min_price": constraints.min_price,
            "keywords": constraints.keywords,
            "max_delivery_days": constraints.max_delivery_days,
            "quantity": constraints.quantity,
        }

        messages = [
            {"role": "system", "content": BUYER_AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": f"Find and select a product matching these constraints: {json.dumps(constraints_dict)}"},
        ]

        TOOL_MAP = {
            "search_catalog": search_catalog_tool,
            "get_product_detail": get_product_detail_tool,
            "compare_products": compare_products_tool,
            "propose_purchase": propose_purchase_tool,
            "request_negotiation": request_negotiation_tool,
        }

        proposed = False

        for iteration in range(max_iterations):
            response = await client.chat_completion(
                model="llama3.2:latest",
                messages=messages,
                tools=BUYER_AGENT_TOOLS,
                tool_choice="auto",
                temperature=0.1,
                max_tokens=2000,
            )

            message = response["message"]
            messages.append(message)

            if not message.get("tool_calls"):
                if not proposed:
                    messages.append({
                        "role": "user",
                        "content": "You must call propose_purchase with your final selection. Explain your reasoning.",
                    })
                    continue
                break

            for tool_call in message.get("tool_calls", []):
                tool_name = tool_call["function"]["name"]
                if tool_name not in TOOL_MAP:
                    result = ToolResult(success=False, error=f"Unknown tool: {tool_name}")
                    messages.append({
                        "role": "tool",
                        "content": result.model_dump_json(),
                        "tool_call_id": tool_call.get("id", f"call_{iteration}"),
                    })
                    continue

                tool_args = _filter_tool_arguments(
                    TOOL_MAP[tool_name],
                    _normalize_tool_arguments(tool_call["function"]["arguments"]),
                )

                if tool_name == "propose_purchase":
                    tool_args["user_id"] = 1  # Will be overridden by orchestrator
                    proposed = True

                result = await TOOL_MAP[tool_name](session, **tool_args)

                messages.append({
                    "role": "tool",
                    "content": result.model_dump_json(),
                    "tool_call_id": tool_call.get("id", f"call_{iteration}"),
                })

                if tool_name == "propose_purchase" and result.success:
                    return {
                        "success": True,
                        "purchase_intent_id": result.data["purchase_intent_id"],
                        "reasoning": tool_args.get("reasoning", ""),
                    }

        return {"success": False, "error": "Agent did not propose a purchase within iteration limit"}
    finally:
        await client.close()


async def fallback_buyer_agent(
    session,
    user_id: int,
    constraints,
) -> dict:
    """Fallback buyer agent using deterministic logic (no LLM)."""
    from app.agents.tools import search_catalog_tool, compare_products_tool, propose_purchase_tool
    from app.agents.tools import ToolResult
    
    search_result = await search_catalog_tool(
        session=session,
        category=constraints.category,
        max_price=constraints.max_price,
        max_delivery_days=constraints.max_delivery_days,
        keywords=constraints.keywords,
        limit=5,
    )
    
    if not search_result.success or not search_result.data["products"]:
        return {"success": False, "error": "No products found matching constraints"}
    
    products = search_result.data["products"]
    
    if len(products) > 1:
        product_ids = [p["id"] for p in products[:3]]
        compare_result = await compare_products_tool(session, product_ids)
        if compare_result.success:
            comparison = compare_result.data["comparison"]
            comparison.sort(key=lambda x: (x["base_price"], x["delivery_days"]))
            best = comparison[0]
        else:
            best = products[0]
    else:
        best = products[0]
    
    # Use product_id from comparison or id from search results
    product_id = best.get("product_id", best.get("id"))
    merchant_name = best.get('merchant_name', best.get('merchant', 'Unknown Merchant'))
    reasoning = (
        f"Selected '{best['name']}' from {merchant_name} "
        f"at {best['base_price']/100:.0f} with {best['delivery_days']} day delivery. "
        f"Matches category '{constraints.category}' and budget constraints."
    )
    
    propose_result = await propose_purchase_tool(
        session=session,
        user_id=user_id,
        product_id=product_id,
        quantity=constraints.quantity,
        reasoning=reasoning,
    )
    
    if propose_result.success:
        return {
            "success": True,
            "purchase_intent_id": propose_result.data["purchase_intent_id"],
            "reasoning": reasoning,
        }
    
    return {"success": False, "error": propose_result.error}