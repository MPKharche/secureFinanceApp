"""Loan simulation service for rate / prepay / preclosure scenarios.

Statement-faithful: projections start from the live outstanding + remaining
schedule. Never regenerates or flattens phased disbursal / Pre-EMI / Pru
interest-only rows.
"""
from __future__ import annotations

import math
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.loan_schedule import LoanAmortizationSchedule

MONEY = Decimal("0.01")
DEFAULT_RATE_STEPS = (
    Decimal("-1.00"),
    Decimal("-0.50"),
    Decimal("-0.25"),
    Decimal("0.25"),
    Decimal("0.50"),
    Decimal("1.00"),
)
# Suggested alternate return when comparing "prepay vs invest elsewhere"
DEFAULT_ALT_RETURN_PCT = Decimal("7.00")


def calculate_emi(principal: Decimal, annual_rate: Decimal, months: int) -> Decimal:
    """Calculate EMI using the standard formula."""
    if months <= 0 or principal <= 0:
        return Decimal("0.00")

    if annual_rate == 0:
        return (principal / months).quantize(MONEY, rounding=ROUND_HALF_UP)

    monthly_rate = annual_rate / Decimal("1200")
    r = float(monthly_rate)
    n = months
    p = float(principal)

    emi = p * r * math.pow(1 + r, n) / (math.pow(1 + r, n) - 1)
    return Decimal(str(emi)).quantize(MONEY, rounding=ROUND_HALF_UP)


def tenure_from_emi(principal: Decimal, annual_rate: Decimal, emi: Decimal) -> int:
    """Months needed to clear principal at fixed EMI. 0 if EMI cannot cover interest."""
    if principal <= 0 or emi <= 0:
        return 0
    if annual_rate <= 0:
        return int(math.ceil(float(principal / emi)))

    monthly_rate = annual_rate / Decimal("1200")
    r = float(monthly_rate)
    emi_f = float(emi)
    p = float(principal)
    interest_only = p * r
    if emi_f <= interest_only + 1e-9:
        return 0  # negative / zero amortisation
    n = math.log(emi_f / (emi_f - p * r)) / math.log(1 + r)
    return max(1, int(math.ceil(n)))


def total_interest_at(
    principal: Decimal,
    annual_rate: Decimal,
    months: int,
    emi: Decimal,
) -> Decimal:
    """Walk amortisation and sum interest (caps at months or payoff)."""
    if principal <= 0 or months <= 0 or emi <= 0:
        return Decimal("0.00")
    monthly_rate = annual_rate / Decimal("1200") if annual_rate > 0 else Decimal("0")
    balance = principal
    total = Decimal("0.00")
    for _ in range(months):
        interest = (balance * monthly_rate).quantize(MONEY, rounding=ROUND_HALF_UP)
        principal_part = emi - interest
        if principal_part <= 0:
            # EMI does not cover interest — accrue and stop counting progress
            total += interest
            break
        if principal_part > balance:
            principal_part = balance
            interest = min(interest, emi)  # last row
        total += interest
        balance -= principal_part
        if balance <= Decimal("0.005"):
            break
    return total.quantize(MONEY, rounding=ROUND_HALF_UP)


def calc_penalty(
    penalty_rate: Decimal,
    penalty_basis: str,
    outstanding: Decimal,
    prepayment_amount: Decimal,
) -> Decimal:
    """Penalty = rate% of outstanding OR of the prepayment amount."""
    if penalty_rate is None or penalty_rate <= 0:
        return Decimal("0.00")
    basis = (penalty_basis or "outstanding").lower()
    base = outstanding if basis == "outstanding" else prepayment_amount
    if base <= 0:
        return Decimal("0.00")
    return (base * penalty_rate / Decimal("100")).quantize(MONEY, rounding=ROUND_HALF_UP)


