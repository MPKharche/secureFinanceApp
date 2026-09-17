"""XIRR (Extended Internal Rate of Return) calculator for mutual fund returns.

Uses Newton-Raphson method for accurate IRR calculation with multiple cash flows.
"""
from datetime import date
from decimal import Decimal
from typing import List, Optional


class XIRRCalculator:
    """Calculate XIRR for mutual fund investments using Newton-Raphson method."""
    
    MAX_ITERATIONS = 100
    PRECISION = Decimal("0.0001")
    MIN_DAYS = 180
    
    @staticmethod
    def calculate_xirr(cash_flows: List[Decimal], dates: List[date], guess: Decimal = Decimal("0.1")) -> Optional[Decimal]:
        if len(cash_flows) != len(dates) or len(cash_flows) < 2:
            return None
        if (dates[-1] - dates[0]).days < XIRRCalculator.MIN_DAYS:
            return None
        all_positive = all(cf >= 0 for cf in cash_flows)
        all_negative = all(cf <= 0 for cf in cash_flows)
        if all_positive or all_negative:
            return None
        
        rate = guess
        for _ in range(XIRRCalculator.MAX_ITERATIONS):
            npv = XIRRCalculator._calculate_npv(cash_flows, dates, rate)
            dnpv = XIRRCalculator._calculate_dnpv(cash_flows, dates, rate)
            if abs(dnpv) < Decimal("1e-10"):
                return None
            new_rate = rate - (npv / dnpv)
            if abs(new_rate - rate) < XIRRCalculator.PRECISION:
                return new_rate
            rate = new_rate
        return None
    
    @staticmethod
    def _calculate_npv(cash_flows: List[Decimal], dates: List[date], rate: Decimal) -> Decimal:
        base_date = dates[0]
        npv = Decimal("0")
        for cf, dt in zip(cash_flows, dates):
            days = (dt - base_date).days
            years = Decimal(str(days)) / Decimal("365")
            npv += cf / ((Decimal("1") + rate) ** years)
        return npv
    
    @staticmethod
    def _calculate_dnpv(cash_flows: List[Decimal], dates: List[date], rate: Decimal) -> Decimal:
        base_date = dates[0]
        dnpv = Decimal("0")
        for cf, dt in zip(cash_flows, dates):
            days = (dt - base_date).days
            years = Decimal(str(days)) / Decimal("365")
            dnpv -= years * cf / ((Decimal("1") + rate) ** (years + Decimal("1")))
        return dnpv
    
    @staticmethod
    def calculate_simple_return(invested: Decimal, current_value: Decimal, start_date: date, end_date: date) -> Optional[Decimal]:
        if invested <= 0 or current_value <= 0:
            return None
        days = (end_date - start_date).days
        if days < XIRRCalculator.MIN_DAYS:
            return None
        years = Decimal(str(days)) / Decimal("365")
        total_return = (current_value / invested) - Decimal("1")
        annualized = (Decimal("1") + total_return) ** (Decimal("1") / years) - Decimal("1")
        return annualized
