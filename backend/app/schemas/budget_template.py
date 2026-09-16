import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class CategoryBudgetData(BaseModel):
    category_id: uuid.UUID
    amount: Decimal


class BudgetTemplateCreate(BaseModel):
    name: str
    description: str | None = None
    categories: list[CategoryBudgetData]


class BudgetTemplateRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    template_data: dict
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BudgetTemplateApply(BaseModel):
    template_id: uuid.UUID
    target_months: list[str]  # ["2025-10-01", "2025-11-01", ...]
    is_recurring: bool = False


class BudgetTemplateApplyResponse(BaseModel):
    created_count: int
