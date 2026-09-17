"""Tests for XIRR calculator."""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta

from app.services.xirr_calculator import XIRRCalculator


def test_simple_xirr():
    """Test simple XIRR calculation."""
    # Invest 10000 on day 0, get 11000 on day 365
    cash_flows = [Decimal(-10000), Decimal(11000)]
    dates = [datetime(2024, 1, 1), datetime(2025, 1, 1)]
    
    xirr = XIRRCalculator.calculate_xirr(cash_flows, dates)
    
    assert xirr is not None
    assert abs(xirr - Decimal("0.10")) < Decimal("0.01")  # ~10% return


def test_sip_xirr():
    """Test XIRR with monthly SIP pattern."""
    cash_flows = []
    dates = []
    
    # Monthly SIP of 10000 for 6 months
    start_date = datetime(2024, 1, 1)
    for i in range(6):
        cash_flows.append(Decimal(-10000))
        dates.append(start_date + timedelta(days=30*i))
    
    # Current value after 6 months: 65000
    cash_flows.append(Decimal(65000))
    dates.append(start_date + timedelta(days=180))
    
    xirr = XIRRCalculator.calculate_xirr(cash_flows, dates)
    
    assert xirr is not None
    assert xirr > Decimal("0")  # Positive return


def test_all_positive_cash_flows():
    """Test that all positive cash flows return None."""
    cash_flows = [Decimal(1000), Decimal(2000), Decimal(3000)]
    dates = [datetime(2024, 1, 1), datetime(2024, 2, 1), datetime(2024, 3, 1)]
    
    xirr = XIRRCalculator.calculate_xirr(cash_flows, dates)
    
    assert xirr is None


def test_all_negative_cash_flows():
    """Test that all negative cash flows return None."""
    cash_flows = [Decimal(-1000), Decimal(-2000), Decimal(-3000)]
    dates = [datetime(2024, 1, 1), datetime(2024, 2, 1), datetime(2024, 3, 1)]
    
    xirr = XIRRCalculator.calculate_xirr(cash_flows, dates)
    
    assert xirr is None


def test_simple_return():
    """Test simple return calculation."""
    invested = Decimal(10000)
    current_value = Decimal(12000)
    
    ret = XIRRCalculator.calculate_simple_return(invested, current_value)
    
    assert ret == Decimal("0.2")  # 20% return