def _is_interest_only(account: Account, future_entries: list) -> bool:
    """Pru / policy: no contractual EMI; schedule rows are interest-only."""
    if account.emi_amount is None or account.emi_amount <= 0:
        # Confirm via notes if present
        for e in future_entries[:3]:
            notes = (e.notes or "").lower()
            if "interest_only" in notes or "no_emi" in notes:
                return True
        # No EMI and remaining rows look interest-only (principal ~ 0)
        if future_entries:
            principals = [e.principal_component or Decimal("0") for e in future_entries[:6]]
            if principals and all(p <= Decimal("0.01") for p in principals):
                return True
        # Explicit no-EMI in display/notes
        blob = f"{account.display_name or ''} {account.name or ''}".lower()
        if "no emi" in blob or "no_emi" in blob or "interest-only" in blob or "interest only" in blob:
            return True
    return False


def _is_nrp_or_commercial(account: Account) -> bool:
    """NRP / commercial may still levy prepay penalty — never force zero."""
    blob = " ".join(
        [
            account.display_name or "",
            account.name or "",
            account.loan_kind or "",
        ]
    ).lower()
    markers = (
        "nrp",
        "commercial",
        "tbpun",
        "unit 114",
        "u114",
        "godrej emerald",
        "non-retail",
        "non retail",
    )
    return any(m in blob for m in markers)


def default_penalty_assumption(account: Account) -> dict:
    """G4 defaults: 0% OK for floating retail HL (RBI); NRP/commercial suggest 2% OS."""
    if _is_nrp_or_commercial(account):
        return {
            "penalty_rate": 2.0,
            "penalty_basis": "outstanding",
            "reason": "commercial_or_nrp",
            "editable": True,
        }
    return {
        "penalty_rate": 0.0,
        "penalty_basis": "outstanding",
        "reason": "floating_retail_hl_rbi",
        "editable": True,
    }


def _future_interest(entries: list) -> Decimal:
    return sum((e.interest_component or Decimal("0") for e in entries), Decimal("0.00"))


def rate_path_pair(
    outstanding: Decimal,
    current_rate: Decimal,
    current_emi: Decimal,
    remaining_months: int,
    new_rate: Decimal,
) -> dict:
    """Both alternatives for a rate change + negative-amortisation flag.

    keep_emi → tenure changes (bank trap: lenders often auto-cut EMI instead)
    keep_duration → EMI changes
    """
    baseline_interest = total_interest_at(
        outstanding, current_rate, remaining_months, current_emi
    )
    monthly_new = new_rate / Decimal("1200") if new_rate > 0 else Decimal("0")
    first_month_interest = (outstanding * monthly_new).quantize(MONEY, rounding=ROUND_HALF_UP)

    # --- Keep duration → change EMI ---
    new_emi = calculate_emi(outstanding, new_rate, remaining_months)
    interest_keep_duration = total_interest_at(
        outstanding, new_rate, remaining_months, new_emi
    )
    keep_duration = {
        "new_emi": float(new_emi),
        "delta_emi": float(new_emi - current_emi),
        "months": remaining_months,
        "delta_months": 0,
        "total_interest": float(interest_keep_duration),
        "interest_delta": float(interest_keep_duration - baseline_interest),
        "interest_saved": float(baseline_interest - interest_keep_duration),
    }

    # --- Keep EMI → change duration ---
    new_tenure = tenure_from_emi(outstanding, new_rate, current_emi)
    neg_amort = new_tenure == 0 and outstanding > 0 and current_emi > 0
    if neg_amort:
        # EMI cannot cover interest at new rate
        keep_emi = {
            "emi": float(current_emi),
            "delta_emi": 0.0,
            "new_tenure_months": None,
            "delta_months": None,
            "total_interest": None,
            "interest_delta": None,
            "interest_saved": None,
            "negative_amortisation": True,
            "monthly_interest": float(first_month_interest),
            "emi_shortfall": float(first_month_interest - current_emi),
        }
        interest_keep_emi = None
    else:
        tenure = new_tenure or remaining_months
        interest_keep_emi = total_interest_at(outstanding, new_rate, tenure, current_emi)
        keep_emi = {
            "emi": float(current_emi),
            "delta_emi": 0.0,
            "new_tenure_months": tenure,
            "delta_months": tenure - remaining_months,
            "total_interest": float(interest_keep_emi),
            "interest_delta": float(interest_keep_emi - baseline_interest),
            "interest_saved": float(baseline_interest - interest_keep_emi),
            "negative_amortisation": False,
        }

    # Tenure-cut usually wins on a rate cut (more interest saved)
    rate_cut = new_rate < current_rate
    winner = None
    if not neg_amort and interest_keep_emi is not None:
        if keep_emi["interest_saved"] > keep_duration["interest_saved"] + 0.01:
            winner = "keep_emi"
        elif keep_duration["interest_saved"] > keep_emi["interest_saved"] + 0.01:
            winner = "keep_duration"
        else:
            winner = "tie"

    return {
        "new_rate": float(new_rate),
        "rate_delta": float(new_rate - current_rate),
        "baseline_interest": float(baseline_interest),
        "keep_duration": keep_duration,
        "keep_emi": keep_emi,
        "recommended": "keep_emi" if rate_cut else None,
        "winner_interest": winner,
        "tenure_cut_usually_wins": rate_cut and winner == "keep_emi",
        "is_rate_cut": rate_cut,
        "is_rate_hike": new_rate > current_rate,
        "negative_amortisation_risk": bool(neg_amort) or (
            new_rate > current_rate and first_month_interest >= current_emi
        ),
    }


