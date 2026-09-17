"""Mutual Fund API endpoints."""
from uuid import UUID
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.mutual_fund_service import MutualFundService

router = APIRouter(prefix="/api/mutual-funds", tags=["mutual_funds"])

@router.post("/cas-import")
async def import_cas(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files supported")
    pdf_bytes = await file.read()
    if len(pdf_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")
    service = MutualFundService(db, current_user.workspace_id)
    try:
        result = await service.import_cas(pdf_bytes)
        return {"success": True, "message": f"Imported {result['imported_schemes']} schemes", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/portfolio")
async def get_portfolio(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = MutualFundService(db, current_user.workspace_id)
    portfolio = await service.get_portfolio_summary()
    return {"success": True, "data": portfolio}

@router.get("/sips")
async def get_sips(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    service = MutualFundService(db, current_user.workspace_id)
    sips = await service.get_sips()
    return {"success": True, "data": sips}

@router.post("/goals/{goal_id}/link-asset/{asset_id}")
async def link_asset_to_goal(goal_id: UUID, asset_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from datetime import datetime
    from app.models.goal_asset import GoalAsset
    link = GoalAsset(goal_id=goal_id, asset_id=asset_id, created_at=datetime.utcnow())
    db.add(link)
    db.commit()
    return {"success": True, "message": "Asset linked to goal"}
