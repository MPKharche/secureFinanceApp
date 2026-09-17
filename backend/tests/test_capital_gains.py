"""Tests for capital gains calculator API."""
import pytest
from decimal import Decimal
from datetime import date

from app.tax.capital_gains_engine import CapitalGainsTaxEngine


def test_equity_stcg_calculation():
    """Test equity short-term capital gains (< 12 months)."""
    engine = CapitalGainsTaxEngine()
    
    gain = engine.calculate_single_gain(
        asset_name="Reliance",
        asset_type="equity",
        buy_date=date(2026, 1, 1),
        sell_date=date(2026, 6, 1),  # 5 months
        buy_price=Decimal("1000"),
        sell_price=Decimal("1200"),
        quantity=Decimal("10"),
    )
    
    assert gain.classification == "STCG"
    assert gain.asset_class == "equity"
    assert gain.gain_loss == Decimal("200")  # 1200 - 1000
    assert gain.tax_rate == Decimal("0.15")  # 15% for equity STCG
    assert gain.tax_amount == Decimal("30")  # 200 * 0.15


def test_equity_ltcg_calculation():
    """Test equity long-term capital gains (> 12 months)."""
    engine = CapitalGainsTaxEngine()
    
    gain = engine.calculate_single_gain(
        asset_name="TCS",
        asset_type="equity",
        buy_date=date(2025, 1, 1),
        sell_date=date(2026, 6, 1),  # 17 months
        buy_price=Decimal("3000"),
        sell_price=Decimal("4000"),
        quantity=Decimal("5"),
    )
    
    assert gain.classification == "LTCG"
    assert gain.asset_class == "equity"
    assert gain.gain_loss == Decimal("1000")
    assert gain.tax_rate == Decimal("0.10")  # 10% for equity LTCG
    assert gain.tax_amount == Decimal("100")  # 1000 * 0.10


def test_debt_stcg_calculation():
    """Test debt short-term capital gains (< 36 months)."""
    engine = CapitalGainsTaxEngine(user_income_tax_slab_rate=Decimal("0.30"))
    
    gain = engine.calculate_single_gain(
        asset_name="Debt Fund",
        asset_type="debt",
        buy_date=date(2025, 1, 1),
        sell_date=date(2026, 6, 1),  # 17 months
        buy_price=Decimal("10000"),
        sell_price=Decimal("11000"),
        quantity=Decimal("1"),
    )
    
    assert gain.classification == "STCG"
    assert gain.asset_class == "debt"
    assert gain.gain_loss == Decimal("1000")
    assert gain.tax_rate == Decimal("0.30")  # User's slab rate
    assert gain.tax_amount == Decimal("300")


def test_debt_ltcg_calculation():
    """Test debt long-term capital gains (> 36 months)."""
    engine = CapitalGainsTaxEngine()
    
    gain = engine.calculate_single_gain(
        asset_name="Debt Bond",
        asset_type="debt",
        buy_date=date(2023, 1, 1),
        sell_date=date(2026, 6, 1),  # 41 months
        buy_price=Decimal("50000"),
        sell_price=Decimal("60000"),
        quantity=Decimal("1"),
    )
    
    assert gain.classification == "LTCG"
    assert gain.asset_class == "debt"
    assert gain.gain_loss == Decimal("10000")
    assert gain.tax_rate == Decimal("0.20")  # 20% with indexation
    assert gain.tax_amount == Decimal("2000")


def test_aggregate_gains_with_exemption():
    """Test aggregation with LTCG exemption."""
    engine = CapitalGainsTaxEngine()
    
    gains = [
        engine.calculate_single_gain(
            asset_name="Stock A",
            asset_type="equity",
            buy_date=date(2024, 1, 1),
            sell_date=date(2026, 6, 1),
            buy_price=Decimal("1000"),
            sell_price=Decimal("2500"),  # Gain: 1500
            quantity=Decimal("1"),
        ),
    ]
    
    summary = engine.aggregate_gains(gains, "2026-27")
    
    assert summary.equity_ltcg_total == Decimal("1500")
    assert summary.equity_ltcg_exempt == Decimal("1000")  # Min(1500, 100000)
    assert summary.equity_ltcg_taxable == Decimal("500")  # 1500 - 1000
    assert summary.equity_ltcg_tax == Decimal("50")  # 500 * 0.10


def test_advance_tax_required():
    """Test advance tax schedule for high tax liability."""
    engine = CapitalGainsTaxEngine()
    
    # Create a large gain that triggers advance tax
    gains = [
        engine.calculate_single_gain(
            asset_name="Big Stock",
            asset_type="equity",
            buy_date=date(2024, 1, 1),
            sell_date=date(2026, 6, 1),
            buy_price=Decimal("10000"),
            sell_price=Decimal("150000"),  # Large gain
            quantity=Decimal("1"),
        ),
    ]
    
    summary = engine.aggregate_gains(gains, "2026-27")
    
    # Tax should exceed 10,000 threshold
    assert summary.total_tax_with_cess > Decimal("10000")
    assert summary.advance_tax_required is True
    assert len(summary.advance_tax_schedule) == 4  # 4 installments


def test_loss_no_tax():
    """Test that losses don't generate tax."""
    engine = CapitalGainsTaxEngine()
    
    gain = engine.calculate_single_gain(
        asset_name="Loss Stock",
        asset_type="equity",
        buy_date=date(2025, 1, 1),
        sell_date=date(2026, 6, 1),
        buy_price=Decimal("2000"),
        sell_price=Decimal("1500"),  # Loss
        quantity=Decimal("1"),
    )
    
    assert gain.gain_loss == Decimal("-500")
    assert gain.tax_amount == Decimal("0")


@pytest.mark.asyncio
async def test_capital_gains_api_calculate(async_client, auth_headers):
    """Test capital gains calculation API endpoint."""
    payload = {
        "financial_year": "2026-27",
        "sales": [
            {
                "asset_name": "Reliance",
                "asset_type": "equity",
                "buy_date": "2025-01-01",
                "sell_date": "2026-06-01",
                "buy_price": "1000",
                "sell_price": "1500",
                "quantity": "10",
            }
        ],
        "user_income_tax_slab_rate": 0.30,
    }
    
    response = await async_client.post(
        "/api/capital-gains/calculate",
        json=payload,
        headers=auth_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "gains" in data
    assert "summary" in data
    assert len(data["gains"]) == 1
    assert data["gains"][0]["asset_name"] == "Reliance"
    assert data["summary"]["financial_year"] == "2026-27"


@pytest.mark.asyncio
async def test_capital_gains_api_validation(async_client, auth_headers):
    """Test API validation for invalid input."""
    payload = {
        "financial_year": "2026-27",
        "sales": [
            {
                "asset_name": "Test",
                "asset_type": "equity",
                "buy_date": "2025-01-01",
                "sell_date": "2026-06-01",
                "buy_price": "-100",  # Invalid negative price
                "sell_price": "1500",
                "quantity": "10",
            }
        ],
    }
    
    response = await async_client.post(
        "/api/capital-gains/calculate",
        json=payload,
        headers=auth_headers,
    )
    
    assert response.status_code == 422  # Validation error