def build_rate_ladder(
    outstanding: Decimal,
    current_rate: Decimal,
    current_emi: Decimal,
    remaining_months: int,
    steps: Optional[list[Decimal]] = None,
) -> list[dict]:
    """Ready-reference rows for ±0.25 / ±0.5 / ±1.0 (etc.)."""
    steps = steps or list(DEFAULT_RATE_STEPS)
    rows = []
    for step in steps:
        new_rate = current_rate + step
        if new_rate < 0:
            continue
        pair = rate_path_pair(
            outstanding, current_rate, current_emi, remaining_months, new_rate
        )
        kd = pair["keep_duration"]
        ke = pair["keep_emi"]
        rows.append(
            {
                "rate_step": float(step),
                "new_rate": float(new_rate),
                "delta_months_if_emi_kept": ke.get("delta_months"),
                "delta_emi_if_duration_kept": kd.get("delta_emi"),
                "interest_impact_keep_emi": ke.get("interest_delta"),
                "interest_impact_keep_duration": kd.get("interest_delta"),
                # Net extra interest (positive = costs more): prefer keep_emi impact when available
                "net_extra_interest": ke.get("interest_delta")
                if ke.get("interest_delta") is not None
                else kd.get("interest_delta"),
                "negative_amortisation": bool(ke.get("negative_amortisation")),
                "keep_duration": kd,
                "keep_emi": ke,
            }
        )
    return rows


def invest_elsewhere_compare(
    prepayment_amount: Decimal,
    interest_saved_best: Decimal,
    months_horizon: int,
    alt_return_pct: Decimal,
    penalty: Decimal,
) -> dict:
    """Lump-sum prepay interest saved vs parking the same cash elsewhere."""
    if prepayment_amount <= 0 or months_horizon <= 0:
        return {
            "alt_return_pct": float(alt_return_pct),
            "horizon_months": months_horizon,
            "alt_earnings": 0.0,
            "prepay_net_benefit": float(interest_saved_best - penalty),
            "prefer_prepay": interest_saved_best - penalty > 0,
        }
    # Simple monthly compound on alternate return
    r = float(alt_return_pct) / 1200.0
    if r <= 0:
        alt_earnings = Decimal("0.00")
    else:
        fv = float(prepayment_amount) * ((1 + r) ** months_horizon)
        alt_earnings = Decimal(str(fv - float(prepayment_amount))).quantize(
            MONEY, rounding=ROUND_HALF_UP
        )
    prepay_net = interest_saved_best - penalty
    return {
        "alt_return_pct": float(alt_return_pct),
        "horizon_months": months_horizon,
        "alt_earnings": float(alt_earnings),
        "prepay_net_benefit": float(prepay_net),
        "prefer_prepay": prepay_net > alt_earnings,
        "edge": float(prepay_net - alt_earnings),
    }


