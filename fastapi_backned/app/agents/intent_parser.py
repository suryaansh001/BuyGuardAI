import json
import re

from groq import Groq

from app.agents.tools import PurchaseConstraints
from app.core.config import settings


INTENT_PARSER_SYSTEM_PROMPT = """You are an intent extraction system.

Your ONLY task is to extract purchasing constraints from the user's request.

Return ONLY a valid JSON object.
Do not return markdown.
Do not return ```json.
Do not explain anything.
Do not add any text before or after the JSON.

Use exactly this structure:

{
    "product": string or null,
    "category": string or null,
    "budget_min": number or null,
    "budget_max": number or null,
    "brand": string or null,
    "requirements": array of strings,
    "preferences": array of strings
}

Rules:
- If a value is not specified, use null.
- If there are no requirements, return [].
- If there are no preferences, return [].
- Convert prices such as ₹80k, 80K, 80,000 into 80000.
- Do not invent information.
- Preserve important user requirements.
- Return valid JSON only.
"""


def _to_paise(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value * 100)
    if isinstance(value, str):
        cleaned = value.replace(",", "").strip().lower()
        if cleaned.startswith("₹"):
            cleaned = cleaned[1:].strip()
        if cleaned.endswith("k"):
            return int(float(cleaned[:-1]) * 1000 * 100)
        return int(float(cleaned) * 100)
    return None


def _extract_delivery_days(user_text: str):
    match = re.search(r"(?:within|in|under)\s*(\d+)\s*days?", user_text.lower())
    return int(match.group(1)) if match else None


def _compose_keywords(data: dict, fallback_text: str) -> str:
    parts = []
    product = data.get("product")
    brand = data.get("brand")
    requirements = data.get("requirements") or []
    preferences = data.get("preferences") or []

    if isinstance(product, str) and product.strip():
        parts.append(product.strip())
    if isinstance(brand, str) and brand.strip():
        parts.append(brand.strip())
    for item in requirements:
        if isinstance(item, str) and item.strip():
            parts.append(item.strip())
    for item in preferences:
        if isinstance(item, str) and item.strip():
            parts.append(item.strip())

    if not parts:
        return fallback_text

    return " ".join(parts)


def _normalize_category(data: dict, user_text: str):
    groq_category = data.get("category")
    if isinstance(groq_category, str):
        normalized = groq_category.strip().lower()
        category_aliases = {
            "electronics": "Electronics",
            "electronic": "Electronics",
            "books": "Books",
            "book": "Books",
            "office supplies": "Office supplies",
            "office": "Office supplies",
            "stationery": "Office supplies",
        }
        if normalized in category_aliases:
            return category_aliases[normalized]

    return _fallback_parse(user_text).category


def _build_purchase_constraints(data: dict, user_text: str) -> PurchaseConstraints:
    return PurchaseConstraints(
        category=_normalize_category(data, user_text),
        max_price=_to_paise(data.get("budget_max")),
        min_price=_to_paise(data.get("budget_min")),
        keywords=_compose_keywords(data, user_text),
        max_delivery_days=_extract_delivery_days(user_text),
    )


def _call_groq_intent_parser(user_text: str) -> dict:
    client = Groq(api_key=settings.GROQ_API_KEY)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": """
You are an intent extraction system.

Your ONLY task is to extract purchasing constraints from the user's request.

Return ONLY a valid JSON object.
Do not return markdown.
Do not return ```json.
Do not explain anything.
Do not add any text before or after the JSON.

Use exactly this structure:

{
    "product": string or null,
    "category": string or null,
    "budget_min": number or null,
    "budget_max": number or null,
    "brand": string or null,
    "requirements": array of strings,
    "preferences": array of strings
}

Rules:
- If a value is not specified, use null.
- If there are no requirements, return [].
- If there are no preferences, return [].
- Convert prices such as ₹80k, 80K, 80,000 into 80000.
- Do not invent information.
- Preserve important user requirements.
- Return valid JSON only.
"""
            },
            {
                "role": "user",
                "content": user_text
            }
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("Groq intent parser returned an empty response")

    return json.loads(content)


async def parse_intent(user_text: str) -> PurchaseConstraints:
    try:
        if not settings.GROQ_API_KEY:
            return _fallback_parse(user_text)

        data = _call_groq_intent_parser(user_text)
        return _build_purchase_constraints(data, user_text)

    except Exception as e:
        return _fallback_parse(user_text)


def _fallback_parse(user_text: str) -> PurchaseConstraints:
    text = user_text.lower()
    
    category = None
    if any(c in text for c in ["electronic", "keyboard", "mouse", "monitor", "webcam", "hub"]):
        category = "Electronics"
    elif any(c in text for c in ["notebook", "pen", "office", "stationery"]):
        category = "Office supplies"
    elif any(c in text for c in ["book", "novel", "read"]):
        category = "Books"
    
    max_price = None
    import re
    price_match = re.search(r"(?:under|below|less than|max|maximum)\s*[₹$]?\s*(\d+(?:,\d+)?)", text)
    if price_match:
        price_str = price_match.group(1).replace(",", "")
        max_price = int(float(price_str) * 100)
    
    max_delivery_days = None
    delivery_match = re.search(r"(?:within|in|under)\s*(\d+)\s*days?", text)
    if delivery_match:
        max_delivery_days = int(delivery_match.group(1))
    
    keywords = user_text
    
    return PurchaseConstraints(
        category=category,
        max_price=max_price,
        max_delivery_days=max_delivery_days,
        keywords=keywords,
    )