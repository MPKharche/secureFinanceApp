# Budget Spreadsheet: 12-Month Multi-Section View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform single-month budget list into comprehensive 12-month spreadsheet with Excel-like editing, income/expense/investment sections, rollover budgets, templates, scenarios, and goal linkage.

**Architecture:** Backend adds category types, bulk query endpoints, template/scenario storage; frontend replaces simple table with react-data-grid component featuring frozen columns, inline editing, copy/paste, trend visualization, and mobile responsive view.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic (backend); React, TypeScript, react-data-grid, recharts, Tailwind CSS (frontend); PostgreSQL (database)

**Spec:** `docs/superpowers/specs/2026-09-16-budget-spreadsheet-design.md`

## Global Constraints

- Python 3.11+ (backend)
- Node 20+ (frontend)
- PostgreSQL 14+
- React 19.2.0, TypeScript 5.9.3
- Use existing shadcn/ui components for dialogs, buttons, inputs
- Follow existing API patterns (workspace context, async/await)
- All amounts use Decimal type with 2 decimal places
- Dates use ISO 8601 format (YYYY-MM-DD)
- Match existing code style (Black formatting for Python, Prettier for TypeScript)

---

## Task 1: Database Schema Migration

**Files:**
- Create: `backend/alembic/versions/018_budget_spreadsheet_schema.py`
- Modify: `backend/app/models/category.py`
- Modify: `backend/app/models/goal.py`
- Create: `backend/app/models/budget_template.py`
- Create: `backend/app/models/budget_scenario.py`
- Create: `backend/app/models/notification.py`

**Interfaces:**
- Consumes: Existing `categories`, `goals`, `budgets` tables
- Produces: 
  - `categories.category_type` VARCHAR(20) DEFAULT 'expense'
  - `categories.enable_rollover` BOOLEAN DEFAULT false
  - `goals.linked_category_ids` UUID[]
  - `budget_templates` table
  - `budget_scenarios` table
  - `notifications` table

- [ ] **Step 1: Create Alembic migration file**

```bash
cd backend
alembic revision -m "budget_spreadsheet_schema"
```

- [ ] **Step 2: Write upgrade migration**

Edit `backend/alembic/versions/018_budget_spreadsheet_schema.py`:

```python
"""budget_spreadsheet_schema

Revision ID: 018
Revises: 017
Create Date: 2026-09-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '018'
down_revision = '017'
branch_labels = None
depends_on = None


def upgrade():
    # Add columns to categories
    op.add_column('categories', sa.Column('category_type', sa.String(20), server_default='expense', nullable=False))
    op.add_column('categories', sa.Column('enable_rollover', sa.Boolean, server_default='false', nullable=False))
    
    # Add column to goals
    op.add_column('goals', sa.Column('linked_category_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), server_default='{}', nullable=False))
    
    # Create budget_templates table
    op.create_table(
        'budget_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('template_data', postgresql.JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('workspace_id', 'name', name='uq_template_name_per_workspace')
    )
    op.create_index('idx_budget_templates_workspace', 'budget_templates', ['workspace_id'])
    
    # Create budget_scenarios table
    op.create_table(
        'budget_scenarios',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('base_month', sa.Date, nullable=False),
        sa.Column('adjustments', postgresql.JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('workspace_id', 'name', name='uq_scenario_name_per_workspace')
    )
    op.create_index('idx_budget_scenarios_workspace', 'budget_scenarios', ['workspace_id'])
    
    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('metadata', postgresql.JSONB, server_default='{}', nullable=False),
        sa.Column('read', sa.Boolean, server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    )
    op.create_index('idx_notifications_user_unread', 'notifications', ['user_id', 'read', sa.text('created_at DESC')])


def downgrade():
    op.drop_index('idx_notifications_user_unread', 'notifications')
    op.drop_table('notifications')
    op.drop_index('idx_budget_scenarios_workspace', 'budget_scenarios')
    op.drop_table('budget_scenarios')
    op.drop_index('idx_budget_templates_workspace', 'budget_templates')
    op.drop_table('budget_templates')
    op.drop_column('goals', 'linked_category_ids')
    op.drop_column('categories', 'enable_rollover')
    op.drop_column('categories', 'category_type')
```

- [ ] **Step 3: Update Category model**

Edit `backend/app/models/category.py`:

```python
# Add after existing imports
from sqlalchemy import String, Boolean

# Add to Category class after existing columns
category_type: Mapped[str] = mapped_column(String(20), server_default='expense', nullable=False)
enable_rollover: Mapped[bool] = mapped_column(Boolean, server_default='false', nullable=False)
```

- [ ] **Step 4: Update Goal model**

Edit `backend/app/models/goal.py`:

```python
# Add after existing imports
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PGUUID

# Add to Goal class after existing columns
linked_category_ids: Mapped[list[uuid.UUID]] = mapped_column(
    ARRAY(PGUUID(as_uuid=True)), server_default='{}', nullable=False
)
```

- [ ] **Step 5: Create BudgetTemplate model**

Create `backend/app/models/budget_template.py`:

```python
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workspace import Workspace


class BudgetTemplate(Base):
    __tablename__ = "budget_templates"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_template_name_per_workspace"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_data: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship()
    workspace: Mapped["Workspace"] = relationship()
```

- [ ] **Step 6: Create BudgetScenario model**

Create `backend/app/models/budget_scenario.py`:

```python
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workspace import Workspace


class BudgetScenario(Base):
    __tablename__ = "budget_scenarios"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_scenario_name_per_workspace"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_month: Mapped[date] = mapped_column(Date)
    adjustments: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship()
    workspace: Mapped["Workspace"] = relationship()
```

- [ ] **Step 7: Create Notification model**

Create `backend/app/models/notification.py`:

```python
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workspace import Workspace


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    metadata: Mapped[dict] = mapped_column(JSONB, server_default='{}')
    read: Mapped[bool] = mapped_column(Boolean, server_default='false')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship()
    workspace: Mapped["Workspace"] = relationship()
```

- [ ] **Step 8: Run migration**

```bash
cd backend
alembic upgrade head
```

Expected output: `Running upgrade 017 -> 018, budget_spreadsheet_schema`

- [ ] **Step 9: Verify migration in database**

```bash
psql $DATABASE_URL -c "\d categories" | grep category_type
psql $DATABASE_URL -c "\d goals" | grep linked_category_ids
psql $DATABASE_URL -c "\dt" | grep budget_templates
```

Expected: Columns and tables exist

- [ ] **Step 10: Commit**

```bash
git add backend/alembic/versions/018_budget_spreadsheet_schema.py \
  backend/app/models/category.py \
  backend/app/models/goal.py \
  backend/app/models/budget_template.py \
  backend/app/models/budget_scenario.py \
  backend/app/models/notification.py
git commit -m "feat(budgets): add database schema for spreadsheet view, templates, scenarios"
```

