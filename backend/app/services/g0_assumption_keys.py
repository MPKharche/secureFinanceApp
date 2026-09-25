"""G4 Assumptions Glossary v1 — stable key names for money.planetfinance.cloud.

Source of truth: Notion «G4 Assumptions Glossary». Keys never rename when values
refresh; calc/post paths read the map — no literal rates/amounts in services.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

# --- G1 (balance sheet / reporting) ---
KEY_REPORTING_CURRENCY = "reporting_currency"
KEY_INSURANCE_VALUE_BASIS = "insurance_value_basis"
KEY_INCLUDE_POLICY_LOAN = "include_policy_loan"
KEY_AS_OF_FIDELITY = "as_of_fidelity"

# --- Debt anchors (G1 liability placeholders / seeds) ---
KEY_NRP_LOAN_ID_LABEL = "nrp_loan_id_label"
KEY_NRP_OUTSTANDING = "nrp_outstanding"
KEY_PERSONAL_LOAN_EMI = "personal_loan_emi"
KEY_LAS_OUTSTANDING = "las_outstanding"

# --- Pru G0 anchors (ledger seeds) ---
KEY_PRU_POLICY_ID = "pru_policy_id"
KEY_PRU_LOAN_OUTSTANDING = "pru_loan_outstanding"
KEY_PRU_LOAN_HAS_EMI = "pru_loan_has_emi"
KEY_PRU_SV_ILLUSTRATIVE = "pru_sv_illustrative"
KEY_PRU_LOAN_CAP_PCT_OF_SV = "pru_loan_cap_pct_of_sv"

# Operational wiring (UUIDs / FKs — not glossary economics keys)
WIRING_LOAN_ACCOUNT_ID = "loan_account_id"
WIRING_CASH_ACCOUNT_ID = "cash_account_id"
WIRING_LINKED_PREMIUM_RECURRING_ID = "linked_premium_recurring_id"
WIRING_LINKED_INTEREST_RECURRING_ID = "linked_interest_recurring_id"
WIRING_LINKED_REPAYMENT_RECURRING_ID = "linked_repayment_recurring_id"

# Legacy blob field → canonical glossary key (read path only)
_LEGACY_G0_FIELD_MAP: dict[str, str] = {
    "outstanding_total_asof": KEY_PRU_LOAN_OUTSTANDING,
    "no_emi": KEY_PRU_LOAN_HAS_EMI,
    "premium_amount": "pru_premium_monthly_inr",  # seed-only until KM adds to glossary
    "loan_rate_percent": "pru_loan_rate_pct",  # seed-only helper; prefer account.interest_rate
    "interest_amount_half_yearly": "pru_interest_half_yearly_inr",
    "principal": "pru_loan_principal_inr",
}

DEFAULT_PLACEHOLDER_LABELS: dict[str, str] = {
    KEY_PRU_LOAN_OUTSTANDING: "Pru loan O/S — placeholder (refresh from statement)",
    KEY_PRU_SV_ILLUSTRATIVE: "Pru SV — illustrative only, not live ICICI quote",
    KEY_NRP_OUTSTANDING: "NRP O/S — refresh from live schedule",
    KEY_PERSONAL_LOAN_EMI: "PL EMI — awaiting statement",
    KEY_LAS_OUTSTANDING: "LAS O/S — awaiting statement",
    "pru_premium_monthly_inr": "Premium — seeded; confirm against policy debit",
    "pru_interest_half_yearly_inr": "Half-yearly interest — seeded; confirm against schedule",
}


def placeholder_label_for_key(
    key: str,
    assumption_meta: dict[str, Any],
) -> str | None:
    """Return UI label when key is a placeholder; None if not placeholder/disclosed."""
    spec = assumption_meta.get(key)
    if isinstance(spec, dict):
        if spec.get("status") != "placeholder":
            return None
        return spec.get("label") or DEFAULT_PLACEHOLDER_LABELS.get(key, key)
    if spec == "placeholder":
        return DEFAULT_PLACEHOLDER_LABELS.get(key, key)
    return None


def is_placeholder_key(key: str, assumption_meta: dict[str, Any]) -> bool:
    spec = assumption_meta.get(key)
    if isinstance(spec, dict):
        return spec.get("status") == "placeholder"
    return spec == "placeholder"


def assumptions_from_metadata(meta: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Single Assumptions map from asset/goal metadata (canonical + legacy merge)."""
    if not meta:
        return {}
    if meta.get("assumptions"):
        base = dict(meta["assumptions"])
    else:
        base = {}
    legacy = meta.get("g0_assumptions") or {}
    for old_key, canon in _LEGACY_G0_FIELD_MAP.items():
        if old_key in legacy and canon not in base:
            val = legacy[old_key]
            if old_key == "no_emi":
                base[KEY_PRU_LOAN_HAS_EMI] = not bool(val)
            elif old_key == "loan_rate_percent":
                try:
                    base[canon] = float(val) / 100.0
                except (TypeError, ValueError):
                    pass
            else:
                base[canon] = val
    for key in (
        KEY_PRU_POLICY_ID,
        KEY_PRU_LOAN_OUTSTANDING,
        KEY_PRU_LOAN_HAS_EMI,
        KEY_PRU_SV_ILLUSTRATIVE,
        KEY_PRU_LOAN_CAP_PCT_OF_SV,
        KEY_REPORTING_CURRENCY,
        KEY_INSURANCE_VALUE_BASIS,
        KEY_INCLUDE_POLICY_LOAN,
    ):
        if key in legacy and key not in base:
            base[key] = legacy[key]
    return base