async def _load_loan_context(
    session: AsyncSession, account_id: uuid.UUID
) -> tuple[Account, list]:
    result = await session.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise ValueError("Account not found")

    schedule_result = await session.execute(
        select(LoanAmortizationSchedule)
        .where(
            LoanAmortizationSchedule.account_id == account_id,
            LoanAmortizationSchedule.schedule_version == account.current_schedule_version,
            LoanAmortizationSchedule.payment_status == "scheduled",
        )
        .order_by(LoanAmortizationSchedule.emi_number)
    )
    future_entries = list(schedule_result.scalars().all())
    return account, future_entries


async def simulate_early_payment(
    session: AsyncSession,
    account_id: uuid.UUID,
    prepayment_amount: Decimal,
    prepayment_date: Optional[date] = None,
    penalty_rate: Optional[Decimal] = None,
    penalty_basis: Optional[str] = None,
    alt_return_pct: Optional[Decimal] = None,
) -> dict:
    """Simulate early payment with reduce EMI vs reduce tenure + invest-elsewhere."""
    if prepayment_date is None:
        prepayment_date = date.today()

    account, future_entries = await _load_loan_context(session, account_id)
    penalty_defaults = default_penalty_assumption(account)
    if penalty_rate is None:
        penalty_rate = Decimal(str(penalty_defaults["penalty_rate"]))
    if penalty_basis is None:
        penalty_basis = penalty_defaults["penalty_basis"]
    if alt_return_pct is None:
        alt_return_pct = DEFAULT_ALT_RETURN_PCT

    if not future_entries:
        return {
            "error": "No future EMIs found",
            "reduce_emi": None,
            "reduce_tenure": None,
            "is_interest_only": _is_interest_only(account, future_entries),
        }

    interest_only = _is_interest_only(account, future_entries)
    current_outstanding = future_entries[0].opening_balance
    new_principal = current_outstanding - prepayment_amount
    if new_principal < 0:
        new_principal = Decimal("0")

    remaining_months = len(future_entries)
    current_emi = account.emi_amount or Decimal("0")
    rate = account.interest_rate or Decimal("0")
    monthly_rate = rate / Decimal("1200") if rate > 0 else Decimal("0")

    penalty = calc_penalty(penalty_rate, penalty_basis, current_outstanding, prepayment_amount)

    if interest_only or current_emi <= 0:
        # Don't invent EMI for Pru / interest-only — show principal drop + penalty only
        old_interest = _future_interest(future_entries)
        return {
            "current_state": {
                "outstanding_balance": float(current_outstanding),
                "current_emi": float(current_emi),
                "remaining_months": remaining_months,
                "current_interest_rate": float(rate),
            },
            "prepayment": {
                "amount": float(prepayment_amount),
                "date": prepayment_date.isoformat(),
                "new_principal": float(new_principal),
            },
            "penalty": {
                "rate": float(penalty_rate),
                "basis": penalty_basis,
                "amount": float(penalty),
                "defaults": penalty_defaults,
            },
            "is_interest_only": True,
            "reduce_emi": None,
            "reduce_tenure": None,
            "note": "Interest-only / no EMI — schedule not flattened; principal drop only.",
            "remaining_scheduled_interest": float(old_interest),
        }

    # Option 1: Reduce EMI (keep same tenure) — bank default trap
    new_emi = calculate_emi(new_principal, rate, remaining_months)
    emi_reduction = current_emi - new_emi
    old_interest = _future_interest(future_entries)
    new_interest_emi = total_interest_at(new_principal, rate, remaining_months, new_emi)
    interest_saved_emi = old_interest - new_interest_emi

    # Option 2: Reduce Tenure (keep same EMI) — usually wins
    new_tenure_months = tenure_from_emi(new_principal, rate, current_emi)
    if new_tenure_months == 0:
        new_tenure_months = remaining_months
    months_saved = remaining_months - new_tenure_months
    new_payoff_date = None
    if future_entries:
        new_payoff_date = future_entries[0].due_date + timedelta(days=30 * new_tenure_months)
    new_interest_tenure = total_interest_at(new_principal, rate, new_tenure_months, current_emi)
    interest_saved_tenure = old_interest - new_interest_tenure

    best_saved = max(interest_saved_emi, interest_saved_tenure)
    invest_cmp = invest_elsewhere_compare(
        prepayment_amount,
        best_saved,
        new_tenure_months if interest_saved_tenure >= interest_saved_emi else remaining_months,
        alt_return_pct,
        penalty,
    )

    return {
        "current_state": {
            "outstanding_balance": float(current_outstanding),
            "current_emi": float(current_emi),
            "remaining_months": remaining_months,
            "current_interest_rate": float(rate),
        },
        "prepayment": {
            "amount": float(prepayment_amount),
            "date": prepayment_date.isoformat(),
            "new_principal": float(new_principal),
        },
        "penalty": {
            "rate": float(penalty_rate),
            "basis": penalty_basis,
            "amount": float(penalty),
            "defaults": penalty_defaults,
        },
        "is_interest_only": False,
        "reduce_emi": {
            "new_emi": float(new_emi),
            "emi_reduction": float(emi_reduction),
            "emi_reduction_percent": float(
                (emi_reduction / current_emi * 100) if current_emi > 0 else 0
            ),
            "tenure_months": remaining_months,
            "delta_months": 0,
            "interest_saved": float(interest_saved_emi),
            "total_savings": float(interest_saved_emi - penalty),
            "bank_default_trap": True,
        },
        "reduce_tenure": {
            "emi": float(current_emi),
            "new_tenure_months": new_tenure_months,
            "months_saved": months_saved,
            "delta_months": -months_saved,
            "new_payoff_date": new_payoff_date.isoformat() if new_payoff_date else None,
            "interest_saved": float(interest_saved_tenure),
            "total_savings": float(interest_saved_tenure - penalty),
            "usually_wins": interest_saved_tenure >= interest_saved_emi,
        },
        "recommended": "reduce_tenure"
        if interest_saved_tenure >= interest_saved_emi
        else "reduce_emi",
        "invest_elsewhere": invest_cmp,
        "hooks": {
            "scenarios": [
                "lump_prepay_vs_invest",
                "part_prepay_emi_reset",
                "part_prepay_tenure_reset",
            ]
        },
    }


