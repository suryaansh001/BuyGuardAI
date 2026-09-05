from datetime import datetime, date
from enum import Enum as PyEnum
from typing import Optional, List
from sqlalchemy import (
    String,
    Integer,
    ForeignKey,
    Index,
    Enum,
    Enum as SQLEnum,
    DateTime,
    Date,
    Text,
    UniqueConstraint,
    JSON,
    func,
    Boolean,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from app.db.session import Base


class PurchaseIntentStatus(str, PyEnum):
    DRAFT = "DRAFT"
    POLICY_CHECKED = "POLICY_CHECKED"
    ALLOWED = "ALLOWED"
    BLOCKED = "BLOCKED"
    NEEDS_APPROVAL = "NEEDS_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PAID = "PAID"
    FAILED = "FAILED"


class TransactionStatus(str, PyEnum):
    CREATED = "CREATED"
    PAID = "PAID"
    FAILED = "FAILED"


class PaymentStatus(str, PyEnum):
    CAPTURED = "CAPTURED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class ApprovalStatus(str, PyEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class NegotiationStatus(str, PyEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    buyer_policy: Mapped[Optional["BuyerPolicy"]] = relationship(back_populates="user", uselist=False)
    purchase_intents: Mapped[List["PurchaseIntent"]] = relationship(back_populates="user")


class BuyerPolicy(Base):
    __tablename__ = "buyer_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    max_transaction_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    daily_spending_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    approval_required_above: Mapped[int] = mapped_column(Integer, nullable=False)
    allowed_categories: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=[])
    blocked_categories: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=[])
    allowed_merchant_ids: Mapped[Optional[List[int]]] = mapped_column(ARRAY(Integer), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="buyer_policy")


class Merchant(Base):
    __tablename__ = "merchants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_permissions: Mapped[dict] = mapped_column(JSONB, nullable=False, default={})
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    products: Mapped[List["Product"]] = relationship(back_populates="merchant")
    pricing_tiers: Mapped[List["MerchantPricingTier"]] = relationship(back_populates="merchant")
    merchant_policy: Mapped[Optional["MerchantPolicy"]] = relationship(back_populates="merchant", uselist=False)
    purchase_intents: Mapped[List["PurchaseIntent"]] = relationship(back_populates="merchant")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    merchant_id: Mapped[int] = mapped_column(Integer, ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    base_price: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    delivery_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    spec: Mapped[dict] = mapped_column(JSONB, nullable=False, default={})
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    merchant: Mapped["Merchant"] = relationship(back_populates="products")
    pricing_tiers: Mapped[List["MerchantPricingTier"]] = relationship(back_populates="product")
    purchase_intents: Mapped[List["PurchaseIntent"]] = relationship(back_populates="product")

    __table_args__ = (
        Index("ix_product_merchant_category", "merchant_id", "category"),
        Index("ix_product_category_price", "category", "base_price"),
    )


class MerchantPricingTier(Base):
    __tablename__ = "merchant_pricing_tiers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    merchant_id: Mapped[int] = mapped_column(Integer, ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False)
    min_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    max_qty: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    product: Mapped["Product"] = relationship(back_populates="pricing_tiers")
    merchant: Mapped["Merchant"] = relationship(back_populates="pricing_tiers")


class MerchantPolicy(Base):
    __tablename__ = "merchant_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    merchant_id: Mapped[int] = mapped_column(Integer, ForeignKey("merchants.id", ondelete="CASCADE"), unique=True, nullable=False)
    negotiation_floor_pct: Mapped[float] = mapped_column(nullable=False, default=0.8)
    agent_transaction_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    merchant: Mapped["Merchant"] = relationship(back_populates="merchant_policy")


class PurchaseIntent(Base):
    __tablename__ = "purchase_intents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    merchant_id: Mapped[int] = mapped_column(Integer, ForeignKey("merchants.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PurchaseIntentStatus] = mapped_column(Enum(PurchaseIntentStatus), nullable=False, default=PurchaseIntentStatus.DRAFT)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    policy_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="purchase_intents")
    product: Mapped["Product"] = relationship(back_populates="purchase_intents")
    merchant: Mapped["Merchant"] = relationship(back_populates="purchase_intents")
    transaction: Mapped[Optional["Transaction"]] = relationship(back_populates="purchase_intent", uselist=False)
    negotiation: Mapped[Optional["Negotiation"]] = relationship(back_populates="purchase_intent", uselist=False)
    approval_request: Mapped[Optional["ApprovalRequest"]] = relationship(back_populates="purchase_intent", uselist=False)

    __table_args__ = (
        Index("ix_purchase_intent_user_created", "user_id", "created_at"),
    )


