from typing import Optional
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Product, Merchant


async def search_catalog(
    session: AsyncSession,
    category: Optional[str] = None,
    max_price: Optional[int] = None,
    min_price: Optional[int] = None,
    max_delivery_days: Optional[int] = None,
    merchant_id: Optional[int] = None,
    keywords: Optional[str] = None,
    in_stock_only: bool = True,
    limit: int = 50,
    offset: int = 0,
) -> list[Product]:
    stmt = select(Product).options(selectinload(Product.merchant))

    conditions = []

    if in_stock_only:
        conditions.append(Product.stock > 0)

    if category:
        conditions.append(Product.category == category)

    if max_price is not None:
        conditions.append(Product.base_price <= max_price)

    if min_price is not None:
        conditions.append(Product.base_price >= min_price)

    if max_delivery_days is not None:
        conditions.append(Product.delivery_days <= max_delivery_days)

    if merchant_id is not None:
        conditions.append(Product.merchant_id == merchant_id)

    if keywords:
        keyword_conditions = []
        for keyword in keywords.split():
            kw = f"%{keyword}%"
            keyword_conditions.append(
                or_(
                    Product.name.ilike(kw),
                    Product.description.ilike(kw),
                )
            )
        if keyword_conditions:
            conditions.append(or_(*keyword_conditions))

    if conditions:
        stmt = stmt.where(and_(*conditions))

    stmt = stmt.order_by(Product.base_price).limit(limit).offset(offset)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_product_detail(session: AsyncSession, product_id: int) -> Optional[Product]:
    stmt = (
        select(Product)
        .options(selectinload(Product.merchant), selectinload(Product.pricing_tiers))
        .where(Product.id == product_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def compare_products(session: AsyncSession, product_ids: list[int]) -> list[dict]:
    if not product_ids:
        return []

    stmt = (
        select(Product)
        .options(selectinload(Product.merchant), selectinload(Product.pricing_tiers))
        .where(Product.id.in_(product_ids))
    )
    result = await session.execute(stmt)
    products = list(result.scalars().all())

    product_map = {p.id: p for p in products}

    comparison = []
    for pid in product_ids:
        if pid not in product_map:
            continue
        p = product_map[pid]
        
        tier_prices = {}
        for tier in p.pricing_tiers:
            max_qty_str = str(tier.max_qty) if tier.max_qty else "+"
            tier_prices[f"{tier.min_qty}-{max_qty_str}"] = tier.unit_price

        comparison.append({
            "product_id": p.id,
            "name": p.name,
            "category": p.category,
            "merchant": p.merchant.name,
            "merchant_id": p.merchant_id,
            "base_price": p.base_price,
            "currency": p.currency,
            "delivery_days": p.delivery_days,
            "stock": p.stock,
            "spec": p.spec,
            "pricing_tiers": tier_prices,
        })

    return comparison