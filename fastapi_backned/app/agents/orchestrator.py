from dataclasses import dataclass
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.agents.intent_parser import parse_intent
from app.agents.buyer_agent import run_buyer_agent
from app.agents.tools import PurchaseConstraints
from app.policy.engine import evaluate
from app.policy.models import BuyerPolicy, PolicyResult
from app.db.models import (
    User, BuyerPolicy as BuyerPolicyModel,
    PurchaseIntent, PurchaseIntentStatus,
    ApprovalRequest, ApprovalStatus,
    AuditLog, Transaction, TransactionStatus
)
from app.razorpay_service.client import create_razorpay_order
from app.audit.logger import log_event


@dataclass
class OrchestratorResult:
    success: bool
    purchase_intent_id: Optional[int] = None
    status: Optional[str] = None
    error: Optional[str] = None
    razorpay_order_id: Optional[str] = None


async def _get_buyer_policy(session: AsyncSession, user_id: int) -> Optional[BuyerPolicy]:
    stmt = select(BuyerPolicyModel).where(BuyerPolicyModel.user_id == user_id)
    result = await session.execute(stmt)
    policy_model = result.scalar_one_or_none()
    
    if not policy_model:
        return None
    
    return BuyerPolicy(
        max_transaction_amount=policy_model.max_transaction_amount,
        daily_spending_limit=policy_model.daily_spending_limit,
        approval_required_above=policy_model.approval_required_above,
        allowed_categories=set(policy_model.allowed_categories),
        blocked_categories=set(policy_model.blocked_categories),
        allowed_merchant_ids=set(policy_model.allowed_merchant_ids) if policy_model.allowed_merchant_ids else None,
    )


async def _get_spent_today(session: AsyncSession, user_id: int) -> int:
    from datetime import datetime, date
    today = date.today()
    stmt = select(func.coalesce(func.sum(PurchaseIntent.amount), 0)).where(
        PurchaseIntent.user_id == user_id,
        func.date(PurchaseIntent.created_at) == today,
        PurchaseIntent.status.in_([PurchaseIntentStatus.ALLOWED, PurchaseIntentStatus.APPROVED, PurchaseIntentStatus.PAID]),
    )
    result = await session.execute(stmt)
    return result.scalar() or 0


async def _create_approval_request(session: AsyncSession, purchase_intent_id: int) -> ApprovalRequest:
    approval = ApprovalRequest(
        purchase_intent_id=purchase_intent_id,
        status=ApprovalStatus.PENDING,
    )
    session.add(approval)
    await session.flush()
    return approval


async def run_purchase_flow(
    session: AsyncSession,
    user_id: int,
    user_text: str,
) -> OrchestratorResult:
    constraints = await parse_intent(user_text)
    
    buyer_result = await run_buyer_agent(session, user_id, constraints)
    
    if not buyer_result["success"]:
        return OrchestratorResult(
            success=False,
            error=buyer_result.get("error", "Buyer agent failed"),
        )
    
    purchase_intent_id = buyer_result["purchase_intent_id"]
    
    await log_event(
        session=session,
        purchase_intent_id=purchase_intent_id,
        actor="system",
        event="intent_received",
        payload={"raw_text": user_text},
    )
    
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    stmt = select(PurchaseIntent).options(
        selectinload(PurchaseIntent.product),
        selectinload(PurchaseIntent.merchant),
    ).where(PurchaseIntent.id == purchase_intent_id)
    result = await session.execute(stmt)
    intent = result.scalar_one_or_none()
    
    if not intent:
        return OrchestratorResult(success=False, error="Purchase intent not found")
    
    buyer_policy = await _get_buyer_policy(session, user_id)
    if not buyer_policy:
        return OrchestratorResult(success=False, error="No buyer policy found")
    
    spent_today = await _get_spent_today(session, user_id)
    
    policy_eval = evaluate(
        category=intent.product.category if intent.product else "",
        amount=intent.amount,
        merchant_id=intent.merchant_id,
        spent_today=spent_today,
        policy=buyer_policy,
    )
    
    intent.status = PurchaseIntentStatus.POLICY_CHECKED
    intent.policy_reason = policy_eval.reason
    await session.flush()
    
    await log_event(
        session=session,
        purchase_intent_id=purchase_intent_id,
        actor="policy_engine",
        event="policy_evaluated",
        payload={"rule": policy_eval.result.value, "reason": policy_eval.reason},
    )
    
    if policy_eval.result == PolicyResult.BLOCKED:
        intent.status = PurchaseIntentStatus.BLOCKED
        await session.commit()
        return OrchestratorResult(
            success=False,
            purchase_intent_id=purchase_intent_id,
            status="BLOCKED",
            error=policy_eval.reason,
        )
    
    if policy_eval.result == PolicyResult.NEEDS_APPROVAL:
        intent.status = PurchaseIntentStatus.NEEDS_APPROVAL
        await _create_approval_request(session, purchase_intent_id)
        await log_event(
            session=session,
            purchase_intent_id=purchase_intent_id,
            actor="human",
            event="approval_requested",
            payload={"threshold": buyer_policy.approval_required_above, "amount": intent.amount},
        )
        await session.commit()
        return OrchestratorResult(
            success=True,
            purchase_intent_id=purchase_intent_id,
            status="NEEDS_APPROVAL",
        )
    
    intent.status = PurchaseIntentStatus.ALLOWED
    await session.flush()
    
    currency = intent.product.currency if intent.product else "INR"
    razorpay_result = await create_razorpay_order(session, intent.amount, currency)
    
    if not razorpay_result.success:
        intent.status = PurchaseIntentStatus.FAILED
        await session.commit()
        return OrchestratorResult(
            success=False,
            purchase_intent_id=purchase_intent_id,
            status="FAILED",
            error=razorpay_result.error,
        )
    
    transaction = Transaction(
        purchase_intent_id=purchase_intent_id,
        razorpay_order_id=razorpay_result.order_id,
        amount=intent.amount,
        currency=currency,
        status=TransactionStatus.CREATED,
    )
    session.add(transaction)
    await session.flush()
    
    await log_event(
        session=session,
        purchase_intent_id=purchase_intent_id,
        actor="system",
        event="razorpay_order_created",
        payload={"order_id": razorpay_result.order_id, "amount": intent.amount},
    )
    
    await session.commit()
    
    return OrchestratorResult(
        success=True,
        purchase_intent_id=purchase_intent_id,
        status="ALLOWED",
        razorpay_order_id=razorpay_result.order_id,
    )


