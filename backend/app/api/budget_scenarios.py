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