async def simulate_preclosure(
    session: AsyncSession,
    account_id: uuid.UUID,
    closure_date: Optional[date] = None,
    penalty_rate: Optional[Decimal] = None,
    penalty_basis: Optional[str] = None,
) -> dict:
    """Simulate loan pre-closure and calculate payoff amount."""
    if closure_date is None:
        closure_date = date.today()

    result = await session.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise ValueError("Account not found")

    penalty_defaults = default_penalty_assumption(account)
    if penalty_rate is None:
        penalty_rate = Decimal(str(penalty_defaults["penalty_rate"]))
    if penalty_basis is None:
        penalty_basis = penalty_defaults["penalty_basis"]

    schedule_result = await session.execute(
        select(LoanAmortizationSchedule)
        .where(
            LoanAmortizationSchedule.account_id == account_id,
            LoanAmortizationSchedule.schedule_version == account.current_schedule_version,
        )
        .order_by(LoanAmortizationSchedule.emi_number)
    )
    all_entries = list(schedule_result.scalars().all())

    paid_entries = [e for e in all_entries if e.payment_status == "paid"]
    scheduled_entries = [e for e in all_entries if e.payment_status == "scheduled"]

    principal_paid = sum((e.principal_component for e in paid_entries), Decimal("0"))
    interest_paid = sum((e.interest_component for e in paid_entries), Decimal("0"))

    outstanding_principal = account.balance or Decimal("0")
    if outstanding_principal < 0:
        outstanding_principal = abs(outstanding_principal)

    if scheduled_entries:
        anchor = (
            paid_entries[-1].actual_payment_date
            if paid_entries and paid_entries[-1].actual_payment_date
            else (account.disbursed_on or closure_date)
        )
        days_since_last_payment = (closure_date - anchor).days
        if days_since_last_payment < 0:
            days_since_last_payment = 0
        daily_rate = (account.interest_rate or Decimal("0")) / Decimal("36500")
        accrued_interest = (
            outstanding_principal * daily_rate * days_since_last_payment
        ).quantize(MONEY, rounding=ROUND_HALF_UP)
    else:
        accrued_interest = Decimal("0")

    prepayment_penalty = calc_penalty(
        penalty_rate, penalty_basis, outstanding_principal, outstanding_principal
    )

    payoff_amount = outstanding_principal + accrued_interest + prepayment_penalty
    interest_saved = sum((e.interest_component for e in scheduled_entries), Decimal("0"))
    net_savings = interest_saved - prepayment_penalty

    return {
        "closure_date": closure_date.isoformat(),
        "outstanding_principal": float(outstanding_principal),
        "accrued_interest": float(accrued_interest),
        "prepayment_penalty": float(prepayment_penalty),
        "prepayment_penalty_rate": float(penalty_rate),
        "prepayment_penalty_basis": penalty_basis,
        "penalty": {
            "rate": float(penalty_rate),
            "basis": penalty_basis,
            "amount": float(prepayment_penalty),
            "defaults": penalty_defaults,
        },
        "total_payoff_amount": float(payoff_amount),
        "interest_saved": float(interest_saved),
        "net_savings": float(net_savings),
        "paid_to_date": {
            "principal": float(principal_paid),
            "interest": float(interest_paid),
            "total": float(principal_paid + interest_paid),
        },
        "remaining_emis": len(scheduled_entries),
        "is_interest_only": _is_interest_only(account, scheduled_entries),
        "hooks": {"scenarios": ["foreclosure", "penalty_myth"]},
    }


