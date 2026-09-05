from dataclasses import dataclass
from enum import Enum


class PolicyResult(str, Enum):
    ALLOWED = "ALLOWED"
    BLOCKED = "BLOCKED"
    NEEDS_APPROVAL = "NEEDS_APPROVAL"


@dataclass(frozen=True)
class BuyerPolicy:
    max_transaction_amount: int
    daily_spending_limit: int
    approval_required_above: int
    allowed_categories: set[str]
    blocked_categories: set[str]
    allowed_merchant_ids: set[int] | None = None


@dataclass(frozen=True)
class PolicyEvaluation:
    result: PolicyResult
    reason: str