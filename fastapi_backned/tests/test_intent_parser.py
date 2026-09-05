import pytest
from app.agents.intent_parser import parse_intent, _fallback_parse
from app.agents.tools import PurchaseConstraints


def test_fallback_parse_mechanical_keyboard():
    result = _fallback_parse("a mechanical keyboard for programming under ₹5000, arriving within 4 days")
    
    assert result.category == "Electronics"
    assert result.max_price == 500000
    assert result.max_delivery_days == 4
    assert "mechanical keyboard" in result.keywords.lower()


def test_fallback_parse_book():
    result = _fallback_parse("clean code book under ₹500")
    
    assert result.category == "Books"
    assert result.max_price == 50000


def test_fallback_parse_office_supplies():
    result = _fallback_parse("notebook and pens for office")
    
    assert result.category == "Office supplies"


def test_fallback_parse_no_category():
    result = _fallback_parse("something cheap under ₹1000")
    
    assert result.category is None
    assert result.max_price == 100000


def test_fallback_parse_quantity():
    result = _fallback_parse("2 mechanical keyboards")
    
    assert result.quantity == 1


@pytest.mark.skipif(
    True, 
    reason="Requires Groq API key - run manually with valid key"
)
def test_groq_parse_integration():
    result = parse_intent("a mechanical keyboard for programming under ₹5000, arriving within 4 days")
    
    assert isinstance(result, PurchaseConstraints)
    assert result.category == "Electronics"
    assert result.max_price == 500000
    assert result.max_delivery_days == 4


def test_purchase_constraints_model():
    constraints = PurchaseConstraints(
        category="Electronics",
        max_price=500000,
        keywords="mechanical keyboard",
        max_delivery_days=4,
        quantity=1,
    )
    
    assert constraints.category == "Electronics"
    assert constraints.max_price == 500000
    assert constraints.max_delivery_days == 4