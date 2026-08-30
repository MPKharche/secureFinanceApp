"""Account-type helpers shared by services (liability vs cash)."""

from __future__ import annotations

LIABILITY_ACCOUNT_TYPES = frozenset({"credit_card", "loan"})
LOAN_KINDS = frozenset({"home", "personal", "auto", "education", "gold", "other"})


def is_liability_account_type(account_type: str | None) -> bool:
    return account_type in LIABILITY_ACCOUNT_TYPES