async def simulate_interest_rate_change(
    session: AsyncSession,
    account_id: uuid.UUID,
    new_interest_rate: Decimal,
    effective_from_date: Optional[date] = None,
    include_ladder: bool = True,
    ladder_steps: Optional[list] = None,
) -> dict:
    """Simulate rate change with BOTH keep-EMI and keep-duration paths + ready-ref."""
    if effective_from_date is None:
        effective_from_date = date.today()

    account, future_entries = await _load_loan_context(session, account_id)

    if not future_entries:
        return {"error": "No future EMIs found"}

    current_outstanding = future_entries[0].opening_balance
    remaining_months = len(future_entries)
    current_rate = account.interest_rate or Decimal("0")
    current_emi = account.emi_amount or Decimal("0")
    interest_only = _is_interest_only(account, future_entries)

    if interest_only or current_emi <= 0:
        # Do not invent EMI for Pru no-EMI — show rate delta on scheduled interest only
        old_interest = _future_interest(future_entries)
        return {
            "current_rate": float(current_rate),
            "new_rate": float(new_interest_rate),
            "rate_change": float(new_interest_rate - current_rate),
            "effective_from": effective_from_date.isoformat(),
            "current_emi": None,
            "outstanding_balance": float(current_outstanding),
            "remaining_months": remaining_months,
            "is_interest_only": True,
            "current_total_interest": float(old_interest),
            "keep_duration": None,
            "keep_emi": None,
            "note": "No EMI on this loan — rate change does not invent an EMI schedule.",
            "rate_ladder": [],
            # legacy fields for older clients
            "new_emi": None,
            "emi_change": None,
            "emi_change_percent": None,
            "new_total_interest": None,
            "interest_difference": None,
            "is_favorable": new_interest_rate < current_rate,
        }

    pair = rate_path_pair(
        current_outstanding,
        current_rate,
        current_emi,
        remaining_months,
        new_interest_rate,
    )
    kd = pair["keep_duration"]
    ke = pair["keep_emi"]

    steps = None
    if ladder_steps:
        steps = [Decimal(str(s)) for s in ladder_steps]
    ladder = (
        build_rate_ladder(
            current_outstanding, current_rate, current_emi, remaining_months, steps
        )
        if include_ladder
        else []
    )

    return {
        "current_rate": float(current_rate),
        "new_rate": float(new_interest_rate),
        "rate_change": float(new_interest_rate - current_rate),
        "effective_from": effective_from_date.isoformat(),
        "current_emi": float(current_emi),
        "outstanding_balance": float(current_outstanding),
        "remaining_months": remaining_months,
        "is_interest_only": False,
        "keep_duration": kd,
        "keep_emi": ke,
        "recommended": pair["recommended"] or "keep_emi",
        "tenure_cut_usually_wins": pair["tenure_cut_usually_wins"],
        "winner_interest": pair["winner_interest"],
        "is_rate_cut": pair["is_rate_cut"],
        "is_rate_hike": pair["is_rate_hike"],
        "negative_amortisation_risk": pair["negative_amortisation_risk"],
        "baseline_interest": pair["baseline_interest"],
        "rate_ladder": ladder,
        # legacy single-path fields (= keep_duration) for older clients
        "new_emi": kd["new_emi"],
        "emi_change": kd["delta_emi"],
        "emi_change_percent": float(
            (Decimal(str(kd["delta_emi"])) / current_emi * 100) if current_emi > 0 else 0
        ),
        "current_total_interest": pair["baseline_interest"],
        "new_total_interest": kd["total_interest"],
        "interest_difference": kd["interest_delta"],
        "is_favorable": kd["interest_delta"] < 0,
        "hooks": {
            "scenarios": [
                "rate_cut_keep_emi",
                "rate_cut_cut_emi",
                "rate_hike_emi_up",
                "rate_hike_tenor_elongates",
                "ready_ref_steps",
            ]
        },
    }


