"""Unit tests for rate dual-path, ladder, penalty, invest-elsewhere."""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.services.loan_simulation_service import (
    build_rate_ladder,
    calc_penalty,
    calculate_emi,
    default_penalty_assumption,
    invest_elsewhere_compare,
    rate_path_pair,
    tenure_from_emi,
    total_interest_at,
)


def test_calculate_emi_basic():
    emi = calculate_emi(Decimal("100000"), Decimal("12"), 12)
    assert emi > Decimal("8000")
    assert emi < Decimal("9000")


def test_tenure_from_emi_roundtrip():
    principal = Decimal("500000")
    rate = Decimal("8.5")
    months = 120
    emi = calculate_emi(principal, rate, months)
    n = tenure_from_emi(principal, rate, emi)
    assert abs(n - months) <= 1


def test_negative_amortisation_when_emi_too_low():
    # EMI below monthly interest at 24% on 1L
    n = tenure_from_emi(Decimal("100000"), Decimal("24"), Decimal("1000"))
    assert n == 0


def test_rate_cut_keep_emi_usually_wins():
    outstanding = Decimal("1000000")
    rate = Decimal("9.00")
    months = 180
    emi = calculate_emi(outstanding, rate, months)
    pair = rate_path_pair(outstanding, rate, emi, months, Decimal("8.00"))
    assert pair["is_rate_cut"] is True
    assert pair["keep_emi"]["delta_months"] is not None
    assert pair["keep_emi"]["delta_months"] < 0
    assert pair["keep_duration"]["delta_emi"] < 0
    # Tenure cut saves at least as much interest as EMI cut (usually more)
    assert pair["keep_emi"]["interest_saved"] >= pair["keep_duration"]["interest_saved"] - 1.0
    assert pair["recommended"] == "keep_emi"
    assert pair["tenure_cut_usually_wins"] is True


def test_rate_hike_flags_both_paths():
    outstanding = Decimal("1000000")
    rate = Decimal("8.00")
    months = 120
    emi = calculate_emi(outstanding, rate, months)
    pair = rate_path_pair(outstanding, rate, emi, months, Decimal("10.00"))
    assert pair["is_rate_hike"] is True
    assert pair["keep_duration"]["delta_emi"] > 0
    assert pair["keep_emi"]["delta_months"] is not None
    assert pair["keep_emi"]["delta_months"] > 0


def test_rate_hike_negative_amort_when_emi_stuck():
    outstanding = Decimal("100000")
    # Tiny EMI relative to a huge hike
    pair = rate_path_pair(
        outstanding, Decimal("8"), Decimal("500"), 120, Decimal("30")
    )
    assert pair["keep_emi"]["negative_amortisation"] is True
    assert pair["negative_amortisation_risk"] is True


def test_rate_ladder_steps():
    outstanding = Decimal("10669593")
    rate = Decimal("7.75")
    months = 130
    emi = calculate_emi(outstanding, rate, months)
    rows = build_rate_ladder(outstanding, rate, emi, months)
    steps = [r["rate_step"] for r in rows]
    assert -0.25 in steps
    assert -0.5 in steps
    assert -1.0 in steps
    assert 0.25 in steps
    assert 1.0 in steps
    for r in rows:
        assert "delta_months_if_emi_kept" in r
        assert "delta_emi_if_duration_kept" in r
        assert "net_extra_interest" in r


def test_penalty_basis_outstanding_vs_prepay():
    os_pen = calc_penalty(Decimal("2"), "outstanding", Decimal("100000"), Decimal("10000"))
    pp_pen = calc_penalty(Decimal("2"), "prepayment_amount", Decimal("100000"), Decimal("10000"))
    assert os_pen == Decimal("2000.00")
    assert pp_pen == Decimal("200.00")
    assert calc_penalty(Decimal("0"), "outstanding", Decimal("100000"), Decimal("10000")) == Decimal(
        "0.00"
    )


def test_nrp_penalty_default_not_zero():
    nrp = SimpleNamespace(
        display_name="ICICI NRP · 7.75% · Godrej Emerald Waters U114",
        name="TBPUN00006895113",
        loan_kind="home",
    )
    retail = SimpleNamespace(
        display_name="HDFC Home Loan floating",
        name="HL-123",
        loan_kind="home",
    )
    d_nrp = default_penalty_assumption(nrp)
    d_ret = default_penalty_assumption(retail)
    assert d_nrp["penalty_rate"] > 0
    assert d_nrp["reason"] == "commercial_or_nrp"
    assert d_ret["penalty_rate"] == 0.0


def test_invest_elsewhere_compare():
    cmp_ = invest_elsewhere_compare(
        Decimal("100000"),
        Decimal("80000"),
        60,
        Decimal("7"),
        Decimal("0"),
    )
    assert cmp_["alt_earnings"] > 0
    assert "prefer_prepay" in cmp_


def test_total_interest_positive():
    principal = Decimal("200000")
    rate = Decimal("10")
    months = 24
    emi = calculate_emi(principal, rate, months)
    interest = total_interest_at(principal, rate, months, emi)
    assert interest > 0


def test_invest_elsewhere_prefers_prepay_when_edge_positive():
    cmp = invest_elsewhere_compare(
        Decimal("100000"),
        Decimal("80000"),
        60,
        Decimal("7"),
        Decimal("2000"),
    )
    assert cmp["prepay_net_benefit"] == 78000.0
    assert "alt_earnings" in cmp
    assert isinstance(cmp["prefer_prepay"], bool)


def test_invest_elsewhere_zero_horizon():
    cmp = invest_elsewhere_compare(
        Decimal("10000"), Decimal("5000"), 0, Decimal("7"), Decimal("0")
    )
    assert cmp["alt_earnings"] == 0.0
    assert cmp["prepay_net_benefit"] == 5000.0
