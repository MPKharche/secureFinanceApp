import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ScenarioAdjustment(BaseModel):
    category_id: uuid.UUID
    adjustment_type: str  # "percent" or "fixed"
    value: Decimal  # +10 for +10%, or +500 for +$500


class BudgetScenarioCreate(BaseModel):
    name: str
    description: str | None = None
    base_month: date
    adjustments: list[ScenarioAdjustment]


class BudgetScenarioRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    base_month: date
    adjustments: dict
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScenarioCategoryPreview(BaseModel):
    category_id: str
    month: str
    base_amount: Decimal
    adjusted_amount: Decimal


class BudgetScenarioPreview(BaseModel):
    months: list[ScenarioCategoryPreview]
