"""Capital gains tax calculation engine (pure functions)."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

from .constants import (
    ADVANCE_TAX_SCHEDULE,
    ADVANCE_TAX_THRESHOLD,
    CESS_RATE,
    DEBT_HOLDING_PERIOD_MONTHS,
    DEBT_LTCG_RATE,
    EQUITY_ASSET_TYPES,
    EQUITY_HOLDING_PERIOD_MONTHS,
    EQUITY_LTCG_EXEMPTION,
    EQUITY_LTCG_RATE,
    EQUITY_STCG_RATE,
)


@dataclass
class CapitalGain:
    asset_name: str
    asset_type: str
    buy_date: date
    sell_date: date
    buy_price: Decimal
    sell_price: Decimal
    quantity: Decimal
    gain_loss: Decimal
    holding_period_days: int
    classification: Literal["STCG", "LTCG"]
    asset_class: Literal["equity", "debt"]
    tax_rate: Decimal
    tax_amount: Decimal


@dataclass
class CapitalGainsSummary:
    financial_year: str
    equity_stcg_total: Decimal
    equity_stcg_tax: Decimal
    equity_ltcg_total: Decimal
    equity_ltcg_exempt: Decimal
    equity_ltcg_taxable: Decimal
    equity_ltcg_tax: Decimal
    debt_stcg_total: Decimal
    debt_ltcg_total: Decimal
    debt_ltcg_tax: Decimal
    total_gains: Decimal
    total_tax: Decimal
    cess: Decimal
    total_tax_with_cess: Decimal
    advance_tax_required: bool
    advance_tax_schedule: list[dict]


class CapitalGainsTaxEngine:
    def __init__(self, user_income_tax_slab_rate: Decimal = Decimal("0.30")):
        self.slab_rate = user_income_tax_slab_rate

    def calculate_holding_period_days(self, buy_date: date, sell_date: date) -> int:
        return (sell_date - buy_date).days

    def classify_asset_class(self, asset_type: str) -> Literal["equity", "debt"]:
        return "equity" if asset_type in EQUITY_ASSET_TYPES else "debt"

    def classify_gain(
        self, asset_class: Literal["equity", "debt"], holding_days: int
    ) -> Literal["STCG", "LTCG"]:
        threshold = EQUITY_HOLDING_PERIOD_MONTHS if asset_class == "equity" else DEBT_HOLDING_PERIOD_MONTHS
        return "LTCG" if holding_days > (threshold * 30) else "STCG"

    def calculate_single_gain(
        self,
        asset_name: str,
        asset_type: str,
        buy_date: date,
        sell_date: date,
        buy_price: Decimal,
        sell_price: Decimal,
        quantity: Decimal,
    ) -> CapitalGain:
        gain_loss = sell_price - buy_price
        holding_days = self.calculate_holding_period_days(buy_date, sell_date)
        asset_class = self.classify_asset_class(asset_type)
        classification = self.classify_gain(asset_class, holding_days)

        if asset_class == "equity":
            tax_rate = EQUITY_STCG_RATE if classification == "STCG" else EQUITY_LTCG_RATE
        else:
            tax_rate = self.slab_rate if classification == "STCG" else DEBT_LTCG_RATE

        tax_amount = gain_loss * tax_rate if gain_loss > 0 else Decimal("0")

        return CapitalGain(
            asset_name=asset_name,
            asset_type=asset_type,
            buy_date=buy_date,
            sell_date=sell_date,
            buy_price=buy_price,
            sell_price=sell_price,
            quantity=quantity,
            gain_loss=gain_loss,
            holding_period_days=holding_days,
            classification=classification,
            asset_class=asset_class,
            tax_rate=tax_rate,
            tax_amount=tax_amount,
        )

    def aggregate_gains(
        self, gains: list[CapitalGain], financial_year: str
    ) -> CapitalGainsSummary:
        equity_stcg_total = sum(g.gain_loss for g in gains if g.asset_class == "equity" and g.classification == "STCG")
        equity_ltcg_total = sum(g.gain_loss for g in gains if g.asset_class == "equity" and g.classification == "LTCG")
        debt_stcg_total = sum(g.gain_loss for g in gains if g.asset_class == "debt" and g.classification == "STCG")
        debt_ltcg_total = sum(g.gain_loss for g in gains if g.asset_class == "debt" and g.classification == "LTCG")

        equity_stcg_tax = equity_stcg_total * EQUITY_STCG_RATE if equity_stcg_total > 0 else Decimal("0")
        equity_ltcg_exempt = min(equity_ltcg_total, EQUITY_LTCG_EXEMPTION)
        equity_ltcg_taxable = max(equity_ltcg_total - EQUITY_LTCG_EXEMPTION, Decimal("0"))
        equity_ltcg_tax = equity_ltcg_taxable * EQUITY_LTCG_RATE
        debt_stcg_tax = debt_stcg_total * self.slab_rate if debt_stcg_total > 0 else Decimal("0")
        debt_ltcg_tax = debt_ltcg_total * DEBT_LTCG_RATE if debt_ltcg_total > 0 else Decimal("0")

        total_tax = equity_stcg_tax + equity_ltcg_tax + debt_stcg_tax + debt_ltcg_tax
        cess = total_tax * CESS_RATE
        total_tax_with_cess = total_tax + cess

        advance_tax_required = total_tax_with_cess > ADVANCE_TAX_THRESHOLD
        advance_tax_schedule = [
            {
                "due_date": s["due_date"],
                "cumulative_percent": float(s["cumulative_percent"]),
                "amount": total_tax_with_cess * s["cumulative_percent"],
            }
            for s in ADVANCE_TAX_SCHEDULE
        ] if advance_tax_required else []

        return CapitalGainsSummary(
            financial_year=financial_year,
            equity_stcg_total=equity_stcg_total,
            equity_stcg_tax=equity_stcg_tax,
            equity_ltcg_total=equity_ltcg_total,
            equity_ltcg_exempt=equity_ltcg_exempt,
            equity_ltcg_taxable=equity_ltcg_taxable,
            equity_ltcg_tax=equity_ltcg_tax,
            debt_stcg_total=debt_stcg_total,
            debt_ltcg_total=debt_ltcg_total,
            debt_ltcg_tax=debt_ltcg_tax,
            total_gains=equity_stcg_total + equity_ltcg_total + debt_stcg_total + debt_ltcg_total,
            total_tax=total_tax,
            cess=cess,
            total_tax_with_cess=total_tax_with_cess,
            advance_tax_required=advance_tax_required,
            advance_tax_schedule=advance_tax_schedule,
        )

    def suggest_tax_harvesting(self, gains: list[CapitalGain], current_holdings: list[dict]) -> list[dict]:
        net_gains = sum(g.gain_loss for g in gains)
        if net_gains <= 0:
            return []
        return [
            {
                "asset_name": h["asset_name"],
                "asset_type": h["asset_type"],
                "unrealized_loss": h["unrealized_loss"],
                "action": "Sell to book loss and offset gains",
                "tax_savings": min(abs(h["unrealized_loss"]), net_gains) * EQUITY_STCG_RATE,
            }
            for h in current_holdings if h["unrealized_loss"] < 0
        ]
