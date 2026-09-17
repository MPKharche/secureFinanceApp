"""Test tax constants."""
import pytest

from app.tax.constants import (
    CURRENT_FY,
    NEW_REGIME_SLABS,
    OLD_REGIME_SLABS,
    SENIOR_CITIZEN_SLABS,
    SUPER_SENIOR_CITIZEN_SLABS,
    SECTION_80C_LIMIT,
    SECTION_80CCD_1B_LIMIT,
    SECTION_80D_SELF_LIMIT,
    SECTION_24B_LIMIT,
    METRO_CITIES,
    SENIOR_CITIZEN_AGE,
    SUPER_SENIOR_CITIZEN_AGE
)


def test_current_fy_format():
    """Test financial year format is correct."""
    assert CURRENT_FY == "2026-27"
    assert len(CURRENT_FY) == 7
    assert "-" in CURRENT_FY


def test_new_regime_slabs_structure():
    """Test new regime slabs are correctly structured."""
    assert len(NEW_REGIME_SLABS) == 7
    
    # First slab: 0-4L at 0%
    assert NEW_REGIME_SLABS[0] == (0, 400000, 0)
    
    # Last slab: >24L at 30%
    assert NEW_REGIME_SLABS[-1][2] == 0.30
    assert NEW_REGIME_SLABS[-1][1] == float('inf')
    
    # Check progressive rates
    for i in range(len(NEW_REGIME_SLABS) - 1):
        assert NEW_REGIME_SLABS[i][1] == NEW_REGIME_SLABS[i + 1][0], \
            f"Slab gap at index {i}"


def test_old_regime_slabs_structure():
    """Test old regime slabs are correctly structured."""
    assert len(OLD_REGIME_SLABS) == 4
    assert OLD_REGIME_SLABS[0] == (0, 250000, 0)
    assert OLD_REGIME_SLABS[-1][2] == 0.30
    assert OLD_REGIME_SLABS[-1][1] == float('inf')


def test_senior_citizen_slabs():
    """Test senior citizen slabs have higher exemption."""
    # Senior citizen exemption is ₹3L vs ₹2.5L for regular
    assert SENIOR_CITIZEN_SLABS[0][1] == 300000
    assert OLD_REGIME_SLABS[0][1] == 250000
    assert SENIOR_CITIZEN_SLABS[0][1] > OLD_REGIME_SLABS[0][1]


def test_super_senior_citizen_slabs():
    """Test super senior citizen slabs have highest exemption."""
    # Super senior exemption is ₹5L
    assert SUPER_SENIOR_CITIZEN_SLABS[0][1] == 500000
    assert SUPER_SENIOR_CITIZEN_SLABS[0][1] > SENIOR_CITIZEN_SLABS[0][1]


def test_deduction_limits():
    """Test all deduction limits are set correctly."""
    assert SECTION_80C_LIMIT == 150000
    assert SECTION_80CCD_1B_LIMIT == 50000
    assert SECTION_80D_SELF_LIMIT == 25000
    assert SECTION_24B_LIMIT == 200000


def test_metro_cities_list():
    """Test metro cities list contains expected cities."""
    assert "Mumbai" in METRO_CITIES
    assert "Delhi" in METRO_CITIES
    assert "Bangalore" in METRO_CITIES
    assert "Chennai" in METRO_CITIES
    assert len(METRO_CITIES) == 8


def test_age_thresholds():
    """Test age thresholds for citizen categories."""
    assert SENIOR_CITIZEN_AGE == 60
    assert SUPER_SENIOR_CITIZEN_AGE == 80
    assert SUPER_SENIOR_CITIZEN_AGE > SENIOR_CITIZEN_AGE
