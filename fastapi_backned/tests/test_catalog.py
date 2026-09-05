import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.catalog.search import search_catalog, get_product_detail, compare_products
from app.db.models import Product


@pytest.mark.asyncio
async def test_search_catalog_by_category(db_session):
    session, _ = db_session
    results = await search_catalog(session, category="Electronics")
    assert len(results) >= 5
    for p in results:
        assert p.category == "Electronics"


@pytest.mark.asyncio
async def test_search_catalog_by_max_price(db_session):
    session, _ = db_session
    results = await search_catalog(session, max_price=500000)
    for p in results:
        assert p.base_price <= 500000


@pytest.mark.asyncio
async def test_search_catalog_by_delivery_days(db_session):
    session, _ = db_session
    results = await search_catalog(session, max_delivery_days=3)
    for p in results:
        assert p.delivery_days <= 3


@pytest.mark.asyncio
async def test_search_catalog_by_keywords(db_session):
    session, _ = db_session
    results = await search_catalog(session, keywords="keyboard")
    assert len(results) >= 1
    assert any("keyboard" in p.name.lower() for p in results)


@pytest.mark.asyncio
async def test_search_catalog_combined_filters(db_session):
    session, _ = db_session
    results = await search_catalog(
        session,
        category="Electronics",
        max_price=500000,
        max_delivery_days=4,
    )
    assert len(results) >= 1
    for p in results:
        assert p.category == "Electronics"
        assert p.base_price <= 500000
        assert p.delivery_days <= 4


@pytest.mark.asyncio
async def test_get_product_detail(db_session):
    session, _ = db_session
    results = await search_catalog(session, category="Electronics", limit=1)
    assert len(results) == 1
    
    product = await get_product_detail(session, results[0].id)
    assert product is not None
    assert product.id == results[0].id
    assert product.merchant is not None
    assert hasattr(product, "pricing_tiers")


@pytest.mark.asyncio
async def test_get_product_detail_not_found(db_session):
    session, _ = db_session
    product = await get_product_detail(session, 99999)
    assert product is None


@pytest.mark.asyncio
async def test_compare_products(db_session):
    session, _ = db_session
    results = await search_catalog(session, category="Electronics", limit=3)
    assert len(results) >= 2
    
    product_ids = [p.id for p in results[:3]]
    comparison = await compare_products(session, product_ids)
    
    assert len(comparison) == len(product_ids)
    for comp in comparison:
        assert "product_id" in comp
        assert "name" in comp
        assert "merchant" in comp
        assert "base_price" in comp
        assert "pricing_tiers" in comp


@pytest.mark.asyncio
async def test_compare_products_empty(db_session):
    session, _ = db_session
    comparison = await compare_products(session, [])
    assert comparison == []


@pytest.mark.asyncio
async def test_compare_products_includes_pricing_tiers(db_session):
    session, _ = db_session
    results = await search_catalog(session, category="Electronics", limit=1)
    assert len(results) == 1
    
    product_ids = [results[0].id]
    comparison = await compare_products(session, product_ids)
    
    assert len(comparison) == 1
    assert "pricing_tiers" in comparison[0]
    if "1-4" in comparison[0]["pricing_tiers"]:
        assert comparison[0]["pricing_tiers"]["1-4"] == 450000