async def simulate_rate_ladder(
    session: AsyncSession,
    account_id: uuid.UUID,
    steps: Optional[list] = None,
) -> dict:
    """Ready-reference table only (default bottom of Simulations)."""
    account, future_entries = await _load_loan_context(session, account_id)
    if not future_entries:
        return {"error": "No future EMIs found", "rate_ladder": []}
    current_outstanding = future_entries[0].opening_balance
    remaining_months = len(future_entries)
    current_rate = account.interest_rate or Decimal("0")
    current_emi = account.emi_amount or Decimal("0")
    interest_only = _is_interest_only(account, future_entries)
    if interest_only or current_emi <= 0:
        return {
            "current_rate": float(current_rate),
            "current_emi": None,
            "outstanding_balance": float(current_outstanding),
            "remaining_months": remaining_months,
            "is_interest_only": True,
            "rate_ladder": [],
            "penalty_defaults": default_penalty_assumption(account),
        }
    step_decs = [Decimal(str(s)) for s in steps] if steps else None
    return {
        "current_rate": float(current_rate),
        "current_emi": float(current_emi),
        "outstanding_balance": float(current_outstanding),
        "remaining_months": remaining_months,
        "is_interest_only": False,
        "rate_ladder": build_rate_ladder(
            current_outstanding, current_rate, current_emi, remaining_months, step_decs
        ),
        "penalty_defaults": default_penalty_assumption(account),
    }


async def apply_preclosure(
    session: AsyncSession,
    account_id: uuid.UUID,
    closure_date: Optional[date] = None,
    create_payoff_transaction: bool = False,
    penalty_rate: Optional[Decimal] = None,
    penalty_basis: Optional[str] = None,
) -> dict:
    """Close a loan using the preclosure quote: mark remaining EMIs skipped, zero balance."""
    quote = await simulate_preclosure(
        session,
        account_id,
        closure_date,
        penalty_rate=penalty_rate,
        penalty_basis=penalty_basis,
    )
    result = await session.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one()
    if closure_date is None:
        closure_date = date.today()

    schedule_result = await session.execute(
        select(LoanAmortizationSchedule).where(
            LoanAmortizationSchedule.account_id == account_id,
            LoanAmortizationSchedule.schedule_version == account.current_schedule_version,
            LoanAmortizationSchedule.payment_status == "scheduled",
        )
    )
    for entry in schedule_result.scalars().all():
        entry.payment_status = "skipped"
        entry.notes = (entry.notes or "") + f" | Pre-closed {closure_date.isoformat()}"

    account.balance = Decimal("0.00")
    account.is_closed = True
    account.closed_at = datetime.now(timezone.utc)
    account.last_payment_date = closure_date
    await session.commit()
    return {"closed": True, "account_id": str(account_id), "quote": quote}


