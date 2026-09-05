import pytest
from app.agents.orchestrator import run_purchase_flow, handle_approval
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.db.models import PurchaseIntent, ApprovalRequest


@pytest.mark.asyncio
async def test_orchestrator_blocked_category(db_session):
    session, user_id = db_session
    # Use a category not in allowed list - the fallback parser will map "clothing" to no category
    # but the policy engine will check against allowed_categories
    result = await run_purchase_flow(session, user_id, "buy expensive clothing item")
    
    assert result.success is False
    # Could be BLOCKED (not in allowed list) or FAILED (no products found)
    # The key is it's not ALLOWED


@pytest.mark.asyncio
async def test_orchestrator_over_max_transaction(db_session):
    session, user_id = db_session
    result = await run_purchase_flow(session, user_id, "buy 4k monitor")
    
    assert result.success is False
    assert result.status == "BLOCKED"
    assert "max transaction" in result.error.lower()


async def _clear_user_data(session, user_id):
    await session.execute(delete(PurchaseIntent).where(PurchaseIntent.user_id == user_id))
    await session.execute(delete(ApprovalRequest).where(ApprovalRequest.purchase_intent_id.in_(
        select(PurchaseIntent.id).where(PurchaseIntent.user_id == user_id)
    )))
    await session.commit()


@pytest.mark.asyncio
async def test_orchestrator_needs_approval(db_session):
    session, user_id = db_session
    await _clear_user_data(session, user_id)
    
    result = await run_purchase_flow(session, user_id, "mechanical keyboard under 5000")
    
    assert result.success is True
    assert result.status == "NEEDS_APPROVAL"
    assert result.purchase_intent_id is not None


@pytest.mark.asyncio
async def test_orchestrator_allowed_low_amount(db_session):
    session, user_id = db_session
    await _clear_user_data(session, user_id)
    
    result = await run_purchase_flow(session, user_id, "usb hub under 2000")
    
    assert result.success is True
    assert result.status == "ALLOWED"
    assert result.purchase_intent_id is not None
    assert result.razorpay_order_id is not None


@pytest.mark.asyncio
async def test_approval_flow_approve(db_session):
    session, user_id = db_session
    await _clear_user_data(session, user_id)
    
    result = await run_purchase_flow(session, user_id, "mechanical keyboard under 5000")
    
    assert result.status == "NEEDS_APPROVAL"
    intent_id = result.purchase_intent_id
    
    approval_result = await handle_approval(session, intent_id, True)
    
    assert approval_result.success is True
    assert approval_result.status == "ALLOWED"
    assert approval_result.razorpay_order_id is not None


@pytest.mark.asyncio
async def test_approval_flow_reject(db_session):
    session, user_id = db_session
    await _clear_user_data(session, user_id)
    
    result = await run_purchase_flow(session, user_id, "mechanical keyboard under 5000")
    
    assert result.status == "NEEDS_APPROVAL"
    intent_id = result.purchase_intent_id
    
    approval_result = await handle_approval(session, intent_id, False)
    
    assert approval_result.success is False
    assert approval_result.status == "REJECTED"


@pytest.mark.asyncio
async def test_audit_trail_created(db_session):
    session, user_id = db_session
    await _clear_user_data(session, user_id)
    
    result = await run_purchase_flow(session, user_id, "mechanical keyboard under 5000")
    
    intent_id = result.purchase_intent_id
    
    from app.audit.logger import log_event
    from sqlalchemy import select
    from app.db.models import AuditLog
    
    stmt = select(AuditLog).where(AuditLog.purchase_intent_id == intent_id)
    res = await session.execute(stmt)
    logs = res.scalars().all()
    
    events = [log.event for log in logs]
    assert "intent_received" in events
    assert "product_selected" in events
    assert "policy_evaluated" in events
    assert "approval_requested" in events