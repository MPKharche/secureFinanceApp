from decimal import Decimal

from app.services.g0_assumption_keys import (
    KEY_LAS_OUTSTANDING,
    KEY_PRU_LOAN_CAP_PCT_OF_SV,
    KEY_PRU_LOAN_HAS_EMI,
    KEY_PRU_LOAN_OUTSTANDING,
    KEY_PRU_POLICY_ID,
    KEY_PRU_SV_ILLUSTRATIVE,
    KEY_REPORTING_CURRENCY,
    assumption_refs_for_post,
    assumptions_from_metadata,
    disclosure_labels_for_post,
    is_placeholder_key,
    placeholder_label_for_key,
    posting_amount_inr,
)


def test_assumptions_from_metadata_glossary_v1():
    meta = {
        "assumptions": {
            "pru_policy_id": "A8884526",
            "pru_loan_outstanding": 174805,
            "pru_loan_has_emi": False,
            "pru_sv_illustrative": 389495,
            "pru_loan_cap_pct_of_sv": 0.80,
            "reporting_currency": "INR",
            "insurance_value_basis": "sv",
            "include_policy_loan": True,
        }
    }
    a = assumptions_from_metadata(meta)
    assert a[KEY_PRU_POLICY_ID] == "A8884526"
    assert a[KEY_PRU_LOAN_HAS_EMI] is False
    assert a[KEY_PRU_LOAN_CAP_PCT_OF_SV] == 0.80


def test_assumption_refs_use_exact_glossary_key_names():
    assumptions = {
        KEY_PRU_POLICY_ID: "A8884526",
        KEY_PRU_LOAN_OUTSTANDING: 174805,
        KEY_REPORTING_CURRENCY: "INR",
    }
    refs = assumption_refs_for_post(assumptions)
    assert "g0.loan_rate_percent" not in refs
    assert refs[KEY_PRU_POLICY_ID] == "A8884526"


def test_placeholder_disclosures_not_silent():
    assumptions = {KEY_PRU_SV_ILLUSTRATIVE: 389495}
    meta = {
        KEY_PRU_SV_ILLUSTRATIVE: {
            "status": "placeholder",
            "label": "SV illustrative — not live quote",
        }
    }
    labels = disclosure_labels_for_post(assumptions, meta)
    assert labels[0]["key"] == KEY_PRU_SV_ILLUSTRATIVE
    assert "live" in labels[0]["label"].lower()


def test_placeholder_label_for_debt_keys():
    meta = {
        KEY_LAS_OUTSTANDING: {
            "status": "placeholder",
            "label": "LAS — need stmt",
        }
    }
    assert is_placeholder_key(KEY_LAS_OUTSTANDING, meta)
    assert placeholder_label_for_key(KEY_LAS_OUTSTANDING, meta) == "LAS — need stmt"


def test_posting_amount_prefers_recurring_not_hardcoded():
    assumptions = {"pru_premium_monthly_inr": 99999}
    assert posting_amount_inr(
        kind="premium",
        recurring_amount=Decimal("10000"),
        assumptions=assumptions,
    ) == Decimal("10000.00")
