import json
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.db.models import Product
from app.agents.tools import ToolResult


async def get_upsell_recommendations(
    session: AsyncSession,
    product_id: int,
    limit: int = 3,
) -> ToolResult:
    """Get upsell recommendations (higher tier/more premium products in same category)."""
    try:
        # Get the base product
        from app.catalog.search import get_product_detail
        product = await get_product_detail(session, product_id)
        if not product:
            return ToolResult(success=False, error="Product not found")
        
        # Find upsell products: same category, higher price, good ratings
        stmt = select(Product).where(
            and_(
                Product.category == product.category,
                Product.base_price > product.base_price,
                Product.stock > 0,
                Product.id != product_id,
            )
        ).order_by(Product.base_price.asc()).limit(limit)
        
        result = await session.execute(stmt)
        upsell_products = result.scalars().all()
        
        upsells = []
        for p in upsell_products:
            price_diff = p.base_price - product.base_price
            upsells.append({
                "product_id": p.id,
                "name": p.name,
                "merchant": p.merchant.name if p.merchant else "Unknown",
                "price": p.base_price,
                "currency": p.currency,
                "price_diff": price_diff,
                "reason": f"Upgrade for {price_diff//100} more - {p.name}",
                "category": p.category,
                "delivery_days": p.delivery_days,
                "stock": p.stock,
            })
        
        return ToolResult(success=True, data={"upsells": upsells})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def get_cross_sell_recommendations(
    session: AsyncSession,
    product_id: int,
    limit: int = 3,
) -> ToolResult:
    """Get cross-sell recommendations (complementary products)."""
    try:
        from app.catalog.search import get_product_detail
        product = await get_product_detail(session, product_id)
        if not product:
            return ToolResult(success=False, error="Product not found")
        
        # Define cross-sell categories mapping
        cross_sell_map = {
            "Electronics": ["Accessories", "Office supplies"],
            "Books": ["Office supplies", "Electronics"],
            "Office supplies": ["Electronics", "Books"],
            "Accessories": ["Electronics"],
        }
        
        target_categories = cross_sell_map.get(product.category, [])
        if not target_categories:
            return ToolResult(success=True, data={"cross_sells": []})
        
        # Find products in complementary categories
        stmt = select(Product).where(
            and_(
                Product.category.in_(target_categories),
                Product.stock > 0,
                Product.id != product_id,
            )
        ).order_by(Product.base_price.asc()).limit(limit)
        
        result = await session.execute(stmt)
        cross_sell_products = result.scalars().all()
        
        cross_sells = []
        for p in cross_sell_products:
            cross_sells.append({
                "product_id": p.id,
                "name": p.name,
                "merchant": p.merchant.name if p.merchant else "Unknown",
                "price": p.base_price,
                "currency": p.currency,
                "reason": f"Complements your {product.name} - {p.category}",
                "category": p.category,
                "delivery_days": p.delivery_days,
                "stock": p.stock,
            })
        
        return ToolResult(success=True, data={"cross_sells": cross_sells})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def get_bundle_recommendations(
    session: AsyncSession,
    product_id: int,
    limit: int = 2,
) -> ToolResult:
    """Get bundle recommendations (product + accessories)."""
    try:
        from app.catalog.search import get_product_detail
        product = await get_product_detail(session, product_id)
        if not product:
            return ToolResult(success=False, error="Product not found")
        
        # For electronics, suggest accessories; for books, suggest related books; etc.
        bundle_map = {
            "Electronics": {
                "categories": ["Accessories"],
                "name": "Protection & Accessories Bundle",
            },
            "Books": {
                "categories": ["Books", "Office supplies"],
                "name": "Reading Essentials Bundle",
            },
            "Office supplies": {
                "categories": ["Office supplies", "Electronics"],
                "name": "Productivity Bundle",
            },
        }
        
        bundle_config = bundle_map.get(product.category)
        if not bundle_config:
            return ToolResult(success=True, data={"bundles": []})
        
        # Find bundle items
        stmt = select(Product).where(
            and_(
                Product.category.in_(bundle_config["categories"]),
                Product.stock > 0,
                Product.id != product_id,
            )
        ).order_by(Product.base_price.asc()).limit(3)
        
        result = await session.execute(stmt)
        bundle_items = result.scalars().all()
        
        if not bundle_items:
            return ToolResult(success=True, data={"bundles": []})
        
        # Create bundle
        bundle_items_data = []
        total_price = 0
        for item in bundle_items:
            item_price = item.base_price
            total_price += item_price
            bundle_items_data.append({
                "product_id": item.id,
                "name": item.name,
                "price": item.base_price,
                "currency": item.currency,
            })
        
        total_with_main = product.base_price + total_price
        savings = int(total_with_main * 0.05)  # 5% bundle discount
        
        bundles = [{
            "bundle_id": f"bundle_{product.id}",
            "name": bundle_config["name"],
            "main_product": {
                "product_id": product.id,
                "name": product.name,
                "price": product.base_price,
            },
            "addons": bundle_items_data,
            "total_price": total_with_main,
            "discounted_price": total_with_main - savings,
            "savings": savings,
            "currency": product.currency,
        }]
        
        return ToolResult(success=True, data={"bundles": bundles})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def get_all_recommendations(
    session: AsyncSession,
    product_id: int,
    limit: int = 3,
) -> ToolResult:
    """Get all recommendation types in one call."""
    try:
        upsells = await get_upsell_recommendations(session, product_id, limit)
        cross_sells = await get_cross_sell_recommendations(session, product_id, limit)
        bundles = await get_bundle_recommendations(session, product_id, limit)
        
        return ToolResult(success=True, data={
            "upsells": upsells.data.get("upsells", []) if upsells.success else [],
            "cross_sells": cross_sells.data.get("cross_sells", []) if cross_sells.success else [],
            "bundles": bundles.data.get("bundles", []) if bundles.success else [],
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))