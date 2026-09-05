from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List

from app.db.session import get_db
from app.agents.campaign_agent import (
    get_active_campaigns,
    evaluate_campaign_eligibility,
    apply_campaign,
    get_campaign_analytics,
)
from app.db.models import Campaign, CampaignStatus, CampaignType


router = APIRouter(prefix="/api", tags=["campaign"])


class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = None
    campaign_type: CampaignType = CampaignType.PROMOTION
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    target_categories: Optional[List[str]] = None
    target_merchants: Optional[List[int]] = None
    min_order_value_paise: Optional[int] = None
    max_discount_pct: Optional[int] = None
    discount_type: Optional[str] = None
    discount_value: Optional[int] = None
    buy_x_get_y_config: Optional[dict] = None
    budget_paise: Optional[int] = None
    max_uses: Optional[int] = None
    max_uses_per_customer: Optional[int] = None
    min_order_value_paise: Optional[int] = None
    applicable_categories: Optional[List[str]] = None
    excluded_categories: Optional[List[str]] = None
    applicable_products: Optional[List[int]] = None
    excluded_products: Optional[List[int]] = None
    min_quantity: int = 1
    new_customers_only: bool = False
    customer_segments: Optional[List[str]] = None
    requires_coupon_code: bool = False
    coupon_code: Optional[str] = None
    created_by: Optional[int] = None


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[CampaignStatus] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    target_categories: Optional[List[str]] = None
    target_merchants: Optional[List[int]] = None
    min_order_value_paise: Optional[int] = None
    max_discount_pct: Optional[int] = None
    discount_type: Optional[str] = None
    discount_value: Optional[int] = None
    buy_x_get_y_config: Optional[dict] = None
    budget_paise: Optional[int] = None
    max_uses: Optional[int] = None
    max_uses_per_customer: Optional[int] = None
    min_order_value_paise: Optional[int] = None
    applicable_categories: Optional[List[str]] = None
    excluded_categories: Optional[List[str]] = None
    applicable_products: Optional[List[int]] = None
    excluded_products: Optional[List[int]] = None
    min_quantity: Optional[int] = None
    new_customers_only: Optional[bool] = None
    customer_segments: Optional[List[str]] = None
    requires_coupon_code: Optional[bool] = None
    coupon_code: Optional[str] = None


class CampaignResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    campaign_type: CampaignType
    status: CampaignStatus
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    discount_type: Optional[str] = None
    discount_value: Optional[int] = None
    max_discount_pct: Optional[int] = None
    coupon_code: Optional[str] = None
    requires_coupon_code: bool = False
    min_order_value_paise: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class CampaignEvaluateRequest(BaseModel):
    user_id: int
    order_value: int
    category: str
    product_ids: List[int]
    coupon_code: Optional[str] = None


class CampaignEvaluateResponse(BaseModel):
    success: bool
    campaign_id: Optional[int] = None
    campaign_name: Optional[str] = None
    discount_paise: Optional[int] = None
    discount_type: Optional[str] = None
    coupon_code: Optional[str] = None
    max_discount_pct: Optional[int] = None
    error: Optional[str] = None


class CampaignApplyRequest(BaseModel):
    user_id: int
    purchase_intent_id: int
    order_value: int
    discount_paise: int
    coupon_code: Optional[str] = None


class CampaignApplyResponse(BaseModel):
    success: bool
    usage_id: Optional[int] = None
    discount_applied: Optional[int] = None
    error: Optional[str] = None


class CampaignAnalyticsResponse(BaseModel):
    analytics: list[dict]


@router.post("/campaigns", response_model=CampaignResponse)
async def create_campaign(
    request: CampaignCreate,
    db: AsyncSession = Depends(get_db),
):
    campaign = Campaign(
        name=request.name,
        description=request.description,
        campaign_type=request.campaign_type,
        start_date=request.start_date,
        end_date=request.end_date,
        target_categories=request.target_categories,
        target_merchants=request.target_merchants,
        min_order_value_paise=request.min_order_value_paise,
        max_discount_pct=request.max_discount_pct,
        discount_type=request.discount_type,
        discount_value=request.discount_value,
        buy_x_get_y_config=request.buy_x_get_y_config,
        budget_paise=request.budget_paise,
        max_uses=request.max_uses,
        max_uses_per_customer=request.max_uses_per_customer,
        applicable_categories=request.applicable_categories,
        excluded_categories=request.excluded_categories,
        applicable_products=request.applicable_products,
        excluded_products=request.excluded_products,
        min_quantity=request.min_quantity,
        new_customers_only=request.new_customers_only,
        customer_segments=request.customer_segments,
        requires_coupon_code=request.requires_coupon_code,
        coupon_code=request.coupon_code,
        created_by=request.created_by,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.get("/campaigns", response_model=list[CampaignResponse])
async def list_campaigns(
    status: Optional[CampaignStatus] = None,
    merchant_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Campaign)
    if status:
        stmt = stmt.where(Campaign.status == status)
    if merchant_id:
        stmt = stmt.where(Campaign.target_merchants.contains([merchant_id]))
    result = await db.execute(stmt)
    campaigns = result.scalars().all()
    return campaigns


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.patch("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: int,
    request: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(campaign, field, value)
    
    campaign.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.delete("/campaigns/{campaign_id}")
async def delete_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    await db.delete(campaign)
    await db.commit()
    return {"success": True}


@router.post("/campaigns/{campaign_id}/activate")
async def activate_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign.status = CampaignStatus.ACTIVE
    campaign.updated_at = datetime.utcnow()
    await db.commit()
    return {"success": True, "status": campaign.status.value}


@router.post("/campaigns/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign.status = CampaignStatus.PAUSED
    campaign.updated_at = datetime.utcnow()
    await db.commit()
    return {"success": True, "status": campaign.status.value}


@router.post("/campaigns/evaluate", response_model=CampaignEvaluateResponse)
async def evaluate_campaign_endpoint(
    request: CampaignEvaluateRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await evaluate_campaign_eligibility(
        db,
        request.user_id,
        request.order_value,
        request.category,
        request.product_ids,
    )
    return CampaignEvaluateResponse(**result.data) if result.success else CampaignEvaluateResponse(success=False, error=result.error)


@router.post("/campaigns/apply", response_model=CampaignApplyResponse)
async def apply_campaign_endpoint(
    request: CampaignApplyRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await apply_campaign(
        db,
        request.user_id,
        request.purchase_intent_id,
        request.order_value,
        request.discount_paise,
        request.coupon_code,
    )
    return CampaignApplyResponse(**result.data) if result.success else CampaignApplyResponse(success=False, error=result.error)


@router.get("/campaigns/analytics", response_model=CampaignAnalyticsResponse)
async def get_campaign_analytics_endpoint(
    campaign_id: Optional[int] = None,
    merchant_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
):
    result = await get_campaign_analytics(db, campaign_id, merchant_id, start_date, end_date)
    return CampaignAnalyticsResponse(**result.data) if result.success else CampaignAnalyticsResponse(analytics=[])