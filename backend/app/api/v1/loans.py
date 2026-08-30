"""Loan schedule API routes."""
import csv
import io
import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_workspace_access
from app.schemas.loan_schedule import LoanScheduleEntryRead
from app.services import loan_schedule_service

router = APIRouter()


@router.get("/{account_id}/schedule", response_model=list[LoanScheduleEntryRead])
async def get_loan_schedule(
    account_id: uuid.UUID,
    status: Optional[str] = Query(None, pattern="^(scheduled|paid|partial|missed|skipped)$"),
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    workspace_id: uuid.UUID = Depends(require_workspace_access),
):
    """Retrieve amortization schedule for a loan account."""
    entries = await loan_schedule_service.get_schedule(
        db=db,
        account_id=account_id,
        workspace_id=workspace_id,
        status=status,
        from_date=from_date,
        to_date=to_date,
    )

    if not entries:
        # Check if account exists
        from app.models.account import Account
        from sqlalchemy import select

        result = await db.execute(
            select(Account).where(
                Account.id == account_id,
                Account.workspace_id == workspace_id,
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

    return entries


@router.get("/{account_id}/schedule/export")
async def export_schedule_csv(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    workspace_id: uuid.UUID = Depends(require_workspace_access),
):
    """Export loan schedule as CSV."""
    entries = await loan_schedule_service.get_schedule(
        db=db,
        account_id=account_id,
        workspace_id=workspace_id,
    )

    if not entries:
        raise HTTPException(status_code=404, detail="No schedule found")

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "EMI Number",
        "Due Date",
        "Principal",
        "Interest",
        "EMI Amount",
        "Opening Balance",
        "Closing Balance",
        "Status",
    ])

    for entry in entries:
        writer.writerow([
            entry.emi_number,
            entry.due_date.isoformat(),
            str(entry.principal_component),
            str(entry.interest_component),
            str(entry.emi_amount),
            str(entry.opening_balance),
            str(entry.closing_balance),
            entry.payment_status,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=loan_{account_id}_schedule.csv"},
    )
