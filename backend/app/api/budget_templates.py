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