---

## Task 2: Backend Schemas (Pydantic)

**Files:**
- Modify: `backend/app/schemas/budget.py`
- Create: `backend/app/schemas/budget_template.py`
- Create: `backend/app/schemas/budget_scenario.py`
- Create: `backend/app/schemas/notification.py`

**Interfaces:**
- Consumes: SQLAlchemy models from Task 1
- Produces:
  - `BudgetMultiMonthResponse` (list of budgets)
  - `BudgetActualsResponse` (dict mapping category_id to month->amount)
  - `BudgetTemplateCreate`, `BudgetTemplateRead`
  - `BudgetScenarioCreate`, `BudgetScenarioRead`, `BudgetScenarioPreview`
  - `NotificationRead`

- [ ] **Step 1: Add multi-month schemas to budget.py**

Edit `backend/app/schemas/budget.py`, add at end:

```python
class BudgetActualsResponse(BaseModel):
    category_actuals: dict[str, dict[str, Decimal]]  # category_id -> { month -> amount }


class CategoryAmountInput(BaseModel):
    category_id: uuid.UUID
    amount: Decimal


class BudgetUpdateWithScope(BaseModel):
    amount: Decimal
    apply_to_future: bool = False
```

- [ ] **Step 2: Create budget_template schemas**

Create `backend/app/schemas/budget_template.py`:

```python
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
```

- [ ] **Step 3: Create budget_scenario schemas**

Create `backend/app/schemas/budget_scenario.py`:

```python
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
```

- [ ] **Step 4: Create notification schemas**

Create `backend/app/schemas/notification.py`:

```python
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    type: str
    title: str
    message: str
    metadata: dict
    read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

- [ ] **Step 5: Run type checker**

```bash
cd backend
mypy app/schemas/
```

Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/
git commit -m "feat(budgets): add Pydantic schemas for templates, scenarios, notifications"
```

---

## Task 3: Multi-Month Budget Service

**Files:**
- Modify: `backend/app/services/budget_service.py`
- Test: `backend/tests/test_budget_service.py`

**Interfaces:**
- Consumes: `Budget`, `Category`, `Transaction` models; existing `get_budgets()` function
- Produces:
  - `get_budgets_multi_month(session, workspace_id, start_month, end_month) -> list[Budget]`
  - `get_actuals_multi_month(session, workspace_id, user_id, start_month, end_month) -> dict[str, dict[str, Decimal]]`

- [ ] **Step 1: Write failing test for multi-month budgets**

Edit `backend/tests/test_budget_service.py`, add:

```python
import pytest
from datetime import date
from decimal import Decimal

@pytest.mark.asyncio
async def test_get_budgets_multi_month(session, test_workspace, test_user, test_category):
    """Test fetching budgets across multiple months with recurring resolution."""
    from app.services import budget_service
    from app.schemas.budget import BudgetCreate
    
    # Create recurring budget for Sep 2025
    sep_budget = await budget_service.create_budget(
        session, test_workspace.id, test_user.id,
        BudgetCreate(
            category_id=test_category.id,
            amount=Decimal("1000.00"),
            month=date(2025, 9, 1),
            is_recurring=True
        )
    )
    
    # Create month-specific override for Nov 2025
    nov_budget = await budget_service.create_budget(
        session, test_workspace.id, test_user.id,
        BudgetCreate(
            category_id=test_category.id,
            amount=Decimal("1200.00"),
            month=date(2025, 11, 1),
            is_recurring=False
        )
    )
    
    # Query Sep-Dec range
    budgets = await budget_service.get_budgets_multi_month(
        session, test_workspace.id,
        date(2025, 9, 1), date(2025, 12, 1)
    )
    
    # Group by month
    by_month = {b.month: b for b in budgets if b.category_id == test_category.id}
    
    # Sep: recurring budget
    assert date(2025, 9, 1) in by_month
    assert by_month[date(2025, 9, 1)].amount == Decimal("1000.00")
    
    # Oct: recurring budget carries forward
    assert date(2025, 10, 1) in by_month
    assert by_month[date(2025, 10, 1)].amount == Decimal("1000.00")
    
    # Nov: month-specific override
    assert date(2025, 11, 1) in by_month
    assert by_month[date(2025, 11, 1)].amount == Decimal("1200.00")
    
    # Dec: recurring budget (override doesn't carry forward)
    assert date(2025, 12, 1) in by_month
    assert by_month[date(2025, 12, 1)].amount == Decimal("1000.00")


@pytest.mark.asyncio
async def test_get_actuals_multi_month(session, test_workspace, test_user, test_category, test_account):
    """Test fetching actual spending across multiple months."""
    from app.services import budget_service
    from app.models.transaction import Transaction
    from decimal import Decimal
    
    # Create transactions in Sep and Oct
    sep_tx = Transaction(
        workspace_id=test_workspace.id,
        account_id=test_account.id,
        type="debit",
        amount=Decimal("950.00"),
        currency="USD",
        date=date(2025, 9, 15),
        effective_date=date(2025, 9, 15),
        category_id=test_category.id,
        status="posted",
        description="Sep expense"
    )
    oct_tx = Transaction(
        workspace_id=test_workspace.id,
        account_id=test_account.id,
        type="debit",
        amount=Decimal("1020.00"),
        currency="USD",
        date=date(2025, 10, 10),
        effective_date=date(2025, 10, 10),
        category_id=test_category.id,
        status="posted",
        description="Oct expense"
    )
    session.add_all([sep_tx, oct_tx])
    await session.commit()
    
    # Query actuals
    actuals = await budget_service.get_actuals_multi_month(
        session, test_workspace.id, test_user.id,
        date(2025, 9, 1), date(2025, 11, 1)
    )
    
    cat_id = str(test_category.id)
    assert cat_id in actuals
    assert "2025-09" in actuals[cat_id]
    assert actuals[cat_id]["2025-09"] == Decimal("950.00")
    assert "2025-10" in actuals[cat_id]
    assert actuals[cat_id]["2025-10"] == Decimal("1020.00")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/test_budget_service.py::test_get_budgets_multi_month -v
pytest tests/test_budget_service.py::test_get_actuals_multi_month -v
```

Expected: FAIL with "function not defined"

- [ ] **Step 3: Implement get_budgets_multi_month**

Edit `backend/app/services/budget_service.py`, add after existing `get_budgets()`:

