from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_db
from app.db.models import (
    Transaction, TransactionStatus,
    Payment, PaymentStatus,
    PurchaseIntent, PurchaseIntentStatus,
    AuditLog,
)
from app.razorpay_service.client import verify_payment_signature
from app.razorpay_service.webhook import handle_webhook
from app.audit.logger import log_event


router = APIRouter(prefix="/api/payments", tags=["payments"])


class CreateOrderRequest(BaseModel):
    purchase_intent_id: int


class CreateOrderResponse(BaseModel):
    success: bool
    razorpay_order_id: str | None = None
    amount: int | None = None
    currency: str | None = None
    key_id: str | None = None
    error: str | None = None


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


@router.post("/purchase-intents/{purchase_intent_id}/pay/create-order", response_model=CreateOrderResponse)
async def create_order(
    purchase_intent_id: int,
    db: AsyncSession = Depends(get_db),
):
    from app.razorpay_service.client import create_razorpay_order
    from app.core.config import settings
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    
    stmt = select(PurchaseIntent).options(
        selectinload(PurchaseIntent.product)
    ).where(PurchaseIntent.id == purchase_intent_id)
    result = await db.execute(stmt)
    intent = result.scalar_one_or_none()
    
    if not intent:
        raise HTTPException(status_code=404, detail="Purchase intent not found")
    
    if intent.status not in [PurchaseIntentStatus.ALLOWED, PurchaseIntentStatus.APPROVED]:
        raise HTTPException(status_code=400, detail="Purchase intent not in payable state")
    
    # Check if transaction already exists
    txn_stmt = select(Transaction).where(Transaction.purchase_intent_id == purchase_intent_id)
    txn_result = await db.execute(txn_stmt)
    existing_txn = txn_result.scalar_one_or_none()
    
    if existing_txn:
        return CreateOrderResponse(
            success=True,
            razorpay_order_id=existing_txn.razorpay_order_id,
            amount=existing_txn.amount,
            currency=existing_txn.currency,
            key_id=settings.RAZORPAY_KEY_ID,
        )
    
    currency = intent.product.currency if intent.product else "INR"
    result = await create_razorpay_order(db, intent.amount, currency)
    
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    
    transaction = Transaction(
        purchase_intent_id=purchase_intent_id,
        razorpay_order_id=result.order_id,
        amount=intent.amount,
        currency=currency,
        status=TransactionStatus.CREATED,
    )
    db.add(transaction)
    
    await log_event(
        session=db,
        purchase_intent_id=purchase_intent_id,
        actor="system",
        event="razorpay_order_created",
        payload={"order_id": result.order_id, "amount": intent.amount},
    )
    
    await db.commit()
    
    return CreateOrderResponse(
        success=True,
        razorpay_order_id=result.order_id,
        amount=intent.amount,
        currency=currency,
        key_id=settings.RAZORPAY_KEY_ID,
    )


@router.post("/verify", response_model=dict)
async def verify_payment(
    request: VerifyPaymentRequest,
    db: AsyncSession = Depends(get_db),
):
    is_valid = verify_payment_signature(
        request.razorpay_order_id,
        request.razorpay_payment_id,
        request.razorpay_signature,
    )
    
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid payment signature")
    
    from sqlalchemy import select
    stmt = select(Transaction).where(Transaction.razorpay_order_id == request.razorpay_order_id)
    result = await db.execute(stmt)
    transaction = result.scalar_one_or_none()
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return {"success": True, "message": "Payment verified"}


@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_razorpay_signature: str = Header(None),
):
    payload = await request.json()
    
    result = await handle_webhook(db, payload, x_razorpay_signature)
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    
    return {"success": True}