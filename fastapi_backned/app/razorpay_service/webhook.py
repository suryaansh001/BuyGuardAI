from dataclasses import dataclass
from typing import Optional
import hmac
import hashlib
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.models import (
    Transaction, TransactionStatus,
    Payment, PaymentStatus,
    PurchaseIntent, PurchaseIntentStatus,
    AuditLog,
)
from app.audit.logger import log_event


@dataclass
class WebhookResult:
    success: bool
    error: Optional[str] = None


async def handle_webhook(
    session: AsyncSession,
    payload: dict,
    signature: Optional[str],
) -> WebhookResult:
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        return WebhookResult(success=False, error="Webhook secret not configured")
    
    if not signature:
        return WebhookResult(success=False, error="Missing signature")
    
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
    expected_signature = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode(),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    
    if not hmac.compare_digest(expected_signature, signature):
        return WebhookResult(success=False, error="Invalid signature")
    
    event = payload.get("event")
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    
    razorpay_payment_id = payment_entity.get("id")
    razorpay_order_id = payment_entity.get("order_id")
    payment_status = payment_entity.get("status")
    payment_method = payment_entity.get("method")
    
    if not razorpay_payment_id or not razorpay_order_id:
        return WebhookResult(success=False, error="Missing payment/order ID in payload")
    
    stmt = select(Transaction).where(Transaction.razorpay_order_id == razorpay_order_id)
    result = await session.execute(stmt)
    transaction = result.scalar_one_or_none()
    
    if not transaction:
        return WebhookResult(success=False, error="Transaction not found")
    
    existing_payment = await session.execute(
        select(Payment).where(Payment.razorpay_payment_id == razorpay_payment_id)
    )
    if existing_payment.scalar_one_or_none():
        return WebhookResult(success=True, error="Duplicate payment ignored")
    
    payment = Payment(
        transaction_id=transaction.id,
        razorpay_payment_id=razorpay_payment_id,
        status=PaymentStatus.CAPTURED if payment_status == "captured" else PaymentStatus.FAILED,
        method=payment_method,
        raw_webhook_payload=payload,
    )
    session.add(payment)
    
    if payment_status == "captured":
        transaction.status = TransactionStatus.PAID
        
        intent = await session.get(PurchaseIntent, transaction.purchase_intent_id)
        if intent:
            intent.status = PurchaseIntentStatus.PAID
        
        await log_event(
            session=session,
            purchase_intent_id=transaction.purchase_intent_id,
            actor="system",
            event="payment_webhook_received",
            payload={"payment_id": razorpay_payment_id, "status": "captured"},
        )
        
        await log_event(
            session=session,
            purchase_intent_id=transaction.purchase_intent_id,
            actor="system",
            event="order_confirmed",
            payload={"transaction_id": transaction.id},
        )
    else:
        transaction.status = TransactionStatus.FAILED
        
        intent = await session.get(PurchaseIntent, transaction.purchase_intent_id)
        if intent:
            intent.status = PurchaseIntentStatus.FAILED
        
        await log_event(
            session=session,
            purchase_intent_id=transaction.purchase_intent_id,
            actor="system",
            event="payment_webhook_received",
            payload={"payment_id": razorpay_payment_id, "status": "failed"},
        )
    
    await session.commit()
    
    return WebhookResult(success=True)