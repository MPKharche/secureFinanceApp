"""Tests for XIRR calculator."""
from datetime import date
from decimal import Decimal
from app.services.xirr_calculator import XIRRCalculator

def test_simple_xirr():
    cash_flows = [Decimal('-10000'), Decimal('11000')]
    dates = [date(2023, 1, 1), date(2024, 1, 1)]
    xirr = XIRRCalculator.calculate_xirr(cash_flows, dates)
    assert xirr is not None
    assert abs(xirr - Decimal('0.1')) < Decimal('0.01')

def test_all_positive_cash_flows():
    cash_flows = [Decimal('1000'), Decimal('2000'), Decimal('3000')]
    dates = [date(2023, 1, 1), date(2023, 6, 1), date(2024, 1, 1)]
    xirr = XIRRCalculator.calculate_xirr(cash_flows, dates)
    assert xirr is None

def test_minimum_holding_period():
    cash_flows = [Decimal('-10000'), Decimal('10500')]
    dates = [date(2024, 1, 1), date(2024, 3, 1)]
    xirr = XIRRCalculator.calculate_xirr(cash_flows, dates)
    assert xirr is None