async def handle_approval(
    session: AsyncSession,
    purchase_intent_id: int,
    approve: bool,
) -> OrchestratorResult:
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    stmt = select(PurchaseIntent).options(
        selectinload(PurchaseIntent.product),
        selectinload(PurchaseIntent.merchant),
    ).where(PurchaseIntent.id == purchase_intent_id)
    result = await session.execute(stmt)
    intent = result.scalar_one_or_none()
    if not intent:
        return OrchestratorResult(success=False, error="Purchase intent not found")
    
    from sqlalchemy import select
    approval_stmt = select(ApprovalRequest).where(ApprovalRequest.purchase_intent_id == purchase_intent_id)
    approval_result = await session.execute(approval_stmt)
    approval = approval_result.scalar_one_or_none()
    
    if not approval or approval.status != ApprovalStatus.PENDING:
        return OrchestratorResult(success=False, error="No pending approval request")
    
    if approve:
        approval.status = ApprovalStatus.APPROVED
        approval.resolved_at = func.now()
        intent.status = PurchaseIntentStatus.APPROVED
        
        await log_event(
            session=session,
            purchase_intent_id=purchase_intent_id,
            actor="human",
            event="approval_resolved",
            payload={"decision": "APPROVED"},
        )
        
        razorpay_result = await create_razorpay_order(session, intent.amount, intent.product.currency if intent.product else "INR")
        
        if not razorpay_result.success:
            intent.status = PurchaseIntentStatus.FAILED
            await session.commit()
            return OrchestratorResult(
                success=False,
                purchase_intent_id=purchase_intent_id,
                status="FAILED",
                error=razorpay_result.error,
            )
        
        transaction = Transaction(
            purchase_intent_id=purchase_intent_id,
            razorpay_order_id=razorpay_result.order_id,
            amount=intent.amount,
            currency=intent.product.currency if intent.product else "INR",
            status=TransactionStatus.CREATED,
        )
        session.add(transaction)
        
        await log_event(
            session=session,
            purchase_intent_id=purchase_intent_id,
            actor="system",
            event="razorpay_order_created",
            payload={"order_id": razorpay_result.order_id, "amount": intent.amount},
        )
        
        await session.commit()
        
        return OrchestratorResult(
            success=True,
            purchase_intent_id=purchase_intent_id,
            status="ALLOWED",
            razorpay_order_id=razorpay_result.order_id,
        )
    else:
        approval.status = ApprovalStatus.REJECTED
        approval.resolved_at = func.now()
        intent.status = PurchaseIntentStatus.REJECTED
        
        await log_event(
            session=session,
            purchase_intent_id=purchase_intent_id,
            actor="human",
            event="approval_resolved",
            payload={"decision": "REJECTED"},
        )
        
        await session.commit()
        
        return OrchestratorResult(
            success=False,
            purchase_intent_id=purchase_intent_id,
            status="REJECTED",
            error="Approval rejected",
        )