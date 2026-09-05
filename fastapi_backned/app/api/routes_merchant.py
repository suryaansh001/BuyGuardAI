from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List

from app.db.session import get_db
from app.agents.merchant_agent import run_merchant_agent
from app.agents.upsell_agent import (
    get_upsell_recommendations,
    get_cross_sell_recommendations,
    get_bundle_recommendations,
    get_all_recommendations,
)
from app.agents.campaign_agent import (
    get_active_campaigns,
    evaluate_campaign_eligibility,
    apply_campaign,
    get_campaign_analytics,
)
from app.db.models import Negotiation, NegotiationStatus, PurchaseIntent, PurchaseIntentStatus, Campaign, CampaignStatus, CampaignType


router = APIRouter(prefix="/api", tags=["merchant"])


class NegotiateRequest(BaseModel):
    product_id: int
    quantity: int
    offered_price: int | None = None


class NegotiateResponse(BaseModel):
    success: bool
    unit_price: int | None = None
    quantity: int | None = None
    countered: bool | None = None
    message: str | None = None
    error: str | None = None


@router.post("/negotiate", response_model=NegotiateResponse)
async def negotiate(
    request: NegotiateRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await run_merchant_agent(
        db,
        product_id=request.product_id,
        quantity=request.quantity,
        offered_price=request.offered_price,
    )
    
    return NegotiateResponse(
        success=result.get("success", False),
        unit_price=result.get("unit_price"),
        quantity=result.get("quantity"),
        countered=result.get("countered"),
        message=result.get("message"),
        error=result.get("error"),
    )


class CreateNegotiationRequest(BaseModel):
    purchase_intent_id: int
    requested_qty: int
    offered_price: int


@router.post("/negotiations", response_model=dict)
async def create_negotiation(
    request: CreateNegotiationRequest,
    db: AsyncSession = Depends(get_db),
):
    intent = await db.get(PurchaseIntent, request.purchase_intent_id)
    if not intent:
        raise HTTPException(status_code=404, detail="Purchase intent not found")
    
    if intent.status != PurchaseIntentStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Intent not in DRAFT status")
    
    # Run merchant agent
    result = await run_merchant_agent(
        db,
        product_id=intent.product_id,
        quantity=request.requested_qty,
        offered_price=request.offered_price,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Negotiation failed"))
    
    # Create negotiation record
    from app.audit.logger import log_event
    
    negotiation = Negotiation(
        purchase_intent_id=request.purchase_intent_id,
        requested_qty=request.requested_qty,
        offered_price=request.offered_price,
        countered_price=result["unit_price"],
        accepted=None,
    )
    db.add(negotiation)
    await db.flush()
    
    await log_event(
        session=db,
        purchase_intent_id=request.purchase_intent_id,
        actor="merchant_agent",
        event="negotiation_response",
        payload={
            "qty": request.requested_qty,
            "tier_used": True,
            "unit_price": result["unit_price"],
            "countered": result.get("countered", False),
        },
    )
    
    await db.commit()
    
    return {
        "success": True,
        "negotiation_id": negotiation.id,
        "unit_price": result["unit_price"],
        "countered": result.get("countered", False),
    }


@router.get("/negotiations/{negotiation_id}")
async def get_negotiation(
    negotiation_id: int,
    db: AsyncSession = Depends(get_db),
):
    negotiation = await db.get(Negotiation, negotiation_id)
    if not negotiation:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    
    return {
        "id": negotiation.id,
        "purchase_intent_id": negotiation.purchase_intent_id,
        "requested_qty": negotiation.requested_qty,
        "offered_price": negotiation.offered_price,
        "countered_price": negotiation.countered_price,
        "accepted": negotiation.accepted,
        "merchant_reasoning": negotiation.merchant_reasoning,
    }


@router.get("/merchants/{merchant_id}/catalog")
async def get_merchant_catalog(
    merchant_id: int,
    db: AsyncSession = Depends(get_db),
):
    from app.db.models import Merchant, Product, MerchantPricingTier
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    
    merchant = await db.get(Merchant, merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    stmt = select(Product).options(
        selectinload(Product.pricing_tiers)
    ).where(Product.merchant_id == merchant_id)
    result = await db.execute(stmt)
    products = result.scalars().all()
    
    return {
        "merchant": merchant.name,
        "protocol": "acg/1.0",
        "catalog": [
            {
                "sku": f"p{p.id}",
                "title": p.name,
                "category": p.category,
                "currency": p.currency,
                "base_price": p.base_price,
                "stock": p.stock,
                "delivery_sla_days": p.delivery_days,
                "pricing_tiers": {
                    f"{t.min_qty}-{t.max_qty if t.max_qty else '+'}": t.unit_price
                    for t in p.pricing_tiers
                },
            }
            for p in products
        ],
    }


@router.get("/merchants/{merchant_id}/policy")
async def get_merchant_policy(
    merchant_id: int,
    db: AsyncSession = Depends(get_db),
):
    from app.db.models import MerchantPolicy
    
    policy = await db.get(MerchantPolicy, merchant_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Merchant policy not found")
    
    return {
        "negotiation_floor_pct": policy.negotiation_floor_pct,
        "agent_transaction_limit": policy.agent_transaction_limit,
        "allowed_categories": [],
    }


class RecommendationRequest(BaseModel):
    product_id: int
    limit: int = 3


class UpsellResponse(BaseModel):
    success: bool
    upsells: list[dict] = []
    error: str | None = None


class CrossSellResponse(BaseModel):
    success: bool
    cross_sells: list[dict] = []
    error: str | None = None


class BundleResponse(BaseModel):
    success: bool
    bundles: list[dict] = []
    error: str | None = None


class AllRecommendationsResponse(BaseModel):
    success: bool
    upsells: list[dict] = []
    cross_sells: list[dict] = []
    bundles: list[dict] = []
    error: str | None = None


@router.post("/recommendations/upsell", response_model=UpsellResponse)
async def get_upsell_recommendations_endpoint(
    request: RecommendationRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await get_upsell_recommendations(db, request.product_id, request.limit)
    return UpsellResponse(
        success=result.success,
        upsells=result.data.get("upsells", []) if result.success else [],
        error=result.error,
    )


@router.post("/recommendations/cross-sell", response_model=CrossSellResponse)
async def get_cross_sell_recommendations_endpoint(
    request: RecommendationRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await get_cross_sell_recommendations(db, request.product_id, request.limit)
    return CrossSellResponse(
        success=result.success,
        cross_sells=result.data.get("cross_sells", []) if result.success else [],
        error=result.error,
    )


@router.post("/recommendations/bundle", response_model=BundleResponse)
async def get_bundle_recommendations_endpoint(
    request: RecommendationRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await get_bundle_recommendations(db, request.product_id, request.limit)
    return BundleResponse(
        success=result.success,
        bundles=result.data.get("bundles", []) if result.success else [],
        error=result.error,
    )


@router.post("/recommendations/all", response_model=AllRecommendationsResponse)
async def get_all_recommendations_endpoint(
    request: RecommendationRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await get_all_recommendations(db, request.product_id, request.limit)
    return AllRecommendationsResponse(
        success=result.success,
        upsells=result.data.get("upsells", []) if result.success else [],
        cross_sells=result.data.get("cross_sells", []) if result.success else [],
        bundles=result.data.get("bundles", []) if result.success else [],
        error=result.error,
    )