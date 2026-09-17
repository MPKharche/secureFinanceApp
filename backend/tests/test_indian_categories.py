"""Test Indian category presets."""
import pytest

from app.services.category_service import DEFAULT_CATEGORIES_I18N


def test_indian_categories_exist():
    """Verify all Indian categories are defined."""
    indian_categories = [
        "house_help",
        "tuition",
        "school_fees",
        "medical",
        "insurance",
        "gold",
        "religious",
        "festivals",
        "pet_care",
        "tobacco_alcohol",
    ]
    
    for cat_key in indian_categories:
        assert cat_key in DEFAULT_CATEGORIES_I18N, f"Missing category: {cat_key}"


def test_indian_categories_have_translations():
    """Verify Indian categories have Hindi, Tamil, Bengali translations."""
    indian_categories = [
        "house_help",
        "tuition",
        "school_fees",
        "medical",
        "insurance",
        "gold",
        "religious",
        "festivals",
        "pet_care",
        "tobacco_alcohol",
    ]
    
    required_langs = ["en", "hi", "ta", "bn"]
    
    for cat_key in indian_categories:
        cat_data = DEFAULT_CATEGORIES_I18N[cat_key]
        for lang in required_langs:
            assert lang in cat_data, f"Missing {lang} translation for {cat_key}"
            assert cat_data[lang], f"Empty {lang} translation for {cat_key}"


def test_indian_categories_have_icons():
    """Verify Indian categories have appropriate icons."""
    expected_icons = {
        "house_help": "users",
        "tuition": "graduation-cap",
        "school_fees": "school",
        "medical": "stethoscope",
        "insurance": "shield",
        "gold": "gem",
        "religious": "church",
        "festivals": "party-popper",
        "pet_care": "dog",
        "tobacco_alcohol": "cigarette",
    }
    
    for cat_key, expected_icon in expected_icons.items():
        cat_data = DEFAULT_CATEGORIES_I18N[cat_key]
        assert "icon" in cat_data, f"Missing icon for {cat_key}"
        assert cat_data["icon"] == expected_icon, f"Wrong icon for {cat_key}: {cat_data['icon']}"


def test_indian_categories_have_colors():
    """Verify Indian categories have color codes."""
    indian_categories = [
        "house_help",
        "tuition",
        "school_fees",
        "medical",
        "insurance",
        "gold",
        "religious",
        "festivals",
        "pet_care",
        "tobacco_alcohol",
    ]
    
    for cat_key in indian_categories:
        cat_data = DEFAULT_CATEGORIES_I18N[cat_key]
        assert "color" in cat_data, f"Missing color for {cat_key}"
        assert cat_data["color"].startswith("#"), f"Invalid color format for {cat_key}"
        assert len(cat_data["color"]) == 7, f"Invalid color length for {cat_key}"


def test_all_categories_have_indian_translations():
    """Verify all existing categories now have Hindi, Tamil, Bengali translations."""
    required_langs = ["hi", "ta", "bn"]
    
    for cat_key, cat_data in DEFAULT_CATEGORIES_I18N.items():
        for lang in required_langs:
            assert lang in cat_data, f"Missing {lang} translation for {cat_key}"
