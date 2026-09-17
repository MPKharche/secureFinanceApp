"""India-specific goal templates with presets and calculation helpers."""

from decimal import Decimal
from typing import Optional, Literal

GoalTemplateType = Literal[
    "emergency_fund",
    "child_education",
    "marriage",
    "house_down_payment",
    "car_purchase",
    "vacation",
    "parents_medical",
    "retirement",
    "gold_purchase",
]

GOAL_TEMPLATES = {
    "emergency_fund": {
        "name_en": "Emergency Fund",
        "name_hi": "आपातकालीन कोष",
        "description_en": "6 months of essential expenses",
        "description_hi": "6 महीने के आवश्यक खर्च",
        "icon": "shield",
        "color": "#10B981",  # Emerald
        "priority": 1,
        "suggested_months": 6,
        "calculation_type": "monthly_expenses",
    },
    "child_education": {
        "name_en": "Child Education",
        "name_hi": "बच्चे की शिक्षा",
        "description_en": "School fees, college, coaching expenses",
        "description_hi": "स्कूल फीस, कॉलेज, कोचिंग खर्च",
        "icon": "graduation-cap",
        "color": "#3B82F6",  # Blue
        "priority": 2,
        "suggested_amount_inr": Decimal("500000"),  # ₹5L baseline
        "calculation_type": "fixed_amount",
    },
    "marriage": {
        "name_en": "Marriage Fund",
        "name_hi": "विवाह कोष",
        "description_en": "Wedding expenses for self or children",
        "description_hi": "स्वयं या बच्चों की शादी के खर्च",
        "icon": "heart",
        "color": "#EC4899",  # Pink
        "priority": 3,
        "suggested_amount_inr": Decimal("1000000"),  # ₹10L baseline
        "calculation_type": "fixed_amount",
    },
    "house_down_payment": {
        "name_en": "House Down Payment",
        "name_hi": "मकान का डाउन पेमेंट",
        "description_en": "20-30% down payment for home loan",
        "description_hi": "होम लोन के लिए 20-30% डाउन पेमेंट",
        "icon": "home",
        "color": "#F59E0B",  # Amber
        "priority": 4,
        "suggested_amount_inr": Decimal("1500000"),  # ₹15L baseline
        "calculation_type": "fixed_amount",
    },
    "car_purchase": {
        "name_en": "Car Purchase",
        "name_hi": "कार खरीद",
        "description_en": "Down payment or full car purchase",
        "description_hi": "डाउन पेमेंट या पूरी कार खरीद",
        "icon": "car",
        "color": "#EF4444",  # Red
        "priority": 5,
        "suggested_amount_inr": Decimal("300000"),  # ₹3L baseline
        "calculation_type": "fixed_amount",
    },
    "vacation": {
        "name_en": "Vacation & Travel",
        "name_hi": "छुट्टी और यात्रा",
        "description_en": "Family vacation or travel fund",
        "description_hi": "पारिवारिक छुट्टी या यात्रा कोष",
        "icon": "plane",
        "color": "#06B6D4",  # Cyan
        "priority": 6,
        "suggested_amount_inr": Decimal("100000"),  # ₹1L baseline
        "calculation_type": "fixed_amount",
    },
    "parents_medical": {
        "name_en": "Parents Medical Fund",
        "name_hi": "माता-पिता का चिकित्सा कोष",
        "description_en": "Healthcare expenses for parents",
        "description_hi": "माता-पिता के स्वास्थ्य खर्च",
        "icon": "heart-pulse",
        "color": "#8B5CF6",  # Purple
        "priority": 2,
        "suggested_amount_inr": Decimal("200000"),  # ₹2L baseline
        "calculation_type": "fixed_amount",
    },
    "retirement": {
        "name_en": "Retirement Corpus",
        "name_hi": "सेवानिवृत्ति कोष",
        "description_en": "Long-term retirement savings",
        "description_hi": "दीर्घकालिक सेवानिवृत्ति बचत",
        "icon": "piggy-bank",
        "color": "#F97316",  # Orange
        "priority": 1,
        "suggested_amount_inr": Decimal("10000000"),  # ₹1Cr baseline
        "calculation_type": "retirement",
    },
    "gold_purchase": {
        "name_en": "Gold Purchase",
        "name_hi": "सोना खरीद",
        "description_en": "Festival, wedding, or investment gold",
        "description_hi": "त्योहार, शादी या निवेश के लिए सोना",
        "icon": "coins",
        "color": "#F59E0B",  # Gold/Amber
        "priority": 7,
        "suggested_amount_inr": Decimal("50000"),  # ₹50K baseline
        "calculation_type": "fixed_amount",
    },
}


def calculate_recommended_amount(
    template_type: GoalTemplateType,
    monthly_expenses: Optional[Decimal] = None,
    age: Optional[int] = None,
    retirement_age: int = 60,
    currency: str = "INR",
) -> Decimal:
    """Calculate recommended goal amount based on template type and user context.
    
    Args:
        template_type: Type of goal template
        monthly_expenses: User's monthly expenses (for emergency fund calculation)
        age: User's current age (for retirement calculation)
        retirement_age: Target retirement age
        currency: Currency code (used for conversion if needed)
    
    Returns:
        Recommended target amount in the specified currency
    """
    template = GOAL_TEMPLATES[template_type]
    calc_type = template.get("calculation_type", "fixed_amount")
    
    if calc_type == "monthly_expenses" and monthly_expenses:
        # Emergency fund: 6 months of expenses
        multiplier = template.get("suggested_months", 6)
        return monthly_expenses * multiplier
    
    elif calc_type == "retirement" and age and age < retirement_age:
        # Retirement: rough estimate based on age and baseline
        years_to_retirement = retirement_age - age
        # Reduce baseline if closer to retirement (already accumulated elsewhere)
        baseline = template.get("suggested_amount_inr", Decimal("10000000"))
        # Simple heuristic: scale down if < 15 years left
        if years_to_retirement < 15:
            baseline = baseline * Decimal(str(years_to_retirement / 15))
        return baseline
    
    # Default: fixed amount from template
    return template.get("suggested_amount_inr", Decimal("100000"))


def get_template_info(template_type: GoalTemplateType, language: str = "en") -> dict:
    """Get template display information."""
    template = GOAL_TEMPLATES[template_type]
    name_key = f"name_{language}" if language in ("en", "hi") else "name_en"
    desc_key = f"description_{language}" if language in ("en", "hi") else "description_en"
    
    return {
        "type": template_type,
        "name": template.get(name_key, template["name_en"]),
        "description": template.get(desc_key, template["description_en"]),
        "icon": template["icon"],
        "color": template["color"],
        "priority": template["priority"],
    }


def list_templates(language: str = "en") -> list[dict]:
    """List all available goal templates, sorted by priority."""
    templates = [
        {**get_template_info(ttype, language), "type": ttype}
        for ttype in GOAL_TEMPLATES.keys()
    ]
    return sorted(templates, key=lambda t: t["priority"])