```python
async def get_budgets_multi_month(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    start_month: date,
    end_month: date,
) -> list[Budget]:
    """
    Fetch all effective budgets for each month in range.
    Uses existing resolution logic: month-specific override > most recent recurring.
    """
    all_budgets = []
    current = start_month.replace(day=1)
    
    while current <= end_month:
        month_budgets = await get_budgets(session, workspace_id, current)
        all_budgets.extend(month_budgets)
        
        # Move to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    
    # Deduplicate by (category_id, month) — keep most specific entry
    unique_budgets = {}
    for b in all_budgets:
        key = (str(b.category_id), b.month.strftime('%Y-%m'))
        if key not in unique_budgets or not b.is_recurring:
            unique_budgets[key] = b
    
    return list(unique_budgets.values())
```

- [ ] **Step 4: Implement get_actuals_multi_month**

Edit `backend/app/services/budget_service.py`, add after `get_budgets_multi_month()`:

```python
async def get_actuals_multi_month(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    start_month: date,
    end_month: date,
) -> dict[str, dict[str, Decimal]]:
    """
    Returns: { "category_uuid": { "2025-09": 950.00, "2025-10": 1020.00, ... }, ... }
    """
    user = await session.get(User, user_id)
    primary_currency = user.primary_currency if user else get_settings().default_currency
    accounting_mode = await get_credit_card_accounting_mode(session)
    report_date = reporting_date_col(accounting_mode)
    
    # Query all transactions in range, grouped by category and month
    result = await session.execute(
        select(
            Transaction.category_id,
            func.date_trunc('month', report_date).label('month'),
            func.sum(_primary_amount_expr()).label('total'),
        )
        .where(
            Transaction.workspace_id == workspace_id,
            report_date >= start_month,
            report_date < end_month,
            Transaction.category_id.isnot(None),
            Transaction.status == 'posted',
            counts_as_user_pnl(),
        )
        .group_by(Transaction.category_id, func.date_trunc('month', report_date))
    )
    
    actuals = {}
    for row in result.all():
        cat_id = str(row.category_id)
        month_key = row.month.strftime('%Y-%m')
        if cat_id not in actuals:
            actuals[cat_id] = {}
        actuals[cat_id][month_key] = abs(row.total or Decimal("0"))
    
    # Apply split adjustments per month
    current = start_month.replace(day=1)
    while current < end_month:
        # Next month boundary
        if current.month == 12:
            next_month = current.replace(year=current.year + 1, month=1)
        else:
            next_month = current.replace(month=current.month + 1)
        
        # Owner share offset
        own_offset = await owner_split_offset_by_category(
            session, user_id, current, next_month,
            use_effective_date=accounting_mode == "accrual",
            primary_currency=primary_currency,
            workspace_id=workspace_id,
        )
        for cat_uuid, total in own_offset.items():
            if cat_uuid is None:
                continue
            cat_id = str(cat_uuid)
            month_key = current.strftime('%Y-%m')
            if cat_id in actuals and month_key in actuals[cat_id]:
                actuals[cat_id][month_key] -= Decimal(str(total))
                if actuals[cat_id][month_key] <= 0:
                    del actuals[cat_id][month_key]
        
        # Group share
        shared_by_cat = await viewer_shared_spending_by_category(
            session, user_id, current, next_month,
            use_effective_date=accounting_mode == "accrual",
            primary_currency=primary_currency,
        )
        for cat_uuid, total in shared_by_cat.items():
            if cat_uuid is None:
                continue
            cat_id = str(cat_uuid)
            month_key = current.strftime('%Y-%m')
            if cat_id not in actuals:
                actuals[cat_id] = {}
            actuals[cat_id][month_key] = actuals[cat_id].get(month_key, Decimal("0")) + Decimal(str(total))
        
        current = next_month
    
    return actuals
```

- [ ] **Step 5: Add import for viewer_shared_spending_by_category**

At top of `backend/app/services/budget_service.py`:

```python
from app.services._query_filters import (
    counts_as_user_pnl,
    owner_split_offset_by_category,
    reporting_date_col,
    viewer_shared_spending_by_category,  # Add this line
)
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd backend
pytest tests/test_budget_service.py::test_get_budgets_multi_month -v
pytest tests/test_budget_service.py::test_get_actuals_multi_month -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/budget_service.py backend/tests/test_budget_service.py
git commit -m "feat(budgets): add multi-month budget and actuals query service"
```

---

## Task 4: Budget Template Service

**Files:**
- Create: `backend/app/services/budget_template_service.py`
- Test: `backend/tests/test_budget_template_service.py`

**Interfaces:**
- Consumes: `BudgetTemplate` model, `BudgetTemplateCreate`, `BudgetTemplateApply` schemas
- Produces:
  - `create_template(session, workspace_id, user_id, data) -> BudgetTemplate`
  - `list_templates(session, workspace_id) -> list[BudgetTemplate]`
  - `delete_template(session, template_id, workspace_id) -> bool`
  - `apply_template(session, workspace_id, user_id, template_id, target_months, is_recurring) -> int`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_budget_template_service.py`:

```python
import pytest
from datetime import date
from decimal import Decimal


@pytest.mark.asyncio
async def test_create_and_list_templates(session, test_workspace, test_user, test_category):
    """Test creating and listing budget templates."""
    from app.services import budget_template_service
    from app.schemas.budget_template import BudgetTemplateCreate, CategoryBudgetData
    
    # Create template
    template = await budget_template_service.create_template(
        session, test_workspace.id, test_user.id,
        BudgetTemplateCreate(
            name="Q4 2025 Default",
            description="Standard budget for Q4",
            categories=[
                CategoryBudgetData(category_id=test_category.id, amount=Decimal("1000.00"))
            ]
        )
    )
    
    assert template.id is not None
    assert template.name == "Q4 2025 Default"
    assert len(template.template_data["categories"]) == 1
    
    # List templates
    templates = await budget_template_service.list_templates(session, test_workspace.id)
    assert len(templates) >= 1
    assert any(t.id == template.id for t in templates)


@pytest.mark.asyncio
async def test_apply_template(session, test_workspace, test_user, test_category):
    """Test applying template to multiple months."""
    from app.services import budget_template_service
    from app.services import budget_service
    from app.schemas.budget_template import BudgetTemplateCreate, CategoryBudgetData
    
    # Create template
    template = await budget_template_service.create_template(
        session, test_workspace.id, test_user.id,
        BudgetTemplateCreate(
            name="Test Template",
            categories=[
                CategoryBudgetData(category_id=test_category.id, amount=Decimal("500.00"))
            ]
        )
    )
    
    # Apply to 3 months
    created_count = await budget_template_service.apply_template(
        session, test_workspace.id, test_user.id,
        template.id,
        [date(2025, 10, 1), date(2025, 11, 1), date(2025, 12, 1)],
        is_recurring=False
    )
    
    assert created_count == 3
    
    # Verify budgets created
    oct_budgets = await budget_service.get_budgets(session, test_workspace.id, date(2025, 10, 1))
    assert any(b.category_id == test_category.id and b.amount == Decimal("500.00") for b in oct_budgets)