def wiring_from_metadata(meta: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not meta:
        return {}
    if meta.get("g0_wiring"):
        return dict(meta["g0_wiring"])
    legacy = meta.get("g0_assumptions") or {}
    out: dict[str, Any] = {}
    for k in (
        WIRING_LOAN_ACCOUNT_ID,
        WIRING_CASH_ACCOUNT_ID,
        WIRING_LINKED_PREMIUM_RECURRING_ID,
        WIRING_LINKED_INTEREST_RECURRING_ID,
        WIRING_LINKED_REPAYMENT_RECURRING_ID,
    ):
        if k in legacy:
            out[k] = legacy[k]
    return out


def assumption_meta_from_metadata(meta: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Status/label sidecar for placeholder rendering (not silent zero)."""
    if not meta:
        return {}
    return dict(meta.get("assumption_meta") or meta.get("assumption_status") or {})


def assumption_value(assumptions: dict[str, Any], key: str) -> Any:
    return assumptions.get(key)


def assumption_refs_for_post(assumptions: dict[str, Any]) -> dict[str, Any]:
    """Snapshot glossary keys stamped on ledger raw_data (values may refresh later)."""
    refs: dict[str, Any] = {}
    for key in (
        KEY_PRU_POLICY_ID,
        KEY_PRU_LOAN_OUTSTANDING,
        KEY_PRU_LOAN_HAS_EMI,
        KEY_PRU_SV_ILLUSTRATIVE,
        KEY_PRU_LOAN_CAP_PCT_OF_SV,
        KEY_REPORTING_CURRENCY,
        KEY_INSURANCE_VALUE_BASIS,
        KEY_INCLUDE_POLICY_LOAN,
    ):
        if key in assumptions:
            refs[key] = assumptions[key]
    return refs


def disclosure_labels_for_post(
    assumptions: dict[str, Any], meta_sidecar: dict[str, Any]
) -> list[dict[str, str]]:
    """UI-facing placeholder labels for keys touched on post (not silent zero)."""
    out: list[dict[str, str]] = []
    for key, spec in meta_sidecar.items():
        if isinstance(spec, dict):
            status = spec.get("status", "")
            label = spec.get("label") or DEFAULT_PLACEHOLDER_LABELS.get(key, key)
        else:
            status = str(spec)
            label = DEFAULT_PLACEHOLDER_LABELS.get(key, key)
        if status == "placeholder" and key in assumptions:
            out.append({"key": key, "label": label})
    return out


def posting_amount_inr(
    *,
    kind: str,
    recurring_amount: Decimal,
    assumptions: dict[str, Any],
    schedule_emi_amount: Optional[Decimal] = None,
    loan_original_principal: Optional[Decimal] = None,
) -> Decimal:
    """Resolve post amount from ledger/schedule/recurring — never hard-coded literals."""
    if schedule_emi_amount is not None:
        return schedule_emi_amount.quantize(Decimal("0.01"))
    if kind == "principal_repayment" and loan_original_principal is not None:
        return loan_original_principal.quantize(Decimal("0.01"))
    if recurring_amount is not None and recurring_amount > 0:
        return recurring_amount.quantize(Decimal("0.01"))
    helper_key = {
        "premium": "pru_premium_monthly_inr",
        "interest_half_yearly": "pru_interest_half_yearly_inr",
        "principal_repayment": "pru_loan_principal_inr",
    }.get(kind)
    if helper_key and helper_key in assumptions:
        return Decimal(str(assumptions[helper_key])).quantize(Decimal("0.01"))
    return Decimal("0.00")


# Back-compat aliases used by earlier G0 PR code
assumption_refs_from_g0 = assumption_refs_for_post


def amount_from_g0_assumption(
    g0: Optional[dict[str, Any]], *, kind: str, fallback: Decimal
) -> Decimal:
    assumptions = assumptions_from_metadata({"g0_assumptions": g0} if g0 else {})
    return posting_amount_inr(
        kind=kind,
        recurring_amount=fallback,
        assumptions=assumptions,
    )
