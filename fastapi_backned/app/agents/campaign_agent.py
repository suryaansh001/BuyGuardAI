from datetime import datetime, date
from typing import Optional, List
from enum import Enum as PyEnum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.db.session import Base
from app.agents.tools import ToolResult
from app.db.models import Campaign, CampaignStatus, CampaignType, CampaignUsage


async def get_active_campaigns(
    session: AsyncSession,
    category: Optional[str] = None,
    merchant_id: Optional[int] = None,
    user_id: Optional[int] = None,
    order_value: int = 0,
    category_list: Optional[List[str]] = None,
) -> ToolResult:
    """Get active campaigns matching the given criteria."""
    try:
        now = datetime.utcnow()
        today = date.today()
        
        stmt = select(Campaign).where(
            and_(
                Campaign.status == CampaignStatus.ACTIVE,
                Campaign.start_date <= today,
                or_(Campaign.end_date.is_(None), Campaign.end_date >= today),
            )
        )
        
        # Apply time-based filters if times are set
        # (simplified for now - could add time-of-day checks)
        
        # Filter by category
        if category:
            stmt = stmt.where(
                or_(
                    Campaign.applicable_categories.is_(None),
                    Campaign.applicable_categories.contains([category]),
                )
            )
        
        # Filter by merchant
        if merchant_id:
            stmt = stmt.where(
                or_(
                    Campaign.target_merchants.is_(None),
                    Campaign.target_merchants.contains([merchant_id]),
                )
            )
        
        # Filter by order value
        if order_value > 0:
            stmt = stmt.where(
                or_(
                    Campaign.min_order_value_paise.is_(None),
                    Campaign.min_order_value_paise <= order_value,
                )
            )
        
        # Budget check
        stmt = stmt.where(
            or_(
                Campaign.budget_paise.is_(None),
                Campaign.spent_paise < Campaign.budget_paise,
            )
        )
        
        # Usage limits
        stmt = stmt.where(
            or_(
                Campaign.max_uses.is_(None),
                Campaign.used_count < Campaign.max_uses,
            )
        )
        
        # Customer targeting
        if user_id:
            # Could add more sophisticated user targeting here
            pass
        
        stmt = stmt.order_by(Campaign.priority.desc() if hasattr(Campaign, 'priority') else Campaign.created_at.desc())
        
        result = await session.execute(stmt)
        campaigns = result.scalars().all()
        
        campaigns_data = []
        for c in campaigns:
            campaigns_data.append({
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "campaign_type": c.campaign_type.value,
                "discount_type": c.discount_type,
                "discount_value": c.discount_value,
                "buy_x_get_y_config": c.buy_x_get_y_config,
                "max_discount_pct": c.max_discount_pct,
                "coupon_code": c.coupon_code,
                "requires_coupon_code": c.requires_coupon_code,
                "min_order_value_paise": c.min_order_value_paise,
                "max_discount_pct": c.max_discount_pct,
                "applicable_categories": c.applicable_categories,
                "excluded_categories": c.excluded_categories,
            })
        
        return ToolResult(success=True, data={"campaigns": campaigns_data})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def evaluate_campaign_eligibility(
    session: AsyncSession,
    campaign_id: int,
    user_id: int,
    order_value: int,
    category: str,
    product_ids: List[int],
    coupon_code: Optional[str] = None,
) -> ToolResult:
    """Evaluate if a campaign applies to a given order."""
    try:
        from app.db.models import Campaign, CampaignUsage, User
        from sqlalchemy import select, and_, func
        
        campaign = await session.get(Campaign, campaign_id)
        if not campaign:
            return ToolResult(success=False, error="Campaign not found")
        
        if campaign.status != CampaignStatus.ACTIVE:
            return ToolResult(success=False, error="Campaign not active")
        
        now = datetime.utcnow()
        today = date.today()
        
        # Check dates
        if campaign.start_date and campaign.start_date > date.today():
            return ToolResult(success=False, error="Campaign not started yet")
        if campaign.end_date and campaign.end_date < date.today():
            return ToolResult(success=False, error="Campaign expired")
        
        # Check budget
        if campaign.budget_paise and campaign.spent_paise >= campaign.budget_paise:
            return ToolResult(success=False, error="Campaign budget exhausted")
        
        # Check usage limits
        if campaign.max_uses and campaign.used_count >= campaign.max_uses:
            return ToolResult(success=False, error="Campaign usage limit reached")
        
        # Check per-customer limit
        if campaign.max_uses_per_customer:
            user_usage = await session.execute(
                select(func.count(CampaignUsage.id)).where(
                    and_(
                        CampaignUsage.campaign_id == campaign_id,
                        CampaignUsage.user_id == user_id,
                    )
                )
            )
            user_count = user_usage.scalar() or 0
            if user_count >= campaign.max_uses_per_customer:
                return ToolResult(success=False, error="Per-customer usage limit reached")
        
        # Check min order value
        if campaign.min_order_value_paise and order_value < campaign.min_order_value_paise:
            return ToolResult(success=False, error=f"Minimum order value {campaign.min_order_value_paise/100} not met")
        
        # Check category
        if campaign.applicable_categories:
            if not any(cat in campaign.applicable_categories for cat in [category]):
                return ToolResult(success=False, error="Category not eligible")
        
        if campaign.excluded_categories:
            if any(cat in campaign.excluded_categories for cat in [category]):
                return ToolResult(success=False, error="Category excluded")
        
        # Check product IDs
        if campaign.applicable_products:
            if not any(pid in campaign.applicable_products for pid in product_ids):
                return ToolResult(success=False, error="No applicable products in order")
        
        if campaign.excluded_products:
            if any(pid in campaign.excluded_products for pid in product_ids):
                return ToolResult(success=False, error="Contains excluded products")
        
        # Check coupon code
        if campaign.requires_coupon_code:
            if not coupon_code or coupon_code != campaign.coupon_code:
                return ToolResult(success=False, error="Valid coupon code required")
        
        # Check user targeting
        if campaign.new_customers_only:
            # Check if user has previous orders
            from app.db.models import PurchaseIntent
            existing_orders = await session.execute(
                select(func.count()).select_from(PurchaseIntent).where(
                    PurchaseIntent.user_id == user_id,
                    PurchaseIntent.status.in_(["PAID", "APPROVED", "ALLOWED"])
                )
            )
            if (await session.execute(select(1).where(PurchaseIntent.user_id == user_id))).scalar():
                return ToolResult(success=False, error="New customers only")
        
        # Calculate discount
        discount = 0
        if campaign.discount_type == "percentage":
            discount = min(
                (order_value * campaign.discount_value) // 100,
                (order_value * (campaign.max_discount_pct or 100)) // 100
            )
        elif campaign.discount_type == "fixed":
            discount = min(campaign.discount_value, order_value)
        elif campaign.discount_type == "buy_x_get_y":
            config = campaign.buy_x_get_y_config or {}
            buy = config.get("buy", 1)
            get = config.get("get", 1)
            free_or_discount = config.get("free_or_discount", "free")
            # This would need more complex logic based on quantities
            pass
        
        return ToolResult(success=True, data={
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "discount_paise": discount,
            "discount_type": campaign.discount_type,
            "coupon_code": campaign.coupon_code,
            "max_discount_pct": campaign.max_discount_pct,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def apply_campaign(
    session: AsyncSession,
    campaign_id: int,
    user_id: int,
    purchase_intent_id: int,
    order_value: int,
    discount_paise: int,
    coupon_code: Optional[str] = None,
) -> ToolResult:
    """Record campaign usage and update counters."""
    try:
        from app.db.models import CampaignUsage, Campaign
        from datetime import datetime
        
        campaign = await session.get(Campaign, campaign_id)
        if not campaign:
            return ToolResult(success=False, error="Campaign not found")
        
        # Create usage record
        usage = CampaignUsage(
            campaign_id=campaign_id,
            user_id=user_id,
            purchase_intent_id=purchase_intent_id,
            order_amount_paise=order_value,
            discount_paise=discount_paise,
            coupon_code=coupon_code,
        )
        session.add(usage)
        
        # Update campaign counters
        campaign.used_count += 1
        campaign.spent_paise += discount_paise
        
        await session.commit()
        
        return ToolResult(success=True, data={
            "usage_id": usage.id,
            "discount_applied": discount_paise,
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def get_campaign_analytics(
    session: AsyncSession,
    campaign_id: Optional[int] = None,
    merchant_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> ToolResult:
    """Get campaign performance analytics."""
    try:
        from app.db.models import CampaignUsage, Campaign, PurchaseIntent
        from sqlalchemy import select, func, and_
        
        query = select(
            Campaign.id,
            Campaign.name,
            Campaign.campaign_type,
            func.count(CampaignUsage.id).label("total_uses"),
            func.sum(CampaignUsage.order_amount_paise).label("total_order_value"),
            func.sum(CampaignUsage.discount_paise).label("total_discount"),
            func.count(func.distinct(CampaignUsage.user_id)).label("unique_customers"),
        ).select_from(Campaign).join(
            CampaignUsage, Campaign.id == CampaignUsage.campaign_id
        ).group_by(Campaign.id, Campaign.name, Campaign.campaign_type)
        
        if campaign_id:
            query = query.where(Campaign.id == campaign_id)
        
        if merchant_id:
            query = query.where(Campaign.target_merchants.contains([merchant_id]))
        
        if start_date:
            query = query.where(CampaignUsage.created_at >= start_date)
        if end_date:
            query = query.where(CampaignUsage.created_at <= end_date)
        
        result = await session.execute(query)
        rows = result.all()
        
        analytics = []
        for row in rows:
            total_order = row.total_order_value or 0
            total_discount = row.total_discount or 0
            analytics.append({
                "campaign_id": row.id,
                "name": row.name,
                "type": row.campaign_type,
                "total_uses": row.total_uses,
                "total_order_value": total_order,
                "total_discount": total_discount,
                "unique_customers": row.unique_customers,
                "avg_order_value": total_order // row.total_uses if row.total_uses else 0,
                "avg_discount": total_discount // row.total_uses if row.total_uses else 0,
                "conversion_rate": 0,  # Would need impression data
            })
        
        return ToolResult(success=True, data={"analytics": analytics})
    except Exception as e:
        return ToolResult(success=False, error=str(e))