class Negotiation(Base):
    __tablename__ = "negotiations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    purchase_intent_id: Mapped[int] = mapped_column(Integer, ForeignKey("purchase_intents.id", ondelete="CASCADE"), unique=True, nullable=False)
    requested_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    offered_price: Mapped[int] = mapped_column(Integer, nullable=False)
    countered_price: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    accepted: Mapped[Optional[bool]] = mapped_column(nullable=True)
    merchant_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    purchase_intent: Mapped["PurchaseIntent"] = relationship(back_populates="negotiation")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    purchase_intent_id: Mapped[int] = mapped_column(Integer, ForeignKey("purchase_intents.id", ondelete="CASCADE"), unique=True, nullable=False)
    razorpay_order_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    status: Mapped[TransactionStatus] = mapped_column(Enum(TransactionStatus), nullable=False, default=TransactionStatus.CREATED)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    purchase_intent: Mapped["PurchaseIntent"] = relationship(back_populates="transaction")
    payments: Mapped[List["Payment"]] = relationship(back_populates="transaction")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)
    razorpay_payment_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), nullable=False)
    method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    raw_webhook_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default={})
    received_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    transaction: Mapped["Transaction"] = relationship(back_populates="payments")


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    purchase_intent_id: Mapped[int] = mapped_column(Integer, ForeignKey("purchase_intents.id", ondelete="CASCADE"), unique=True, nullable=False)
    status: Mapped[ApprovalStatus] = mapped_column(Enum(ApprovalStatus), nullable=False, default=ApprovalStatus.PENDING)
    requested_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    purchase_intent: Mapped["PurchaseIntent"] = relationship(back_populates="approval_request")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    purchase_intent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("purchase_intents.id", ondelete="SET NULL"), nullable=True)
    actor: Mapped[str] = mapped_column(String(50), nullable=False)
    event: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default={})
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_audit_log_intent_created", "purchase_intent_id", "created_at"),
    )


class CampaignStatus(str, PyEnum):
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class CampaignType(str, PyEnum):
    PROMOTION = "PROMOTION"
    FLASH_SALE = "FLASH_SALE"
    SEASONAL = "SEASONAL"
    CLEARANCE = "CLEARANCE"
    NEW_ARRIVAL = "NEW_ARRIVAL"
    CUSTOM = "CUSTOM"


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    campaign_type: Mapped[CampaignType] = mapped_column(SQLEnum(CampaignType), nullable=False, default=CampaignType.PROMOTION)
    status: Mapped[CampaignStatus] = mapped_column(SQLEnum(CampaignStatus), nullable=False, default=CampaignStatus.DRAFT)

    # Scheduling
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Targeting
    target_categories: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    target_merchants: Mapped[Optional[List[int]]] = mapped_column(ARRAY(Integer), nullable=True)
    min_order_value_paise: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_discount_pct: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Discount configuration
    discount_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    discount_value: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    buy_x_get_y_config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Budget & limits
    budget_paise: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_uses: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_uses_per_customer: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    spent_paise: Mapped[int] = mapped_column(Integer, default=0)

    # Conditions
    min_order_value_paise: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    applicable_categories: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    excluded_categories: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    applicable_products: Mapped[Optional[List[int]]] = mapped_column(ARRAY(Integer), nullable=True)
    excluded_products: Mapped[Optional[List[int]]] = mapped_column(ARRAY(Integer), nullable=True)
    min_quantity: Mapped[int] = mapped_column(Integer, default=1)

    # Customer targeting
    new_customers_only: Mapped[bool] = mapped_column(Boolean, default=False)
    customer_segments: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    requires_coupon_code: Mapped[bool] = mapped_column(Boolean, default=False)
    coupon_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, unique=True)

    # Metadata
    created_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    usages = relationship("CampaignUsage", back_populates="campaign")


class CampaignUsage(Base):
    __tablename__ = "campaign_usages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    purchase_intent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("purchase_intents.id", ondelete="SET NULL"), nullable=True)
    order_amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_paise: Mapped[int] = mapped_column(Integer, default=0)
    coupon_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    campaign: Mapped["Campaign"] = relationship(back_populates="usages")
    user: Mapped["User"] = relationship("User")


class CampaignRule(Base):
    __tablename__ = "campaign_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[int] = mapped_column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    rule_config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())