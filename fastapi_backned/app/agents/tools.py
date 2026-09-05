from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from app.catalog.search import search_catalog, get_product_detail, compare_products
from app.db.models import PurchaseIntent, AuditLog


class PurchaseConstraints(BaseModel):
    category: Optional[str] = Field(default=None, description="Product category")
    max_price: Optional[int] = Field(default=None, description="Maximum price in paise")
    min_price: Optional[int] = Field(default=None, description="Minimum price in paise")
    keywords: Optional[str] = Field(default=None, description="Search keywords")
    max_delivery_days: Optional[int] = Field(default=None, description="Maximum delivery days")
    quantity: int = Field(default=1, description="Quantity to purchase")


class ToolResult(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


async def search_catalog_tool(
    session: AsyncSession,
    category: Optional[str] = None,
    max_price: Optional[int] = None,
    min_price: Optional[int] = None,
    max_delivery_days: Optional[int] = None,
    merchant_id: Optional[int] = None,
    keywords: Optional[str] = None,
    limit: int = 20,
) -> ToolResult:
    """Search catalog - Buyer Agent only"""
    try:
        products = await search_catalog(
            session=session,
            category=category,
            max_price=max_price,
            min_price=min_price,
            max_delivery_days=max_delivery_days,
            merchant_id=merchant_id,
            keywords=keywords,
            limit=limit,
        )
        return ToolResult(
            success=True,
            data={
                "products": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "category": p.category,
                        "merchant_id": p.merchant_id,
                        "merchant_name": p.merchant.name if p.merchant else None,
                        "base_price": p.base_price,
                        "currency": p.currency,
                        "delivery_days": p.delivery_days,
                        "stock": p.stock,
                    }
                    for p in products
                ]
            }
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def get_product_detail_tool(
    session: AsyncSession,
    product_id: int,
) -> ToolResult:
    """Get product detail - Buyer Agent only"""
    try:
        product = await get_product_detail(session, product_id)
        if not product:
            return ToolResult(success=False, error="Product not found")
        
        tier_prices = {}
        for tier in product.pricing_tiers:
            max_qty_str = str(tier.max_qty) if tier.max_qty else "+"
            tier_prices[f"{tier.min_qty}-{max_qty_str}"] = tier.unit_price
        
        return ToolResult(
            success=True,
            data={
                "id": product.id,
                "name": product.name,
                "category": product.category,
                "description": product.description,
                "merchant_id": product.merchant_id,
                "merchant_name": product.merchant.name if product.merchant else None,
                "base_price": product.base_price,
                "currency": product.currency,
                "delivery_days": product.delivery_days,
                "stock": product.stock,
                "spec": product.spec,
                "pricing_tiers": tier_prices,
            }
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def compare_products_tool(
    session: AsyncSession,
    product_ids: List[int],
) -> ToolResult:
    """Compare products - Buyer Agent only"""
    try:
        comparison = await compare_products(session, product_ids)
        return ToolResult(success=True, data={"comparison": comparison})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def propose_purchase_tool(
    session: AsyncSession,
    user_id: int,
    product_id: int,
    quantity: int,
    reasoning: str,
) -> ToolResult:
    """Propose purchase - Buyer Agent only. Creates PurchaseIntent in DRAFT status."""
    try:
        product = await get_product_detail(session, product_id)
        if not product:
            return ToolResult(success=False, error="Product not found")
        
        if product.stock < quantity:
            return ToolResult(success=False, error=f"Insufficient stock: {product.stock} available")
        
        unit_price = product.base_price
        amount = unit_price * quantity
        
        from app.db.models import PurchaseIntentStatus
        
        intent = PurchaseIntent(
            user_id=user_id,
            product_id=product_id,
            merchant_id=product.merchant_id,
            quantity=quantity,
            unit_price=unit_price,
            amount=amount,
            status=PurchaseIntentStatus.DRAFT,
            reasoning=reasoning,
        )
        session.add(intent)
        await session.flush()
        
        audit_log = AuditLog(
            purchase_intent_id=intent.id,
            actor="buyer_agent",
            event="product_selected",
            payload={"product_id": product_id, "reasoning": reasoning},
        )
        session.add(audit_log)
        await session.commit()
        
        return ToolResult(
            success=True,
            data={
                "purchase_intent_id": intent.id,
                "status": intent.status.value,
                "amount": amount,
            }
        )
    except Exception as e:
        await session.rollback()
        return ToolResult(success=False, error=str(e))


async def request_negotiation_tool(
    session: AsyncSession,
    purchase_intent_id: int,
    requested_qty: int,
) -> ToolResult:
    """Request negotiation - Buyer Agent only. Opens negotiation with merchant agent."""
    try:
        from app.db.models import PurchaseIntent, Negotiation
        
        intent = await session.get(PurchaseIntent, purchase_intent_id)
        if not intent:
            return ToolResult(success=False, error="Purchase intent not found")
        
        if intent.status != "DRAFT":
            return ToolResult(success=False, error="Intent not in DRAFT status")
        
        product = await get_product_detail(session, intent.product_id)
        if not product:
            return ToolResult(success=False, error="Product not found")
        
        negotiation = Negotiation(
            purchase_intent_id=purchase_intent_id,
            requested_qty=requested_qty,
            offered_price=intent.unit_price,
            accepted=None,
        )
        session.add(negotiation)
        await session.commit()
        
        return ToolResult(
            success=True,
            data={"negotiation_id": negotiation.id, "status": "pending"}
        )
    except Exception as e:
        await session.rollback()
        return ToolResult(success=False, error=str(e))


async def get_pricing_tier_tool(
    session: AsyncSession,
    product_id: int,
    quantity: int,
) -> ToolResult:
    """Get pricing tier - Merchant Agent only. Deterministic lookup."""
    try:
        from app.db.models import MerchantPricingTier
        from sqlalchemy import select, and_
        
        stmt = select(MerchantPricingTier).where(
            and_(
                MerchantPricingTier.product_id == product_id,
                MerchantPricingTier.min_qty <= quantity,
                (MerchantPricingTier.max_qty.is_(None)) | (MerchantPricingTier.max_qty >= quantity),
            )
        ).order_by(MerchantPricingTier.min_qty.desc())
        
        result = await session.execute(stmt)
        tier = result.scalars().first()
        
        if not tier:
            product = await get_product_detail(session, product_id)
            if product:
                return ToolResult(
                    success=True,
                    data={"unit_price": product.base_price, "tier_found": False}
                )
            return ToolResult(success=False, error="Product not found")
        
        return ToolResult(
            success=True,
            data={"unit_price": tier.unit_price, "tier_found": True}
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def check_negotiation_floor_tool(
    session: AsyncSession,
    product_id: int,
    offered_price: int,
) -> ToolResult:
    """Check negotiation floor - Merchant Agent only. Deterministic check."""
    try:
        from app.db.models import Product, MerchantPolicy
        from sqlalchemy import select
        
        product = await get_product_detail(session, product_id)
        if not product:
            return ToolResult(success=False, error="Product not found")
        
        stmt = select(MerchantPolicy).where(MerchantPolicy.merchant_id == product.merchant_id)
        result = await session.execute(stmt)
        policy = result.scalars().first()
        
        if not policy:
            return ToolResult(success=True, data={"allowed": True, "floor_price": product.base_price})
        
        floor_price = int(product.base_price * policy.negotiation_floor_pct)
        allowed = offered_price >= floor_price
        
        return ToolResult(
            success=True,
            data={"allowed": allowed, "floor_price": floor_price}
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def get_merchant_policy_tool(
    session: AsyncSession,
    merchant_id: int,
) -> ToolResult:
    """Get merchant policy - Merchant Agent only."""
    try:
        from app.db.models import MerchantPolicy
        from sqlalchemy import select
        
        stmt = select(MerchantPolicy).where(MerchantPolicy.merchant_id == merchant_id)
        result = await session.execute(stmt)
        policy = result.scalars().first()
        
        if not policy:
            return ToolResult(success=True, data={"negotiation_floor_pct": 0.8, "agent_transaction_limit": None})
        
        return ToolResult(
            success=True,
            data={
                "negotiation_floor_pct": policy.negotiation_floor_pct,
                "agent_transaction_limit": policy.agent_transaction_limit,
            }
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))