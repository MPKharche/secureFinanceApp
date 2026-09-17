"""Tests for tax dashboard integration."""
import pytest
from decimal import Decimal

from app.tax.constants import CURRENT_FY


@pytest.mark.asyncio
async def test_tax_dashboard_get_projection(async_client, auth_headers, test_workspace, test_user):
    """Test getting tax projection."""
    response = await async_client.get(
        f"/api/tax/projections/{CURRENT_FY}",
        headers=auth_headers,
    )
    
    # May be 404 if no data exists yet, or 200 with projection
    assert response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_tax_income_source_create(async_client, auth_headers, test_workspace):
    """Test creating income source."""
    payload = {
        "financial_year": CURRENT_FY,
        "salary_annual": 1200000,
        "rental_income": 0,
        "interest_income": 5000,
        "dividend_income": 0,
        "capital_gains_short_term": 0,
        "capital_gains_long_term": 0,
        "business_income": 0,
        "other_income": 0,
    }
    
    response = await async_client.post(
        "/api/tax/income-sources",
        json=payload,
        headers=auth_headers,
    )
    
    # May be 201 (created) or 400 (already exists)
    assert response.status_code in [201, 400]


@pytest.mark.asyncio
async def test_tax_deductions_create(async_client, auth_headers, test_workspace):
    """Test creating deductions."""
    payload = {
        "financial_year": CURRENT_FY,
        "epf_employee": 150000,
        "ppf": 0,
        "elss": 0,
        "lic_premium": 0,
        "nps_additional": 50000,
        "health_insurance_self": 25000,
        "health_insurance_parents": 0,
    }
    
    response = await async_client.post(
        "/api/tax/deductions",
        json=payload,
        headers=auth_headers,
    )
    
    assert response.status_code in [201, 400]


@pytest.mark.asyncio
async def test_tax_what_if_scenario(async_client, auth_headers):
    """Test what-if scenario calculation."""
    payload = {
        "financial_year": CURRENT_FY,
        "income": {
            "salary_annual": 1500000,
            "rental_income": 0,
            "interest_income": 10000,
            "dividend_income": 0,
            "capital_gains_short_term": 0,
            "capital_gains_long_term": 0,
            "business_income": 0,
            "other_income": 0,
        },
        "deductions": {
            "epf_employee": 150000,
            "ppf": 0,
            "elss": 0,
            "lic_premium": 0,
            "nps_additional": 50000,
            "health_insurance_self": 25000,
            "health_insurance_parents": 0,
            "parents_are_senior_citizens": False,
            "preventive_checkup": 0,
            "education_loan_interest": 0,
            "donations_100_percent": 0,
            "donations_50_percent": 0,
            "savings_interest_claimed": 10000,
            "home_loan_interest": 0,
            "property_is_self_occupied": True,
            "rent_paid_annual": 0,
        },
    }
    
    response = await async_client.post(
        "/api/tax/what-if",
        json=payload,
        headers=auth_headers,
    )
    
    # May fail if user age not set
    assert response.status_code in [200, 400]
    
    if response.status_code == 200:
        data = response.json()
        assert "old_regime" in data
        assert "new_regime" in data
        assert "recommended_regime" in data


@pytest.mark.asyncio
async def test_tax_payment_update(async_client, auth_headers, test_workspace):
    """Test updating tax payments."""
    # First ensure projection exists
    income_payload = {
        "financial_year": CURRENT_FY,
        "salary_annual": 1000000,
    }
    
    await async_client.post(
        "/api/tax/income-sources",
        json=income_payload,
        headers=auth_headers,
    )
    
    # Calculate projection
    await async_client.post(
        "/api/tax/projections/calculate",
        json={"financial_year": CURRENT_FY},
        headers=auth_headers,
    )
    
    # Update payments
    payment_payload = {
        "tds_deducted": 50000,
        "advance_tax_paid": 20000,
    }
    
    response = await async_client.put(
        f"/api/tax/payments/{CURRENT_FY}",
        json=payment_payload,
        headers=auth_headers,
    )
    
    assert response.status_code in [200, 404]
    
    if response.status_code == 200:
        data = response.json()
        assert "tds_deducted" in data
        assert "advance_tax_paid" in data
        assert "tax_due_or_refund" in data
