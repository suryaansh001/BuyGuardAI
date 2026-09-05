from dataclasses import dataclass
from typing import Optional
import razorpay
from app.core.config import settings
import uuid


@dataclass
class RazorpayOrderResult:
    success: bool
    order_id: Optional[str] = None
    error: Optional[str] = None


def _get_razorpay_client():
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        return None
    if settings.RAZORPAY_KEY_ID.startswith("rzp_test_xxxxx"):
        return None
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


async def create_razorpay_order(
    session,
    amount: int,
    currency: str = "INR",
) -> RazorpayOrderResult:
    client = _get_razorpay_client()
    if client is None:
        # Mock mode for testing - generate a fake order ID
        mock_order_id = f"order_mock_{uuid.uuid4().hex[:12]}"
        return RazorpayOrderResult(success=True, order_id=mock_order_id)
    
    try:
        order = client.order.create({
            "amount": amount,
            "currency": currency,
            "payment_capture": 1,
        })
        return RazorpayOrderResult(success=True, order_id=order["id"])
    except Exception as e:
        return RazorpayOrderResult(success=False, error=str(e))


def verify_payment_signature(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
) -> bool:
    client = _get_razorpay_client()
    if client is None:
        # Mock mode - accept any signature for testing
        return True
    
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        })
        return True
    except Exception:
        return False