async def apply_interest_rate_change(
    session: AsyncSession,
    account_id: uuid.UUID,
    new_interest_rate: Decimal,
    effective_from_date: Optional[date] = None,
    strategy: str = "keep_emi",
) -> dict:
    """Apply a new interest rate and regenerate remaining schedule.

    Default strategy is keep_emi (one-tap escape from bank auto-cut-EMI trap).
    Statement-faithful: only rewrites *future scheduled* rows from current OS —
    does not touch paid / Pre-EMI / phased history.
    """
    from app.services.loan_schedule_service import regenerate_schedule, calculate_emi as sched_emi

    sim = await simulate_interest_rate_change(
        session, account_id, new_interest_rate, effective_from_date, include_ladder=False
    )
    if sim.get("error"):
        raise ValueError(sim["error"])
    if sim.get("is_interest_only"):
        raise ValueError("Cannot apply EMI rate strategy on interest-only / no-EMI loan")

    result = await session.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one()

    schedule_result = await session.execute(
        select(LoanAmortizationSchedule)
        .where(
            LoanAmortizationSchedule.account_id == account_id,
            LoanAmortizationSchedule.schedule_version == account.current_schedule_version,
            LoanAmortizationSchedule.payment_status == "scheduled",
        )
        .order_by(LoanAmortizationSchedule.emi_number)
        .limit(1)
    )
    next_entry = schedule_result.scalar_one_or_none()
    if not next_entry:
        raise ValueError("No future EMIs to regenerate")

    remaining_months = int(sim["remaining_months"])
    outstanding = Decimal(str(sim["outstanding_balance"]))
    old_rate = account.interest_rate
    account.interest_rate = new_interest_rate

    # Prefer keep_emi (tenure adjusts) — bank trap escape
    if strategy in ("keep_emi", "reduce_tenure") and account.emi_amount:
        monthly_rate = (
            new_interest_rate / Decimal("1200") if new_interest_rate > 0 else Decimal("0")
        )
        if monthly_rate > 0:
            r = float(monthly_rate)
            emi = float(account.emi_amount)
            p = float(outstanding)
            if emi > p * r:
                tenure = int(math.ceil(math.log(emi / (emi - p * r)) / math.log(1 + r)))
            else:
                raise ValueError(
                    "Negative amortisation: current EMI cannot cover interest at new rate"
                )
        else:
            tenure = int((outstanding / account.emi_amount).to_integral_value())
        new_params = {
            "new_principal_balance": outstanding,
            "new_interest_rate": new_interest_rate,
            "new_emi_amount": account.emi_amount,
            "new_tenure_months": max(1, tenure),
        }
    else:
        new_emi = sched_emi(outstanding, new_interest_rate, remaining_months)
        account.emi_amount = new_emi
        new_params = {
            "new_principal_balance": outstanding,
            "new_interest_rate": new_interest_rate,
            "new_tenure_months": remaining_months,
            "new_emi_amount": new_emi,
        }

    entries = await regenerate_schedule(session, account_id, next_entry.emi_number, new_params)
    await session.refresh(account)
    return {
        "applied": True,
        "old_rate": float(old_rate or 0),
        "new_rate": float(new_interest_rate),
        "strategy": strategy,
        "simulation": sim,
        "new_schedule_version": account.current_schedule_version,
        "entries_created": len(entries),
    }
