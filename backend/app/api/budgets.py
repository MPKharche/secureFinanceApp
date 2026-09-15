import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.workspace_context import (
    WorkspaceContext,
    current_workspace,
    current_writable_workspace,
)
from app.schemas.budget import BudgetCreate, BudgetRead, BudgetUpdate, BudgetVsActual, BudgetActualsResponse
from app.services import budget_service
from app.services import category_service

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


@router.get("", response_model=list[BudgetRead])
async def list_budgets(
    month: Optional[date] = Query(None),
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    return await budget_service.get_budgets(session, ctx.workspace.id, month)


@router.post("", response_model=BudgetRead, status_code=status.HTTP_201_CREATED)
async def create_budget(
    data: BudgetCreate,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        return await budget_service.create_budget(session, ctx.workspace.id, ctx.user_id, data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/{budget_id}", response_model=BudgetRead)
async def update_budget(
    budget_id: uuid.UUID,
    data: BudgetUpdate,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    budget = await budget_service.update_budget(session, budget_id, ctx.workspace.id, data)
    if not budget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    return budget


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_budget(
    budget_id: uuid.UUID,
    ctx: WorkspaceContext = Depends(current_writable_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    deleted = await budget_service.delete_budget(session, budget_id, ctx.workspace.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")


@router.get("/comparison", response_model=list[BudgetVsActual])
async def budget_comparison(
    month: Optional[date] = Query(None),
    ctx: WorkspaceContext = Depends(current_workspace),
    session: AsyncSession = Depends(get_async_session),
):
    return await budget_service.get_budget_vs_actual(session, ctx.workspace.id, ctx.user_id, month)


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
    categories = await category_service.get_categories(session, ctx.workspace.id)
    
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
