"""G4-lite assumption key hooks for G0 policy-loan posting (KM glossary owns rates later)."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

# Stable keys referenced from transaction raw_data and asset g0_assumptions blobs.
KEY_LOAN_RATE_PERCENT = "g0.loan_rate_percent"
KEY_INTEREST_HALF_YEARLY = "g0.interest_amount_half_yearly"
KEY_PREMIUM_AMOUNT = "g0.premium_amount"
KEY_PRINCIPAL = "g0.principal"
KEY_INTEREST_CADENCE = "g0.interest_cadence"


def assumption_refs_from_g0(g0: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Map g0_assumptions fields to KM-style assumption refs for ledger provenance."""
    if not g0:
        return {}
    refs: dict[str, Any] = {}
    if g0.get("loan_rate_percent") is not None:
        refs[KEY_LOAN_RATE_PERCENT] = g0["loan_rate_percent"]
    if g0.get("interest_amount_half_yearly") is not None:
        refs[KEY_INTEREST_HALF_YEARLY] = g0["interest_amount_half_yearly"]
    if g0.get("premium_amount") is not None:
        refs[KEY_PREMIUM_AMOUNT] = g0["premium_amount"]
    if g0.get("principal") is not None:
        refs[KEY_PRINCIPAL] = g0["principal"]
    if g0.get("interest_cadence") is not None:
        refs[KEY_INTEREST_CADENCE] = g0["interest_cadence"]
    return refs


def amount_from_g0_assumption(
    g0: Optional[dict[str, Any]], *, kind: str, fallback: Decimal
) -> Decimal:
    """Prefer seeded assumption amounts when posting (avoid hard-coded recompute drift)."""
    if not g0:
        return fallback
    if kind == "premium" and g0.get("premium_amount") is not None:
        return Decimal(str(g0["premium_amount"]))
    if kind == "interest_half_yearly" and g0.get("interest_amount_half_yearly") is not None:
        return Decimal(str(g0["interest_amount_half_yearly"]))
    if kind == "principal_repayment" and g0.get("principal") is not None:
        return Decimal(str(g0["principal"]))
    return fallback
