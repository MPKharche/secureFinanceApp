"""Combined plan invest-elsewhere parity helpers."""
from datetime import date
from decimal import Decimal

from app.services.loan_combined_simulation_service import (
    ScenarioEvent,
    summarize,
    walk_amortization,
)
from app.services.loan_simulation_service import invest_elsewhere_compare


def test_combined_extras_feed_invest_elsewhere():
    steps = walk_amortization(
        principal=Decimal("500000"),
        annual_rate=Decimal("8"),
        emi=Decimal("6000"),
        start_date=date(2026, 1, 1),
        emi_day=5,
        events=[
            ScenarioEvent(
                type="one_time_prepayment",
                date=date(2026, 2, 5),
                amount=Decimal("50000"),
                label="Bonus",
            )
        ],
        strategy="reduce_tenure",
        max_months=240,
    )
    base = walk_amortization(
        principal=Decimal("500000"),
        annual_rate=Decimal("8"),
        emi=Decimal("6000"),
        start_date=date(2026, 1, 1),
        emi_day=5,
        events=[],
        strategy="reduce_tenure",
        max_months=240,
    )
    base_sum = summarize(base, Decimal("6000"), Decimal("8"))
    scen_sum = summarize(steps, Decimal("6000"), Decimal("8"))
    total_extra = sum((s.extra_principal for s in steps), Decimal("0"))
    interest_saved = Decimal(str(base_sum["total_interest"])) - Decimal(
        str(scen_sum["total_interest"])
    )
    cmp = invest_elsewhere_compare(
        total_extra, interest_saved, base_sum["months"], Decimal("7"), Decimal("0")
    )
    assert total_extra >= Decimal("50000")
    assert interest_saved > 0
    assert "prefer_prepay" in cmp
    assert cmp["horizon_months"] == base_sum["months"]
