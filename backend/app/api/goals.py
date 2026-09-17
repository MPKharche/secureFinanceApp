import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.workspace_context import (
    WorkspaceContext,
    current_workspace,
    current_writable_workspace,
)
from app.schemas.goal import (
    GoalCreate,
    GoalRead,
    GoalSummary,
    GoalTemplate,
    GoalTemplateCalculation,
    GoalUpdate,
)
from app.services import goal_service
from app.data.goal_templates import list_templates, calculate_recommended_amount

router = APIRouter(prefix="/api/goals", tags=["goals"])


@router.get("", response_model=list[GoalRead])
async def list_goals(
    status: Optional[str] = Query(None),
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    return await goal_service.get_goals(session, ctx.workspace.id, ctx.user_id, status)


@router.get("/summary", response_model=list[GoalSummary])
async def goal_summary(
    limit: int = Query(3, ge=1, le=10),
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    return await goal_service.get_goal_summary(session, ctx.workspace.id, ctx.user_id, limit)


@router.post("", response_model=GoalRead, status_code=status.HTTP_201_CREATED)
async def create_goal(
    data: GoalCreate,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        return await goal_service.create_goal(session, ctx.workspace.id, ctx.user_id, data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{goal_id}", response_model=GoalRead)
async def get_goal(
    goal_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    goal = await goal_service.get_goal(session, goal_id, ctx.workspace.id, ctx.user_id)
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    return goal


@router.patch("/{goal_id}", response_model=GoalRead)
async def update_goal(
    goal_id: uuid.UUID,
    data: GoalUpdate,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        goal = await goal_service.update_goal(session, goal_id, ctx.workspace.id, ctx.user_id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    return goal


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    deleted = await goal_service.delete_goal(session, goal_id, ctx.workspace.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")


@router.get("/templates", response_model=list[GoalTemplate])
async def get_goal_templates(
    language: str = Query("en", regex="^(en|hi)$"),
):
    """Get list of India-specific goal templates."""
    return list_templates(language)


@router.post("/templates/calculate", response_model=dict)
async def calculate_template_amount(
    data: GoalTemplateCalculation,
):
    """Calculate recommended amount for a goal template."""
    try:
        amount = calculate_recommended_amount(
            template_type=data.template_type,
            monthly_expenses=data.monthly_expenses,
            age=data.age,
            retirement_age=data.retirement_age,
            currency=data.currency,
        )
        return {
            "template_type": data.template_type,
            "recommended_amount": float(amount),
            "currency": data.currency,
        }
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid template_type: {data.template_type}"
        )
