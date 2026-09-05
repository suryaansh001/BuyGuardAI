from app.policy.models import BuyerPolicy, PolicyEvaluation, PolicyResult


def evaluate(
    category: str,
    amount: int,
    merchant_id: int,
    spent_today: int,
    policy: BuyerPolicy,
) -> PolicyEvaluation:
    if category in policy.blocked_categories:
        return PolicyEvaluation(PolicyResult.BLOCKED, "Category is blocked")

    if category not in policy.allowed_categories:
        return PolicyEvaluation(PolicyResult.BLOCKED, "Category not in allow-list")

    if policy.allowed_merchant_ids is not None and merchant_id not in policy.allowed_merchant_ids:
        return PolicyEvaluation(PolicyResult.BLOCKED, "Merchant not allowed")

    if amount > policy.max_transaction_amount:
        return PolicyEvaluation(PolicyResult.BLOCKED, "Exceeds max transaction amount")

    if spent_today + amount > policy.daily_spending_limit:
        return PolicyEvaluation(PolicyResult.BLOCKED, "Exceeds daily spending limit")

    if amount > policy.approval_required_above:
        return PolicyEvaluation(PolicyResult.NEEDS_APPROVAL, "Above auto-approval threshold")

    return PolicyEvaluation(PolicyResult.ALLOWED, "Within policy")