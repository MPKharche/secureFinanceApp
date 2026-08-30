from datetime import date
from decimal import Decimal
import uuid

from app.schemas.loan_schedule import (
    LoanScheduleEntryRead,
    PrepaymentCreate,
    PrepaymentRead,
    PrepaymentSimulation,
)


def test_loan_schedule_entry_read_serialization():
    """Test LoanScheduleEntryRead schema serialization."""
    data = {
        "id": uuid.uuid4(),
        "account_id": uuid.uuid4(),
        "workspace_id": uuid.uuid4(),
        "schedule_version": 1,
        "emi_number": 1,
        "due_date": date(2026, 9, 5),
        "principal_component": 8333.33,
        "interest_component": 1666.67,
        "emi_amount": 10000.00,
        "opening_balance": 1000000.00,
        "closing_balance": 991666.67,
        "payment_status": "scheduled",
        "actual_payment_date": None,
        "actual_amount_paid": None,
        "linked_transaction_id": None,
        "notes": None,
    }
    entry = LoanScheduleEntryRead(**data)
    assert entry.emi_number == 1
    assert entry.payment_status == "scheduled"
    assert entry.principal_component == 8333.33


def test_prepayment_create_validation():
    """Test PrepaymentCreate validates required fields."""
    data = {
        "prepayment_amount": Decimal("50000.00"),
        "prepayment_date": date(2026, 12, 15),
        "recalculation_method": "reduce_emi",
    }
    prepayment = PrepaymentCreate(**data)
    assert prepayment.recalculation_method == "reduce_emi"
    assert prepayment.prepayment_amount == Decimal("50000.00")


def test_prepayment_simulation_structure():
    """Test PrepaymentSimulation contains both options."""
    data = {
        "reduce_emi_option": {
            "new_emi_amount": Decimal("9500.00"),
            "emi_reduction": Decimal("500.00"),
            "tenure_months": 100,
            "total_interest_saved": Decimal("15000.00"),
            "sample_schedule": [],
        },
        "reduce_tenure_option": {
            "new_tenure_months": 95,
            "months_saved": 5,
            "new_payoff_date": date(2034, 8, 5),
            "emi_amount": Decimal("10000.00"),
            "total_interest_saved": Decimal("18000.00"),
            "sample_schedule": [],
        },
    }
    simulation = PrepaymentSimulation(**data)
    assert simulation.reduce_emi_option.new_emi_amount == Decimal("9500.00")
    assert simulation.reduce_tenure_option.months_saved == 5
