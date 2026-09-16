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
