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
