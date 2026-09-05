import pytest
from app.policy.engine import evaluate
from app.policy.models import BuyerPolicy, PolicyResult


@pytest.fixture
def sample_policy() -> BuyerPolicy:
    return BuyerPolicy(
        max_transaction_amount=500000,
        daily_spending_limit=1000000,
        approval_required_above=300000,
        allowed_categories={"Electronics", "Books", "Office supplies"},
        blocked_categories={"Gambling", "Adult"},
        allowed_merchant_ids={1, 2},
    )


def test_blocked_category(sample_policy):
    result = evaluate(
        category="Gambling",
        amount=100000,
        merchant_id=1,
        spent_today=0,
        policy=sample_policy,
    )
    assert result.result == PolicyResult.BLOCKED
    assert "blocked" in result.reason.lower()


def test_not_allowed_category(sample_policy):
    result = evaluate(
        category="Clothing",
        amount=100000,
        merchant_id=1,
        spent_today=0,
        policy=sample_policy,
    )
    assert result.result == PolicyResult.BLOCKED
    assert "allow-list" in result.reason.lower()


def test_merchant_not_allowed(sample_policy):
    result = evaluate(
        category="Electronics",
        amount=100000,
        merchant_id=999,
        spent_today=0,
        policy=sample_policy,
    )
    assert result.result == PolicyResult.BLOCKED
    assert "merchant" in result.reason.lower()


def test_exceeds_max_transaction(sample_policy):
    result = evaluate(
        category="Electronics",
        amount=600000,
        merchant_id=1,
        spent_today=0,
        policy=sample_policy,
    )
    assert result.result == PolicyResult.BLOCKED
    assert "max transaction" in result.reason.lower()


def test_exceeds_daily_limit(sample_policy):
    result = evaluate(
        category="Electronics",
        amount=400000,
        merchant_id=1,
        spent_today=700000,
        policy=sample_policy,
    )
    assert result.result == PolicyResult.BLOCKED
    assert "daily" in result.reason.lower()


def test_needs_approval(sample_policy):
    result = evaluate(
        category="Electronics",
        amount=400000,
        merchant_id=1,
        spent_today=0,
        policy=sample_policy,
    )
    assert result.result == PolicyResult.NEEDS_APPROVAL
    assert "approval" in result.reason.lower()


def test_allowed_within_policy(sample_policy):
    result = evaluate(
        category="Electronics",
        amount=200000,
        merchant_id=1,
        spent_today=100000,
        policy=sample_policy,
    )
    assert result.result == PolicyResult.ALLOWED
    assert "within policy" in result.reason.lower()


def test_allowed_no_merchant_restriction():
    policy = BuyerPolicy(
        max_transaction_amount=500000,
        daily_spending_limit=1000000,
        approval_required_above=300000,
        allowed_categories={"Electronics"},
        blocked_categories=set(),
        allowed_merchant_ids=None,
    )
    result = evaluate(
        category="Electronics",
        amount=200000,
        merchant_id=999,
        spent_today=0,
        policy=policy,
    )
    assert result.result == PolicyResult.ALLOWED


def test_exact_max_transaction_needs_approval(sample_policy):
    result = evaluate(
        category="Electronics",
        amount=500000,
        merchant_id=1,
        spent_today=0,
        policy=sample_policy,
    )
    assert result.result == PolicyResult.NEEDS_APPROVAL


def test_exact_approval_threshold_allowed(sample_policy):
    result = evaluate(
        category="Electronics",
        amount=300000,
        merchant_id=1,
        spent_today=0,
        policy=sample_policy,
    )
    assert result.result == PolicyResult.ALLOWED