import uuid
from datetime import date as _Date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

WeekendAdjustment = Literal["none", "previous_friday", "next_monday"]


class RecurringTransactionCreate(BaseModel):
    description: str
    amount: Decimal
    currency: str = "USD"
    type: str  # debit, credit
    frequency: str  # weekly, biweekly, monthly, quarterly, semiannual, yearly
    weekend_adjustment: WeekendAdjustment = "none"
    day_of_month: Optional[int] = None
    start_date: _Date
    end_date: Optional[_Date] = None
    account_id: uuid.UUID
    category_id: Optional[uuid.UUID] = None
    skip_first: bool = False  # Set true when first occurrence already created as a transaction
    auto_generate: bool = True  # Materialize occurrences; when false, wait for the real charge


class RecurringTransactionUpdate(BaseModel):
    description: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    type: Optional[str] = None
    frequency: Optional[str] = None  # weekly, biweekly, monthly, quarterly, semiannual, yearly
    weekend_adjustment: Optional[WeekendAdjustment] = None
    day_of_month: Optional[int] = None
    start_date: Optional[_Date] = None
    end_date: Optional[_Date] = None
    account_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None
    auto_generate: Optional[bool] = None


class RecurringPostOccurrenceRequest(BaseModel):
    """Guided post for reminder-only (auto_generate=false) bills."""

    payment_date: Optional[_Date] = None
    transfer_to_account_id: Optional[uuid.UUID] = None
    link_loan_schedule: bool = False
    loan_account_id: Optional[uuid.UUID] = None


class RecurringPostOccurrenceResponse(BaseModel):
    already_posted: bool
    transaction_ids: list[str]
    cash_leg_id: Optional[str] = None
    credit_leg_id: Optional[str] = None
    schedule_entry_id: Optional[str] = None
    recurring_id: str
    next_occurrence: _Date
    post_kind: Optional[str] = None


class RecurringTransactionRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    account_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    description: str
    amount: Decimal
    currency: str
    type: str
    frequency: str
    weekend_adjustment: WeekendAdjustment = "none"
    day_of_month: Optional[int] = None
    start_date: _Date
    end_date: Optional[_Date] = None
    is_active: bool
    auto_generate: bool = True
    next_occurrence: _Date
    amount_primary: Optional[float] = None
    fx_rate_used: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)
