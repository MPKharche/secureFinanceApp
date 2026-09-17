"""Test goal templates feature."""

import pytest
from decimal import Decimal
from app.data.goal_templates import (
    GOAL_TEMPLATES,
    calculate_recommended_amount,
    get_template_info,
    list_templates,
)


def test_all_templates_have_required_fields():
    """Ensure all templates have required fields."""
    required_fields = ["name_en", "description_en", "icon", "color", "priority"]
    for template_type, template in GOAL_TEMPLATES.items():
        for field in required_fields:
            assert field in template, f"Template {template_type} missing {field}"


def test_list_templates_returns_sorted_by_priority():
    """Templates should be sorted by priority."""
    templates = list_templates("en")
    assert len(templates) == len(GOAL_TEMPLATES)
    
    # Check that priorities are in ascending order
    priorities = [t["priority"] for t in templates]
    assert priorities == sorted(priorities)


def test_emergency_fund_calculation():
    """Emergency fund should be 6x monthly expenses."""
    monthly_expenses = Decimal("50000")
    result = calculate_recommended_amount(
        "emergency_fund",
        monthly_expenses=monthly_expenses,
        currency="INR"
    )
    assert result == monthly_expenses * 6


def test_retirement_calculation_scales_with_age():
    """Retirement amount should scale based on years to retirement."""
    # Someone 45 years old (15 years to retirement)
    result_45 = calculate_recommended_amount(
        "retirement",
        age=45,
        retirement_age=60,
        currency="INR"
    )
    
    # Someone 30 years old (30 years to retirement)
    result_30 = calculate_recommended_amount(
        "retirement",
        age=30,
        retirement_age=60,
        currency="INR"
    )
    
    # Younger person should have higher target (more time to accumulate)
    assert result_30 == Decimal("10000000")  # Full baseline
    assert result_45 == Decimal("10000000")  # Full baseline at 15 years


def test_fixed_amount_templates():
    """Fixed amount templates should return baseline."""
    result = calculate_recommended_amount("child_education", currency="INR")
    assert result == Decimal("500000")
    
    result = calculate_recommended_amount("marriage", currency="INR")
    assert result == Decimal("1000000")


def test_get_template_info_english():
    """Get template info in English."""
    info = get_template_info("emergency_fund", "en")
    assert info["name"] == "Emergency Fund"
    assert info["type"] == "emergency_fund"
    assert info["icon"] == "shield"
    assert info["color"] == "#10B981"
    assert info["priority"] == 1


def test_get_template_info_hindi():
    """Get template info in Hindi."""
    info = get_template_info("emergency_fund", "hi")
    assert info["name"] == "आपातकालीन कोष"
    assert "description" in info


def test_priority_ranking():
    """Verify priority ranking matches specification."""
    priorities = {
        "emergency_fund": 1,
        "retirement": 1,
        "child_education": 2,
        "parents_medical": 2,
        "marriage": 3,
        "house_down_payment": 4,
        "car_purchase": 5,
        "vacation": 6,
        "gold_purchase": 7,
    }
    
    for template_type, expected_priority in priorities.items():
        assert GOAL_TEMPLATES[template_type]["priority"] == expected_priority


def test_all_templates_have_indian_context():
    """All templates should have Hindi translations."""
    for template_type, template in GOAL_TEMPLATES.items():
        assert "name_hi" in template, f"{template_type} missing Hindi name"
        assert "description_hi" in template, f"{template_type} missing Hindi description"
