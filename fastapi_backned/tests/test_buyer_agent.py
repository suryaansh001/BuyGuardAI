import pytest
import httpx
from app.agents.buyer_agent import run_buyer_agent, _fallback_buyer_agent
from app.agents.tools import PurchaseConstraints
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_fallback_buyer_agent_selects_product(db_session):
    session, user_id = db_session
    result = await _fallback_buyer_agent(
        session,
        user_id=user_id,
        constraints=PurchaseConstraints(
            category="Electronics",
            max_price=500000,
            max_delivery_days=4,
            keywords="keyboard",
            quantity=1,
        ),
    )
    
    assert result["success"] is True
    assert "purchase_intent_id" in result
    assert "reasoning" in result
    assert len(result["reasoning"]) > 0


@pytest.mark.asyncio
async def test_fallback_buyer_agent_books(db_session):
    session, user_id = db_session
    result = await _fallback_buyer_agent(
        session,
        user_id=user_id,
        constraints=PurchaseConstraints(
            category="Books",
            max_price=60000,
            keywords="clean code",
            quantity=1,
        ),
    )
    
    assert result["success"] is True
    assert "purchase_intent_id" in result


@pytest.mark.asyncio
async def test_fallback_buyer_agent_no_match(db_session):
    session, user_id = db_session
    result = await _fallback_buyer_agent(
        session,
        user_id=user_id,
        constraints=PurchaseConstraints(
            category="Electronics",
            max_price=1000,
            quantity=1,
        ),
    )
    
    assert result["success"] is False
    assert "No products found" in result["error"]


@pytest.mark.asyncio
async def test_run_buyer_agent_falls_back_on_ollama_timeout(db_session, monkeypatch):
    session, user_id = db_session

    async def raise_timeout(*args, **kwargs):
        request = httpx.Request("POST", "http://localhost:11434/api/chat")
        raise httpx.ReadTimeout("timeout", request=request)

    monkeypatch.setattr("app.agents.ollama_client.run_buyer_agent_ollama", raise_timeout)

    result = await run_buyer_agent(
        session,
        user_id=user_id,
        constraints=PurchaseConstraints(
            category="Electronics",
            max_price=500000,
            max_delivery_days=4,
            keywords="keyboard",
            quantity=1,
        ),
    )

    assert result["success"] is True
    assert "purchase_intent_id" in result


def test_buyer_agent_no_money_imports():
    import app.agents.buyer_agent as ba
    import inspect
    
    source = inspect.getsource(ba)
    assert "razorpay_service" not in source
    assert "policy.engine" not in source
    assert "create_razorpay_order" not in source
    assert "evaluate" not in source


def test_ollama_tool_arguments_are_normalized():
    from app.agents.ollama_client import _filter_tool_arguments, _normalize_tool_arguments
    from app.agents.tools import search_catalog_tool

    raw_arguments = {"object": {"category": "Electronics", "keywords": "keyboard", "limit": 5, "unexpected": "ignore"}}

    normalized = _normalize_tool_arguments(raw_arguments)
    filtered = _filter_tool_arguments(search_catalog_tool, normalized)

    assert normalized == raw_arguments["object"]
    assert filtered == {"category": "Electronics", "keywords": "keyboard", "limit": 5}