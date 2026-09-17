"""Mutual Fund API endpoints."""
from uuid import UUID
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_session
from app.core.workspace_context import WorkspaceContext, current_writable_workspace
from app.services.mutual_fund_service import MutualFundService

router = APIRouter(prefix="/api/mutual-funds", tags=["mutual_funds"])

@router.post("/cas-import")
async def import_cas(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_writable_workspace)
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files supported")
    pdf_bytes = await file.read()
    if len(pdf_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")
    service = MutualFundService(session, workspace.workspace_id)
    try:
        result = await service.import_cas(pdf_bytes)
        return {"success": True, "message": f"Imported {result['imported_schemes']} schemes", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/portfolio")
async def get_portfolio(
    session: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_writable_workspace)
):
    service = MutualFundService(session, workspace.workspace_id)
    portfolio = await service.get_portfolio_summary()
    return {"success": True, "data": portfolio}

@router.get("/sips")
async def get_sips(
    session: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_writable_workspace)
):
    service = MutualFundService(session, workspace.workspace_id)
    sips = await service.get_sips()
    return {"success": True, "data": sips}

@router.post("/goals/{goal_id}/link-asset/{asset_id}")
async def link_asset_to_goal(
    goal_id: UUID,
    asset_id: UUID,
    session: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_writable_workspace)
):
    from datetime import datetime
    from app.models.goal_asset import GoalAsset
    link = GoalAsset(goal_id=goal_id, asset_id=asset_id, created_at=datetime.utcnow())
    session.add(link)
    await session.commit()
    return {"success": True, "message": "Asset linked to goal"}