@pytest.mark.asyncio
async def test_delete_template(session, test_workspace, test_user, test_category):
    """Test deleting a template."""
    from app.services import budget_template_service
    from app.schemas.budget_template import BudgetTemplateCreate, CategoryBudgetData
    
    # Create template
    template = await budget_template_service.create_template(
        session, test_workspace.id, test_user.id,
        BudgetTemplateCreate(
            name="To Delete",
            categories=[
                CategoryBudgetData(category_id=test_category.id, amount=Decimal("100.00"))
            ]
        )
    )
    
    # Delete
    deleted = await budget_template_service.delete_template(session, template.id, test_workspace.id)
    assert deleted is True
    
    # Verify gone
    templates = await budget_template_service.list_templates(session, test_workspace.id)
    assert not any(t.id == template.id for t in templates)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/test_budget_template_service.py -v
```

Expected: FAIL with "module not found"

- [ ] **Step 3: Implement budget_template_service**

Create `backend/app/services/budget_template_service.py`:

```python
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import Budget
from app.models.budget_template import BudgetTemplate
from app.schemas.budget_template import BudgetTemplateCreate


async def create_template(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    data: BudgetTemplateCreate,
) -> BudgetTemplate:
    """Create a new budget template."""
    template = BudgetTemplate(
        user_id=user_id,
        workspace_id=workspace_id,
        name=data.name,
        description=data.description,
        template_data={
            "categories": [
                {"category_id": str(c.category_id), "amount": float(c.amount)}
                for c in data.categories
            ]
        }
    )
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return template


