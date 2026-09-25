from decimal import Decimal

from app.services.g0_assumption_keys import (
    KEY_LOAN_RATE_PERCENT,
    amount_from_g0_assumption,
    assumption_refs_from_g0,
)


def test_assumption_refs_from_g0_maps_stable_keys():
    g0 = {
        "loan_rate_percent": 7.96,
        "premium_amount": 10000,
        "interest_amount_half_yearly": 6368,
        "principal": 160000,
        "interest_cadence": "half_yearly",
    }
    refs = assumption_refs_from_g0(g0)
    assert refs[KEY_LOAN_RATE_PERCENT] == 7.96
    assert refs["g0.premium_amount"] == 10000


def test_amount_from_g0_prefers_blob():
    g0 = {"premium_amount": 10000, "interest_amount_half_yearly": 6368.0}
    assert amount_from_g0_assumption(g0, kind="premium", fallback=Decimal("1")) == Decimal("10000")
    assert amount_from_g0_assumption(
        g0, kind="interest_half_yearly", fallback=Decimal("1")
    ) == Decimal("6368.0")
