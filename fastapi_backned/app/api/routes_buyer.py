from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.db.session import get_db
from app.agents.orchestrator import run_purchase_flow, handle_approval
from app.agents.tools import PurchaseConstraints
from app.agents.intent_parser import parse_intent
from app.agents.ollama_client import get_ollama_client


router = APIRouter(prefix="/api", tags=["buyer"])


class IntentRequest(BaseModel):
    text: str


class IntentResponse(BaseModel):
    success: bool
    purchase_intent_id: int | None = None
    status: str | None = None
    error: str | None = None
    razorpay_order_id: str | None = None


class ApprovalRequest(BaseModel):
    approve: bool


class ChatRequest(BaseModel):
    question: str
    productId: Optional[int] = None
    productName: Optional[str] = None
    merchantName: Optional[str] = None
    category: Optional[str] = None
    specs: Optional[Dict[str, Any]] = None
    comparisonProducts: Optional[List[Dict[str, Any]]] = None


class ChatResponse(BaseModel):
    answer: str
    type: Optional[str] = "text"
    metadata: Optional[Dict[str, Any]] = None


@router.post("/intent", response_model=IntentResponse)
async def create_intent(
    request: IntentRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await run_purchase_flow(db, user_id=1, user_text=request.text)
    return IntentResponse(
        success=result.success,
        purchase_intent_id=result.purchase_intent_id,
        status=result.status,
        error=result.error,
        razorpay_order_id=result.razorpay_order_id,
    )


@router.get("/purchase-intents/{intent_id}")
async def get_purchase_intent(
    intent_id: int,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.db.models import PurchaseIntent, Product
    
    stmt = select(PurchaseIntent).options(
        selectinload(PurchaseIntent.product).selectinload(Product.merchant),
        selectinload(PurchaseIntent.merchant)
    ).where(PurchaseIntent.id == intent_id)
    result = await db.execute(stmt)
    intent = result.scalar_one_or_none()
    
    if not intent:
        raise HTTPException(status_code=404, detail="Purchase intent not found")
    
    return {
        "id": intent.id,
        "user_id": intent.user_id,
        "product_id": intent.product_id,
        "merchant_id": intent.merchant_id,
        "quantity": intent.quantity,
        "unit_price": intent.unit_price,
        "amount": intent.amount,
        "status": intent.status.value,
        "reasoning": intent.reasoning,
        "policy_reason": intent.policy_reason,
        "created_at": intent.created_at.isoformat() if intent.created_at else None,
        "product": {
            "id": intent.product.id,
            "name": intent.product.name,
            "merchant": intent.product.merchant.name,
            "category": intent.product.category,
        } if intent.product else None,
        "merchant": {
            "id": intent.merchant.id,
            "name": intent.merchant.name,
        } if intent.merchant else None,
    }


@router.post("/purchase-intents/{intent_id}/approve", response_model=IntentResponse)
async def approve_purchase_intent(
    intent_id: int,
    request: ApprovalRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await handle_approval(db, intent_id, request.approve)
    return IntentResponse(
        success=result.success,
        purchase_intent_id=result.purchase_intent_id,
        status=result.status,
        error=result.error,
        razorpay_order_id=result.razorpay_order_id,
    )

@router.post("/purchase-intents/{intent_id}/reject", response_model=IntentResponse)
async def reject_purchase_intent(
    intent_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await handle_approval(db, intent_id, False)
    return IntentResponse(
        success=result.success,
        purchase_intent_id=result.purchase_intent_id,
        status=result.status,
        error=result.error,
        razorpay_order_id=result.razorpay_order_id,
    )


@router.post("/intent/stream")
async def create_intent_stream(
    request: IntentRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Stream the agent's thinking process as Server-Sent Events (SSE).
    Yields events for each step of the agent's thinking process.
    """
    import json
    from app.agents.intent_parser import parse_intent
    from app.agents.buyer_agent import run_buyer_agent
    from app.agents.orchestrator import _get_buyer_policy, _get_spent_today
    from app.policy.engine import evaluate
    from app.policy.models import PolicyResult
    from app.db.models import PurchaseIntent, PurchaseIntentStatus, ApprovalRequest, ApprovalStatus, AuditLog, Transaction, TransactionStatus
    from app.razorpay_service.client import create_razorpay_order
    from app.audit.logger import log_event
    
    async def event_generator():
        def sse_event(event_type: str, data: dict):
            return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        
        # Step 1: Parse intent
        yield sse_event("thinking", {"step": "parsing", "message": "Parsing user intent..."})
        
        constraints = await parse_intent(request.text)
        
        yield sse_event("thinking", {
            "step": "parsed", 
            "message": f"Parsed intent: {constraints.category or 'any'} under {constraints.max_price/100 if constraints.max_price else 'any'} INR",
            "constraints": {
                "category": constraints.category,
                "max_price": constraints.max_price,
                "max_delivery_days": constraints.max_delivery_days,
                "keywords": constraints.keywords,
                "quantity": constraints.quantity,
            }
        })
        
        # Step 2: Run buyer agent with streaming
        yield sse_event("thinking", {"step": "searching", "message": "Searching catalog for matching products..."})
        
        buyer_result = await run_buyer_agent(db, user_id=1, constraints=constraints)
        
        if not buyer_result["success"]:
            yield sse_event("error", {"message": buyer_result.get("error", "Buyer agent failed")})
            return
        
        purchase_intent_id = buyer_result["purchase_intent_id"]
        
        yield sse_event("thinking", {
            "step": "selected", 
            "message": f"Selected product (intent: {purchase_intent_id})",
            "purchase_intent_id": purchase_intent_id,
        })
        
        await log_event(
            session=db,
            purchase_intent_id=purchase_intent_id,
            actor="system",
            event="intent_received",
            payload={"raw_text": request.text},
        )
        
        # Get intent details
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.db.models import PurchaseIntent
        
        stmt = select(PurchaseIntent).options(
            selectinload(PurchaseIntent.product),
            selectinload(PurchaseIntent.merchant),
        ).where(PurchaseIntent.id == purchase_intent_id)
        result = await db.execute(stmt)
        intent = result.scalar_one_or_none()
        
        if not intent:
            yield sse_event("error", {"message": "Purchase intent not found"})
            return
        
        buyer_policy = await _get_buyer_policy(db, 1)
        if not buyer_policy:
            yield sse_event("error", {"message": "No buyer policy found"})
            return
        
        spent_today = await _get_spent_today(db, 1)
        
        policy_eval = evaluate(
            category=intent.product.category if intent.product else "",
            amount=intent.amount,
            merchant_id=intent.merchant_id,
            spent_today=spent_today,
            policy=buyer_policy,
        )
        
        intent.status = PurchaseIntentStatus.POLICY_CHECKED
        intent.policy_reason = policy_eval.reason
        await db.flush()
        
        await log_event(
            session=db,
            purchase_intent_id=purchase_intent_id,
            actor="policy_engine",
            event="policy_evaluated",
            payload={"rule": policy_eval.result.value, "reason": policy_eval.reason},
        )
        
        if policy_eval.result == PolicyResult.BLOCKED:
            intent.status = PurchaseIntentStatus.BLOCKED
            await db.commit()
            yield sse_event("blocked", {
                "reason": policy_eval.reason,
                "amount": intent.amount,
            })
            return
        
        if policy_eval.result == PolicyResult.NEEDS_APPROVAL:
            intent.status = PurchaseIntentStatus.NEEDS_APPROVAL
            from app.db.models import ApprovalRequest, ApprovalStatus
            approval = ApprovalRequest(
                purchase_intent_id=purchase_intent_id,
                status=ApprovalStatus.PENDING,
            )
            db.add(approval)
            await db.flush()
            
            await log_event(
                session=db,
                purchase_intent_id=purchase_intent_id,
                actor="human",
                event="approval_requested",
                payload={"threshold": buyer_policy.approval_required_above, "amount": intent.amount},
            )
            await db.commit()
            
            yield sse_event("needs_approval", {
                "reason": policy_eval.reason,
                "amount": intent.amount,
                "threshold": buyer_policy.approval_required_above,
                "purchase_intent_id": purchase_intent_id,
            })
            return
        
        intent.status = PurchaseIntentStatus.ALLOWED
        await db.flush()
        
        razorpay_result = await create_razorpay_order(db, intent.amount, intent.currency)
        
        if not razorpay_result.success:
            intent.status = PurchaseIntentStatus.FAILED
            await db.commit()
            yield sse_event("error", {"message": razorpay_result.error})
            return
        
        from app.db.models import Transaction, TransactionStatus
        transaction = Transaction(
            purchase_intent_id=purchase_intent_id,
            razorpay_order_id=razorpay_result.order_id,
            amount=intent.amount,
            currency=intent.currency,
            status=TransactionStatus.CREATED,
        )
        db.add(transaction)
        
        await log_event(
            session=db,
            purchase_intent_id=purchase_intent_id,
            actor="system",
            event="razorpay_order_created",
            payload={"order_id": razorpay_result.order_id, "amount": intent.amount},
        )
        
        await db.commit()
        
        yield sse_event("ready_to_pay", {
            "purchase_intent_id": purchase_intent_id,
            "razorpay_order_id": razorpay_result.order_id,
            "amount": intent.amount,
            "currency": intent.currency,
            "key_id": "rzp_test_xxxxxxxxxxxx",  # This should come from settings
        })
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/chat/agent", response_model=ChatResponse)
async def chat_with_agent(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Chat with AI agent about product features, reviews, comparisons, etc.
    Uses Groq/Ollama with product context to answer questions.
    """
    from app.agents.ollama_client import get_ollama_client
    
    client = await get_ollama_client()
    
    # Build product context
    product_context = ""
    if request.productName:
        product_context += f"Product: {request.productName}\n"
    if request.merchantName:
        product_context += f"Merchant: {request.merchantName}\n"
    if request.category:
        product_context += f"Category: {request.category}\n"
    if request.specs:
        product_context += f"Specifications: {request.specs}\n"
    if request.comparisonProducts:
        product_context += "\nSimilar Products:\n"
        for p in request.comparisonProducts:
            product_context += f"- {p.get('name', '')} from {p.get('merchant', '')} at ₹{p.get('price', 0)/100:.0f} (specs: {p.get('specs', {})})\n"
    
    system_prompt = f"""You are a helpful shopping assistant for Agent Commerce Gateway. 
You have access to product information and can answer questions about features, reviews, comparisons, delivery, warranty, etc.

Current Product Context:
{product_context}

Guidelines:
- Be helpful, concise, and conversational
- If asked about reviews, provide a balanced summary (pros/cons)
- If asked for comparisons, highlight key differences
- If asked about features, reference the specifications
- If you don't know something, say so honestly
- Keep responses under 200 words unless detailed comparison requested
- Use INR for prices (1 INR = 100 paise)"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": request.question}
    ]
    
    try:
        response = await client.chat_completion(
            model="llama3.2:latest",
            messages=messages,
            temperature=0.7,
            max_tokens=500,
        )
        answer = response.get("message", {}).get("content", "I'm not sure about that. Let me know if you have other questions!")
        
        # Determine response type
        q_lower = request.question.lower()
        if any(w in q_lower for w in ["compare", "alternative", "similar", "vs", "versus", "better"]):
            resp_type = "comparison"
        elif any(w in q_lower for w in ["feature", "spec", "specification", "detail"]):
            resp_type = "product"
        else:
            resp_type = "text"
        
        await client.close()
        return ChatResponse(
            answer=answer,
            type=resp_type,
            metadata={"question": request.question}
        )
    except Exception as e:
        await client.close()
        return ChatResponse(
            answer="Sorry, I couldn't process that question. Please try again.",
            type="error",
            metadata={"error": str(e)}
        )


@router.get("/recommendations")
async def get_recommendations(
    category: str,
    exclude: int | None = None,
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
):
    """
    Get similar product recommendations by category.
    Used by conversational checkout for product comparisons.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.db.models import Product
    
    stmt = select(Product).options(
        selectinload(Product.merchant)
    ).where(
        Product.category == category,
        Product.stock > 0
    )
    if exclude:
        stmt = stmt.where(Product.id != exclude)
    stmt = stmt.limit(limit)
    
    result = await db.execute(stmt)
    products = result.scalars().all()
    
    return {
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "merchant": p.merchant.name if p.merchant else "Unknown",
                "price": p.base_price,
                "category": p.category,
                "specs": p.spec or {}
            }
            for p in products
        ]
    }