async def list_templates(
    session: AsyncSession,
    workspace_id: uuid.UUID,
) -> list[BudgetTemplate]:
    """List all templates for a workspace."""
    result = await session.execute(
        select(BudgetTemplate)
        .where(BudgetTemplate.workspace_id == workspace_id)
        .order_by(BudgetTemplate.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_template(
    session: AsyncSession,
    template_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> bool:
    """Delete a template."""
    result = await session.execute(
        select(BudgetTemplate).where(
            BudgetTemplate.id == template_id,
            BudgetTemplate.workspace_id == workspace_id
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        return False
    
    await session.delete(template)
    await session.commit()
    return True


async def apply_template(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    template_id: uuid.UUID,
    target_months: list[date],
    is_recurring: bool,
) -> int:
    """Apply template to multiple months, creating budgets."""
    # Fetch template
    result = await session.execute(
        select(BudgetTemplate).where(
            BudgetTemplate.id == template_id,
            BudgetTemplate.workspace_id == workspace_id
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise ValueError("Template not found")
    
    created_count = 0
    for month in target_months:
        month_start = month.replace(day=1)
        
        for cat_data in template.template_data["categories"]:
            # Check if budget already exists
            existing = await session.execute(
                select(Budget).where(
                    Budget.workspace_id == workspace_id,
                    Budget.category_id == uuid.UUID(cat_data["category_id"]),
                    Budget.month == month_start,
                    Budget.is_recurring == is_recurring,
                )
            )
            if existing.scalar_one_or_none():
                continue  # Skip existing
            
            # Create budget
            budget = Budget(
                user_id=user_id,
                workspace_id=workspace_id,
                category_id=uuid.UUID(cat_data["category_id"]),
                amount=Decimal(str(cat_data["amount"])),
                month=month_start,
                is_recurring=is_recurring,
            )
            session.add(budget)
            created_count += 1
    
    await session.commit()
    return created_count
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
pytest tests/test_budget_template_service.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/budget_template_service.py backend/tests/test_budget_template_service.py
git commit -m "feat(budgets): add budget template service with create/list/apply"
```

---

## Task 5: Budget Scenario Service

**Files:**
- Create: `backend/app/services/budget_scenario_service.py`
- Test: `backend/tests/test_budget_scenario_service.py`

**Interfaces:**
- Consumes: `BudgetScenario` model, `BudgetScenarioCreate` schema, `get_budgets_multi_month()` from Task 3
- Produces:
  - `create_scenario(session, workspace_id, user_id, data) -> BudgetScenario`
  - `list_scenarios(session, workspace_id) -> list[BudgetScenario]`
  - `preview_scenario(session, scenario_id, workspace_id, months) -> dict`
  - `delete_scenario(session, scenario_id, workspace_id) -> bool`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_budget_scenario_service.py`:

```python
import pytest
from datetime import date
from decimal import Decimal


@pytest.mark.asyncio
async def test_create_and_preview_scenario(session, test_workspace, test_user, test_category):
    """Test creating scenario and previewing adjusted budgets."""
    from app.services import budget_scenario_service, budget_service
    from app.schemas.budget_scenario import BudgetScenarioCreate, ScenarioAdjustment
    from app.schemas.budget import BudgetCreate
    
    # Create base budget
    await budget_service.create_budget(
        session, test_workspace.id, test_user.id,
        BudgetCreate(
            category_id=test_category.id,
            amount=Decimal("1000.00"),
            month=date(2025, 9, 1),
            is_recurring=True
        )
    )
    
    # Create scenario with +10% adjustment
    scenario = await budget_scenario_service.create_scenario(
        session, test_workspace.id, test_user.id,
        BudgetScenarioCreate(
            name="Salary +10%",
            description="What if I get a raise",
            base_month=date(2025, 9, 1),
            adjustments=[
                ScenarioAdjustment(
                    category_id=test_category.id,
                    adjustment_type="percent",
                    value=Decimal("10")
                )
            ]
        )
    )
    
    assert scenario.id is not None
    assert scenario.name == "Salary +10%"
    
    # Preview 3 months
    preview = await budget_scenario_service.preview_scenario(
        session, scenario.id, test_workspace.id, 3
    )
    
    # Find Sep entry
    sep_entry = next(m for m in preview["months"] if m["month"] == "2025-09" and m["category_id"] == str(test_category.id))
    assert sep_entry["base_amount"] == Decimal("1000.00")
    assert sep_entry["adjusted_amount"] == Decimal("1100.00")


@pytest.mark.asyncio
async def test_scenario_fixed_adjustment(session, test_workspace, test_user, test_category):
    """Test scenario with fixed amount adjustment."""
    from app.services import budget_scenario_service, budget_service
    from app.schemas.budget_scenario import BudgetScenarioCreate, ScenarioAdjustment
    from app.schemas.budget import BudgetCreate
    
    # Create base budget
    await budget_service.create_budget(
        session, test_workspace.id, test_user.id,
        BudgetCreate(
            category_id=test_category.id,
            amount=Decimal("1200.00"),
            month=date(2025, 10, 1),
            is_recurring=True
        )
    )
    
    # Create scenario with +200 fixed adjustment
    scenario = await budget_scenario_service.create_scenario(
        session, test_workspace.id, test_user.id,
        BudgetScenarioCreate(
            name="Rent Increase",
            base_month=date(2025, 10, 1),
            adjustments=[
                ScenarioAdjustment(
                    category_id=test_category.id,
                    adjustment_type="fixed",
                    value=Decimal("200")
                )
            ]
        )
    )
    
    # Preview
    preview = await budget_scenario_service.preview_scenario(
        session, scenario.id, test_workspace.id, 1
    )
    
    oct_entry = next(m for m in preview["months"] if m["month"] == "2025-10")
    assert oct_entry["base_amount"] == Decimal("1200.00")
    assert oct_entry["adjusted_amount"] == Decimal("1400.00")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/test_budget_scenario_service.py -v
```

Expected: FAIL with "module not found"

- [ ] **Step 3: Implement budget_scenario_service**

Create `backend/app/services/budget_scenario_service.py`:

```python
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget_scenario import BudgetScenario
from app.schemas.budget_scenario import BudgetScenarioCreate
from app.services.budget_service import get_budgets_multi_month


async def create_scenario(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    data: BudgetScenarioCreate,
) -> BudgetScenario:
    """Create a new budget scenario."""
    scenario = BudgetScenario(
        user_id=user_id,
        workspace_id=workspace_id,
        name=data.name,
        description=data.description,
        base_month=data.base_month.replace(day=1),
        adjustments={
            "categories": [
                {
                    "category_id": str(adj.category_id),
                    "adjustment_type": adj.adjustment_type,
                    "value": float(adj.value)
                }
                for adj in data.adjustments
            ]
        }
    )
    session.add(scenario)
    await session.commit()
    await session.refresh(scenario)
    return scenario


async def list_scenarios(
    session: AsyncSession,
    workspace_id: uuid.UUID,
) -> list[BudgetScenario]:
    """List all scenarios for a workspace."""
    result = await session.execute(
        select(BudgetScenario)
        .where(BudgetScenario.workspace_id == workspace_id)
        .order_by(BudgetScenario.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_scenario(
    session: AsyncSession,
    scenario_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> bool:
    """Delete a scenario."""
    result = await session.execute(
        select(BudgetScenario).where(
            BudgetScenario.id == scenario_id,
            BudgetScenario.workspace_id == workspace_id
        )
    )
    scenario = result.scalar_one_or_none()
    if not scenario:
        return False
    
    await session.delete(scenario)
    await session.commit()
    return True


async def preview_scenario(
    session: AsyncSession,
    scenario_id: uuid.UUID,
    workspace_id: uuid.UUID,
    months: int,
) -> dict:
    """Preview adjusted budgets for a scenario."""
    # Fetch scenario
    result = await session.execute(
        select(BudgetScenario).where(
            BudgetScenario.id == scenario_id,
            BudgetScenario.workspace_id == workspace_id
        )
    )
    scenario = result.scalar_one_or_none()
    if not scenario:
        raise ValueError("Scenario not found")
    
    # Calculate end month
    end_month = scenario.base_month
    for _ in range(months - 1):
        if end_month.month == 12:
            end_month = end_month.replace(year=end_month.year + 1, month=1)
        else:
            end_month = end_month.replace(month=end_month.month + 1)
    
    # Get base budgets
    base_budgets = await get_budgets_multi_month(
        session, workspace_id, scenario.base_month, end_month
    )
    
    # Apply adjustments
    adjusted_budgets = []
    for budget in base_budgets:
        adjusted_amount = budget.amount
        
        # Find matching adjustment
        for adj in scenario.adjustments["categories"]:
            if str(budget.category_id) == adj["category_id"]:
                if adj["adjustment_type"] == "percent":
                    adjusted_amount = budget.amount * (1 + Decimal(str(adj["value"])) / 100)
                elif adj["adjustment_type"] == "fixed":
                    adjusted_amount = budget.amount + Decimal(str(adj["value"]))
                break
        
        adjusted_budgets.append({
            "category_id": str(budget.category_id),
            "month": budget.month.strftime('%Y-%m'),
            "base_amount": budget.amount,
            "adjusted_amount": adjusted_amount,
        })
    
    return {"months": adjusted_budgets}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
pytest tests/test_budget_scenario_service.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/budget_scenario_service.py backend/tests/test_budget_scenario_service.py
git commit -m "feat(budgets): add scenario service with create/preview/adjust"
```

---

## Task 6: Budget API Endpoints

**Files:**
- Modify: `backend/app/api/budgets.py`
- Create: `backend/app/api/budget_templates.py`
- Create: `backend/app/api/budget_scenarios.py`
- Modify: `backend/app/main.py` (register routers)

**Interfaces:**
- Consumes: Services from Tasks 3-5
- Produces:
  - `GET /api/budgets/multi-month`
  - `GET /api/budgets/actuals`
  - `GET /api/budgets/export`
  - `POST /api/budgets/templates`, `GET /api/budgets/templates`, `DELETE /api/budgets/templates/{id}`, `POST /api/budgets/apply-template`
  - `POST /api/budgets/scenarios`, `GET /api/budgets/scenarios`, `GET /api/budgets/scenarios/{id}/preview`, `DELETE /api/budgets/scenarios/{id}`

- [ ] **Step 1: Add multi-month and actuals endpoints**

Edit `backend/app/api/budgets.py`, add after existing endpoints:

```python
@router.get("/multi-month", response_model=list[BudgetRead])
async def list_budgets_multi_month(
    start_month: date = Query(...),
    end_month: date = Query(...),
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    """Fetch budgets for multiple months with recurring resolution."""
    return await budget_service.get_budgets_multi_month(
        session, ctx.workspace.id, start_month, end_month
    )


@router.get("/actuals", response_model=BudgetActualsResponse)
async def list_budget_actuals(
    start_month: date = Query(...),
    end_month: date = Query(...),
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    """Fetch actual spending by category for multiple months."""
    category_actuals = await budget_service.get_actuals_multi_month(
        session, ctx.workspace.id, ctx.user_id, start_month, end_month
    )
    return BudgetActualsResponse(category_actuals=category_actuals)


@router.get("/export")
async def export_budgets_csv(
    start_month: date = Query(...),
    end_month: date = Query(...),
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    """Export budgets and actuals as CSV."""
    from fastapi.responses import StreamingResponse
    import io
    import csv
    
    # Fetch data
    budgets_list = await budget_service.get_budgets_multi_month(
        session, ctx.workspace.id, start_month, end_month
    )
    actuals = await budget_service.get_actuals_multi_month(
        session, ctx.workspace.id, ctx.user_id, start_month, end_month
    )
    categories = await categories_api.list(session, ctx.workspace.id)
    
    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Generate month columns
    months = []
    current = start_month.replace(day=1)
    while current <= end_month:
        months.append(current.strftime('%Y-%m'))
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    
    # Header row
    header = ['Category', 'Type']
    for month in months:
        header.extend([f'{month} Budget', f'{month} Actual'])
    writer.writerow(header)
    
    # Category rows
    budgets_by_cat = {}
    for b in budgets_list:
        key = (str(b.category_id), b.month.strftime('%Y-%m'))
        budgets_by_cat[key] = b.amount
    
    for cat in categories:
        row = [cat.name, cat.category_type]
        cat_id = str(cat.id)
        
        for month in months:
            budget_amt = budgets_by_cat.get((cat_id, month), '')
            actual_amt = actuals.get(cat_id, {}).get(month, '')
            row.extend([budget_amt, actual_amt])
        
        writer.writerow(row)
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=budgets_{start_month}_{end_month}.csv"}
    )
```

- [ ] **Step 2: Add import for BudgetActualsResponse**

At top of `backend/app/api/budgets.py`:

```python
from app.schemas.budget import BudgetActualsResponse
```

- [ ] **Step 3: Create budget_templates router**

Create `backend/app/api/budget_templates.py`:

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.workspace_context import WorkspaceContext, current_workspace, current_writable_workspace
from app.schemas.budget_template import (
    BudgetTemplateCreate,
    BudgetTemplateRead,
    BudgetTemplateApply,
    BudgetTemplateApplyResponse,
)
from app.services import budget_template_service

router = APIRouter(prefix="/api/budgets/templates", tags=["budget-templates"])


@router.get("", response_model=list[BudgetTemplateRead])
async def list_templates(
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    """List all budget templates for the workspace."""
    return await budget_template_service.list_templates(session, ctx.workspace.id)


@router.post("", response_model=BudgetTemplateRead, status_code=status.HTTP_201_CREATED)
async def create_template(
    data: BudgetTemplateCreate,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new budget template."""
    try:
        return await budget_template_service.create_template(
            session, ctx.workspace.id, ctx.user_id, data
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    """Delete a budget template."""
    deleted = await budget_template_service.delete_template(session, template_id, ctx.workspace.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")


@router.post("/apply", response_model=BudgetTemplateApplyResponse)
async def apply_template(
    data: BudgetTemplateApply,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    """Apply a template to create budgets for target months."""
    from datetime import datetime
    
    target_dates = [datetime.fromisoformat(m).date() for m in data.target_months]
    created_count = await budget_template_service.apply_template(
        session, ctx.workspace.id, ctx.user_id,
        data.template_id, target_dates, data.is_recurring
    )
    return BudgetTemplateApplyResponse(created_count=created_count)
```

- [ ] **Step 4: Create budget_scenarios router**

Create `backend/app/api/budget_scenarios.py`:

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.workspace_context import WorkspaceContext, current_workspace, current_writable_workspace
from app.schemas.budget_scenario import (
    BudgetScenarioCreate,
    BudgetScenarioRead,
    BudgetScenarioPreview,
)
from app.services import budget_scenario_service

router = APIRouter(prefix="/api/budgets/scenarios", tags=["budget-scenarios"])


@router.get("", response_model=list[BudgetScenarioRead])
async def list_scenarios(
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    """List all budget scenarios for the workspace."""
    return await budget_scenario_service.list_scenarios(session, ctx.workspace.id)


@router.post("", response_model=BudgetScenarioRead, status_code=status.HTTP_201_CREATED)
async def create_scenario(
    data: BudgetScenarioCreate,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new budget scenario."""
    try:
        return await budget_scenario_service.create_scenario(
            session, ctx.workspace.id, ctx.user_id, data
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{scenario_id}/preview", response_model=BudgetScenarioPreview)
async def preview_scenario(
    scenario_id: uuid.UUID,
    months: int = Query(12, ge=1, le=24),
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    """Preview adjusted budgets for a scenario."""
    try:
        preview = await budget_scenario_service.preview_scenario(
            session, scenario_id, ctx.workspace.id, months
        )
        return BudgetScenarioPreview(months=preview["months"])
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scenario(
    scenario_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    """Delete a budget scenario."""
    deleted = await budget_scenario_service.delete_scenario(session, scenario_id, ctx.workspace.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
```

- [ ] **Step 5: Register routers in main.py**

Edit `backend/app/main.py`, add after existing budget router registration:

```python
from app.api import budget_templates, budget_scenarios

app.include_router(budget_templates.router)
app.include_router(budget_scenarios.router)
```

- [ ] **Step 6: Test endpoints manually**

```bash
cd backend
# Start dev server
uvicorn app.main:app --reload

# In another terminal, test endpoints
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/budgets/multi-month?start_month=2025-09-01&end_month=2026-08-01"
```

Expected: JSON array of budgets

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/
git commit -m "feat(budgets): add API endpoints for multi-month, actuals, templates, scenarios"
```

---

## Task 7: Frontend - Install react-data-grid

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`

**Interfaces:**
- Consumes: npm registry
- Produces: `react-data-grid` available for import

- [ ] **Step 1: Install react-data-grid**

```bash
cd frontend
npm install react-data-grid@7.0.0-beta.44
```

- [ ] **Step 2: Verify installation**

```bash
npm list react-data-grid
```

Expected: `react-data-grid@7.0.0-beta.44`

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "feat(budgets): install react-data-grid for spreadsheet UI"
```

---

## Task 8: Frontend - API Client for Budget Spreadsheet

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/types/index.ts`

**Interfaces:**
- Consumes: Backend API endpoints from Task 6
- Produces:
  - `budgetsApi.multiMonth(startMonth, endMonth)`
  - `budgetsApi.actuals(startMonth, endMonth)`
  - `budgetsApi.createTemplate(...)`
  - `budgetsApi.applyTemplate(...)`
  - `budgetsApi.createScenario(...)`
  - `budgetsApi.previewScenario(...)`

- [ ] **Step 1: Add types**

Edit `frontend/src/types/index.ts`, add after existing Budget types:

```typescript
export interface BudgetActualsResponse {
  category_actuals: Record<string, Record<string, number>> // category_id -> { month -> amount }
}

export interface CategoryBudgetData {
  category_id: string
  amount: number
}

export interface BudgetTemplate {
  id: string
  user_id: string
  workspace_id: string
  name: string
  description: string | null
  template_data: {
    categories: CategoryBudgetData[]
  }
  created_at: string
  updated_at: string
}

export interface BudgetTemplateApplyResponse {
  created_count: number
}

export interface ScenarioAdjustment {
  category_id: string
  adjustment_type: 'percent' | 'fixed'
  value: number
}

export interface BudgetScenario {
  id: string
  user_id: string
  workspace_id: string
  name: string
  description: string | null
  base_month: string
  adjustments: {
    categories: ScenarioAdjustment[]
  }
  created_at: string
}

export interface ScenarioCategoryPreview {
  category_id: string
  month: string
  base_amount: number
  adjusted_amount: number
}

export interface BudgetScenarioPreview {
  months: ScenarioCategoryPreview[]
}
```

- [ ] **Step 2: Add API methods**

Edit `frontend/src/lib/api.ts`, modify the `budgets` export object:

```typescript
export const budgets = {
  list: async (month?: string): Promise<Budget[]> => {
    const { data } = await api.get('/budgets', { params: { month } })
    return data
  },
  multiMonth: async (startMonth: string, endMonth: string): Promise<Budget[]> => {
    const { data } = await api.get('/budgets/multi-month', {
      params: { start_month: startMonth, end_month: endMonth }
    })
    return data
  },
  actuals: async (startMonth: string, endMonth: string): Promise<BudgetActualsResponse> => {
    const { data } = await api.get('/budgets/actuals', {
      params: { start_month: startMonth, end_month: endMonth }
    })
    return data
  },
  create: async (budget: { category_id: string; amount: number; month: string; is_recurring?: boolean }): Promise<Budget> => {
    const { data } = await api.post('/budgets', budget)
    return data
  },
  update: async (id: string, budget: { amount?: number; apply_to_future?: boolean }): Promise<Budget> => {
    const { data } = await api.patch(`/budgets/${id}`, budget)
    return data
  },
  delete: async (id: string): Promise<void> => {
    await api.delete(`/budgets/${id}`)
  },
  comparison: async (month?: string): Promise<BudgetVsActual[]> => {
    const { data } = await api.get('/budgets/comparison', { params: { month } })
    return data
  },
  exportCsv: async (startMonth: string, endMonth: string): Promise<Blob> => {
    const { data } = await api.get('/budgets/export', {
      params: { start_month: startMonth, end_month: endMonth },
      responseType: 'blob'
    })
    return data
  },
  
  // Templates
  listTemplates: async (): Promise<BudgetTemplate[]> => {
    const { data } = await api.get('/budgets/templates')
    return data
  },
  createTemplate: async (template: {
    name: string
    description?: string
    categories: CategoryBudgetData[]
  }): Promise<BudgetTemplate> => {
    const { data } = await api.post('/budgets/templates', template)
    return data
  },
  deleteTemplate: async (id: string): Promise<void> => {
    await api.delete(`/budgets/templates/${id}`)
  },
  applyTemplate: async (input: {
    template_id: string
    target_months: string[]
    is_recurring: boolean
  }): Promise<BudgetTemplateApplyResponse> => {
    const { data} = await api.post('/budgets/templates/apply', input)
    return data
  },
  
  // Scenarios
  listScenarios: async (): Promise<BudgetScenario[]> => {
    const { data } = await api.get('/budgets/scenarios')
    return data
  },
  createScenario: async (scenario: {
    name: string
    description?: string
    base_month: string
    adjustments: ScenarioAdjustment[]
  }): Promise<BudgetScenario> => {
    const { data } = await api.post('/budgets/scenarios', scenario)
    return data
  },
  previewScenario: async (id: string, months: number): Promise<BudgetScenarioPreview> => {
    const { data } = await api.get(`/budgets/scenarios/${id}/preview`, { params: { months } })
    return data
  },
  deleteScenario: async (id: string): Promise<void> => {
    await api.delete(`/budgets/scenarios/${id}`)
  },
}
```

- [ ] **Step 3: Build to check for TypeScript errors**

```bash
cd frontend
npm run build
```

Expected: No TypeScript errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/types/index.ts
git commit -m "feat(budgets): add API client methods for multi-month, templates, scenarios"
```

---

---

## Task 9: Frontend - BudgetSpreadsheetPage Component (Core Structure)

**Files:**
- Modify: `frontend/src/pages/budgets.tsx` (complete rewrite)

**Interfaces:**
- Consumes: `budgetsApi.multiMonth()`, `budgetsApi.actuals()`, `categoriesApi.list()`, `goalsApi.list()`
- Produces: `BudgetSpreadsheetPage` component with data loading, month range calculation, row structure

- [ ] **Step 1: Create row structure types**

Replace content of `frontend/src/pages/budgets.tsx` with:

```typescript
import React, { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { budgets as budgetsApi, categories as categoriesApi, goals as goalsApi } from '@/lib/api'
import { PageHeader } from '@/components/page-header'
import { useAuth } from '@/contexts/auth-context'
import { useWorkspace } from '@/contexts/workspace-context'
import { addMonths, subMonths, startOfMonth, format } from 'date-fns'

interface BudgetGridRow {
  id: string
  type: 'category' | 'subtotal' | 'total' | 'section-header'
  categoryId?: string
  categoryName: string
  categoryType?: 'income' | 'expense' | 'investment'
  categoryIcon?: string
  categoryColor?: string
  enableRollover?: boolean
  linkedGoalId?: string
  isRecurring?: boolean
  months: Record<string, {
    budget: number | null
    budgetId?: string
    actual: number | null
    rollover?: number
    projected?: number
    isEditable: boolean
  }>
}

export default function BudgetSpreadsheetPage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const { canWrite } = useWorkspace()
  const queryClient = useQueryClient()
  
  // State: current center month for 12-month range
  const [selectedMonth, setSelectedMonth] = useState<Date>(startOfMonth(new Date()))
  
  // Calculate 12-month range: -5 months to +6 months
  const startMonth = useMemo(() => subMonths(selectedMonth, 5), [selectedMonth])
  const endMonth = useMemo(() => addMonths(selectedMonth, 6), [selectedMonth])
  
  const startMonthStr = format(startMonth, 'yyyy-MM-dd')
  const endMonthStr = format(endMonth, 'yyyy-MM-dd')
  
  // Fetch data in parallel
  const { data: budgetsList, isLoading: budgetsLoading } = useQuery({
    queryKey: ['budgets', 'multi-month', startMonthStr, endMonthStr],
    queryFn: () => budgetsApi.multiMonth(startMonthStr, endMonthStr),
  })
  
  const { data: actualsData, isLoading: actualsLoading } = useQuery({
    queryKey: ['budgets', 'actuals', startMonthStr, endMonthStr],
    queryFn: () => budgetsApi.actuals(startMonthStr, endMonthStr),
  })
  
  const { data: categoriesList, isLoading: categoriesLoading } = useQuery({
    queryKey: ['categories'],
    queryFn: categoriesApi.list,
  })
  
  const { data: goalsList } = useQuery({
    queryKey: ['goals'],
    queryFn: goalsApi.list,
  })
  
  const isLoading = budgetsLoading || actualsLoading || categoriesLoading
  
  // Build rows structure
  const rows = useMemo<BudgetGridRow[]>(() => {
    if (!categoriesList || !budgetsList || !actualsData) return []
    
    // Generate month keys
    const monthKeys: string[] = []
    let current = startMonth
    while (current <= endMonth) {
      monthKeys.push(format(current, 'yyyy-MM'))
      current = addMonths(current, 1)
    }
    
    // Group categories by type
    const incomeCategories = categoriesList.filter(c => c.category_type === 'income')
    const expenseCategories = categoriesList.filter(c => c.category_type === 'expense')
    const investmentCategories = categoriesList.filter(c => c.category_type === 'investment')
    
    // Build budget map: category_id -> month -> budget
    const budgetMap: Record<string, Record<string, { amount: number, budgetId: string, isRecurring: boolean }>> = {}
    budgetsList.forEach(b => {
      const catId = b.category_id
      const monthKey = format(new Date(b.month), 'yyyy-MM')
      if (!budgetMap[catId]) budgetMap[catId] = {}
      budgetMap[catId][monthKey] = { amount: b.amount, budgetId: b.id, isRecurring: b.is_recurring }
    })
    
    // Build category rows helper
    const buildCategoryRow = (cat: any): BudgetGridRow => {
      const catId = cat.id
      const months: Record<string, any> = {}
      
      monthKeys.forEach(monthKey => {
        const monthDate = new Date(monthKey + '-01')
        const isPast = monthDate < startOfMonth(new Date())
        const budgetEntry = budgetMap[catId]?.[monthKey]
        const actualAmount = actualsData.category_actuals[catId]?.[monthKey] ?? null
        
        months[monthKey] = {
          budget: budgetEntry?.amount ?? null,
          budgetId: budgetEntry?.budgetId,
          actual: actualAmount,
          rollover: 0, // TODO: Calculate rollover in next task
          projected: null, // TODO: Calculate projected in next task
          isEditable: !isPast && canWrite,
        }
      })
      
      return {
        id: catId,
        type: 'category',
        categoryId: catId,
        categoryName: cat.name,
        categoryType: cat.category_type,
        categoryIcon: cat.icon,
        categoryColor: cat.color,
        enableRollover: cat.enable_rollover,
        linkedGoalId: goalsList?.find(g => g.linked_category_ids?.includes(catId))?.id,
        isRecurring: budgetMap[catId]?.[monthKeys[0]]?.isRecurring ?? false,
        months,
      }
    }
    
    // Build subtotal row helper
    const buildSubtotalRow = (id: string, name: string, categoryRows: BudgetGridRow[]): BudgetGridRow => {
      const months: Record<string, any> = {}
      monthKeys.forEach(monthKey => {
        const budgetSum = categoryRows.reduce((sum, row) => sum + (row.months[monthKey]?.budget ?? 0), 0)
        const actualSum = categoryRows.reduce((sum, row) => sum + (row.months[monthKey]?.actual ?? 0), 0)
        months[monthKey] = {
          budget: budgetSum,
          budgetId: undefined,
          actual: actualSum,
          rollover: 0,
          projected: null,
          isEditable: false,
        }
      })
      
      return { id, type: 'subtotal', categoryName: name, months }
    }
    
    // Assemble rows
    const allRows: BudgetGridRow[] = []
    
    // Income section
    if (incomeCategories.length > 0) {
      allRows.push({ id: 'income-header', type: 'section-header', categoryName: 'INCOME', months: {} })
      const incomeRows = incomeCategories.map(buildCategoryRow)
      allRows.push(...incomeRows)
      allRows.push(buildSubtotalRow('income-subtotal', 'Income Subtotal', incomeRows))
    }
    
    // Expenses section
    if (expenseCategories.length > 0) {
      allRows.push({ id: 'expenses-header', type: 'section-header', categoryName: 'EXPENSES', months: {} })
      const expenseRows = expenseCategories.map(buildCategoryRow)
      allRows.push(...expenseRows)
      allRows.push(buildSubtotalRow('expenses-subtotal', 'Expenses Subtotal', expenseRows))
    }
    
    // Investments section
    if (investmentCategories.length > 0) {
      allRows.push({ id: 'investments-header', type: 'section-header', categoryName: 'INVESTMENTS', months: {} })
      const investmentRows = investmentCategories.map(buildCategoryRow)
      allRows.push(...investmentRows)
      allRows.push(buildSubtotalRow('investments-subtotal', 'Investments Subtotal', investmentRows))
    }
    
    // Net Savings total row
    const netSavingsMonths: Record<string, any> = {}
    monthKeys.forEach(monthKey => {
      const income = allRows.find(r => r.id === 'income-subtotal')?.months[monthKey]?.budget ?? 0
      const expenses = allRows.find(r => r.id === 'expenses-subtotal')?.months[monthKey]?.budget ?? 0
      const investments = allRows.find(r => r.id === 'investments-subtotal')?.months[monthKey]?.budget ?? 0
      netSavingsMonths[monthKey] = {
        budget: income - expenses - investments,
        actual: null,
        isEditable: false,
      }
    })
    allRows.push({ id: 'net-savings', type: 'total', categoryName: 'NET SAVINGS', months: netSavingsMonths })
    
    return allRows
  }, [categoriesList, budgetsList, actualsData, goalsList, startMonth, endMonth, canWrite])
  
  if (isLoading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>
  }
  
  return (
    <div className="space-y-6">
      <PageHeader
        section={t('budgets.title')}
        title="12-Month Budget Spreadsheet"
      />
      
      <div className="text-sm text-muted-foreground">
        Showing {format(startMonth, 'MMM yyyy')} - {format(endMonth, 'MMM yyyy')}
      </div>
      
      {/* Placeholder for TrendSummaryBar */}
      <div className="border-2 border-dashed border-muted rounded-lg p-8 text-center text-muted-foreground">
        Trend Summary Bar (Task 11)
      </div>
      
      {/* Placeholder for BudgetDataGrid */}
      <div className="border-2 border-dashed border-muted rounded-lg p-8">
        <p className="text-muted-foreground">Budget Data Grid (Task 9 continued)</p>
        <p className="text-sm text-muted-foreground mt-2">
          {rows.length} rows loaded
        </p>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Test page loads**

```bash
cd frontend
npm run dev
# Visit http://localhost:3000/budgets
```

Expected: Page loads with placeholders, no errors in console

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/budgets.tsx
git commit -m "feat(budgets): add BudgetSpreadsheetPage skeleton with row structure"
```

---

_The implementation plan is quite extensive. To keep this response manageable, I've written Tasks 1-9 covering the full backend implementation and the frontend data structure. The remaining 10 tasks (grid rendering, editing, visualizations, mobile, notifications) follow the same detailed pattern._

_Would you like me to:_
1. **Continue writing all remaining tasks** in the plan file (Tasks 10-19)
2. **Save the plan as-is and begin execution** with what's written
3. **Show you a summary** of the remaining tasks without full step-by-step detail