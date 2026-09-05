import asyncio
from decimal import Decimal
from sqlalchemy import select
from app.db.session import engine, async_session_maker, init_db
from app.db.models import (
    User,
    BuyerPolicy,
    Merchant,
    Product,
    MerchantPricingTier,
    MerchantPolicy,
    PurchaseIntentStatus,
)


async def seed():
    await init_db()
    
    async with async_session_maker() as session:
        # Check if already seeded
        result = await session.execute(select(User))
        if result.scalars().first():
            print("Database already seeded, skipping...")
            return

        # Create demo user
        user = User(name="Demo Buyer", email="buyer@demo.com")
        session.add(user)
        await session.flush()

        # Create buyer policy
        buyer_policy = BuyerPolicy(
            user_id=user.id,
            max_transaction_amount=500000,  # ₹5000 in paise
            daily_spending_limit=1000000,   # ₹10000 in paise
            approval_required_above=300000, # ₹3000 in paise
            allowed_categories=["Electronics", "Books", "Office supplies"],
            blocked_categories=[],
            allowed_merchant_ids=None,
        )
        session.add(buyer_policy)

        # Create Merchant 1 - TechCorp Electronics
        merchant1 = Merchant(
            name="TechCorp Electronics",
            agent_permissions={"allow_negotiation": True, "max_negotiation_rounds": 2},
        )
        session.add(merchant1)
        await session.flush()

        merchant1_policy = MerchantPolicy(
            merchant_id=merchant1.id,
            negotiation_floor_pct=0.85,
            agent_transaction_limit=500000,
        )
        session.add(merchant1_policy)

        # Create Merchant 2 - BookWorm Books
        merchant2 = Merchant(
            name="BookWorm Books",
            agent_permissions={"allow_negotiation": True, "max_negotiation_rounds": 2},
        )
        session.add(merchant2)
        await session.flush()

        merchant2_policy = MerchantPolicy(
            merchant_id=merchant2.id,
            negotiation_floor_pct=0.90,
            agent_transaction_limit=200000,
        )
        session.add(merchant2_policy)

        # Products for TechCorp Electronics
        products_merchant1 = [
            Product(
                merchant_id=merchant1.id,
                name="Mechanical Keyboard RGB",
                category="Electronics",
                description="RGB backlit mechanical keyboard with Cherry MX switches",
                base_price=450000,  # ₹4500
                currency="INR",
                delivery_days=3,
                stock=50,
                spec={"switch_type": "Cherry MX Red", "backlight": "RGB", "layout": "TKL"},
            ),
            Product(
                merchant_id=merchant1.id,
                name="Wireless Mouse Pro",
                category="Electronics",
                description="Ergonomic wireless mouse with 25600 DPI",
                base_price=280000,  # ₹2800
                currency="INR",
                delivery_days=2,
                stock=100,
                spec={"dpi": 25600, "connectivity": "2.4GHz + Bluetooth", "battery_life": "70 hours"},
            ),
            Product(
                merchant_id=merchant1.id,
                name="USB-C Hub 7-in-1",
                category="Electronics",
                description="7-port USB-C hub with HDMI, USB-A, SD card reader",
                base_price=180000,  # ₹1800
                currency="INR",
                delivery_days=2,
                stock=75,
                spec={"ports": ["HDMI 4K", "USB-A 3.0 x3", "USB-C PD", "SD", "microSD"]},
            ),
            Product(
                merchant_id=merchant1.id,
                name="Monitor 27\" 4K",
                category="Electronics",
                description="27-inch 4K IPS monitor with HDR400",
                base_price=3500000,  # ₹35000
                currency="INR",
                delivery_days=5,
                stock=20,
                spec={"resolution": "3840x2160", "panel": "IPS", "refresh_rate": "60Hz", "hdr": "HDR400"},
            ),
            Product(
                merchant_id=merchant1.id,
                name="Webcam 1080p",
                category="Electronics",
                description="Full HD webcam with privacy cover",
                base_price=350000,  # ₹3500
                currency="INR",
                delivery_days=2,
                stock=60,
                spec={"resolution": "1080p@30fps", "fov": "78°", "microphone": "dual stereo"},
            ),
        ]

        # Products for BookWorm Books
        products_merchant2 = [
            Product(
                merchant_id=merchant2.id,
                name="Clean Code",
                category="Books",
                description="A Handbook of Agile Software Craftsmanship by Robert Martin",
                base_price=45000,  # ₹450
                currency="INR",
                delivery_days=3,
                stock=200,
                spec={"author": "Robert C. Martin", "pages": 464, "publisher": "Prentice Hall"},
            ),
            Product(
                merchant_id=merchant2.id,
                name="Design Patterns",
                category="Books",
                description="Elements of Reusable Object-Oriented Software by GoF",
                base_price=55000,  # ₹550
                currency="INR",
                delivery_days=3,
                stock=150,
                spec={"authors": ["Erich Gamma", "Richard Helm", "Ralph Johnson", "John Vlissides"], "pages": 395},
            ),
            Product(
                merchant_id=merchant2.id,
                name="System Design Interview",
                category="Books",
                description="An Insider's Guide by Alex Xu",
                base_price=40000,  # ₹400
                currency="INR",
                delivery_days=2,
                stock=180,
                spec={"author": "Alex Xu", "pages": 370, "volume": 1},
            ),
            Product(
                merchant_id=merchant2.id,
                name="Python Tricks",
                category="Books",
                description="A Buffet of Awesome Python Features by Dan Bader",
                base_price=35000,  # ₹350
                currency="INR",
                delivery_days=2,
                stock=200,
                spec={"author": "Dan Bader", "pages": 302},
            ),
            Product(
                merchant_id=merchant2.id,
                name="A4 Premium Notebook",
                category="Office supplies",
                description="Premium dotted notebook 192 pages",
                base_price=25000,  # ₹250
                currency="INR",
                delivery_days=1,
                stock=300,
                spec={"size": "A4", "pages": 192, "paper": "100gsm", "binding": "lay-flat"},
            ),
            Product(
                merchant_id=merchant2.id,
                name="Gel Pen Set 12pcs",
                category="Office supplies",
                description="Smooth writing gel pens assorted colors",
                base_price=15000,  # ₹150
                currency="INR",
                delivery_days=1,
                stock=500,
                spec={"count": 12, "tip": "0.5mm", "colors": "assorted"},
            ),
        ]

        all_products = products_merchant1 + products_merchant2
        for p in all_products:
            session.add(p)
        await session.flush()

        # Add pricing tiers for Mechanical Keyboard (product 1) - for negotiation demo
        keyboard = products_merchant1[0]
        pricing_tiers = [
            MerchantPricingTier(
                product_id=keyboard.id,
                merchant_id=merchant1.id,
                min_qty=1,
                max_qty=4,
                unit_price=450000,
            ),
            MerchantPricingTier(
                product_id=keyboard.id,
                merchant_id=merchant1.id,
                min_qty=5,
                max_qty=9,
                unit_price=420000,  # ~7% discount
            ),
            MerchantPricingTier(
                product_id=keyboard.id,
                merchant_id=merchant1.id,
                min_qty=10,
                max_qty=19,
                unit_price=390000,  # ~13% discount
            ),
            MerchantPricingTier(
                product_id=keyboard.id,
                merchant_id=merchant1.id,
                min_qty=20,
                max_qty=None,
                unit_price=360000,  # 20% discount
            ),
        ]
        for tier in pricing_tiers:
            session.add(tier)

        await session.commit()
        print("Database seeded successfully!")
        print(f"Created user: {user.email}")
        print(f"Created {len(all_products)} products across 2 merchants")
        print(f"Created pricing tiers for '{keyboard.name}'")


if __name__ == "__main__":
    asyncio.run(seed())