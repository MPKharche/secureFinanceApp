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
from app.schemas.loan_schedule import (
    LoanScheduleEntryRead,
    ScheduleEntryUpdate,
    BulkDateUpdate,
    StatusUpdate,
)
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


@router.patch("/schedule/{entry_id}", response_model=LoanScheduleEntryRead)
async def update_schedule_entry(
    entry_id: uuid.UUID,
    update_data: ScheduleEntryUpdate,
    db: AsyncSession = Depends(get_db),
    workspace_id: uuid.UUID = Depends(require_workspace_access),
):
    """Update a single schedule entry (due date, EMI amount, etc)."""
    updated = await loan_schedule_service.update_schedule_entry(
        db=db,
        entry_id=entry_id,
        workspace_id=workspace_id,
        update_data=update_data.model_dump(exclude_unset=True),
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Schedule entry not found")

    # Fetch and return the updated entry
    from app.models.loan_schedule import LoanAmortizationSchedule
    from sqlalchemy import select

    result = await db.execute(
        select(LoanAmortizationSchedule).where(
            LoanAmortizationSchedule.id == entry_id,
            LoanAmortizationSchedule.workspace_id == workspace_id,
        )
    )
    entry = result.scalar_one()
    return entry


@router.post("/schedule/bulk-update-dates")
async def bulk_update_dates(
    update_data: BulkDateUpdate,
    db: AsyncSession = Depends(get_db),
    workspace_id: uuid.UUID = Depends(require_workspace_access),
):
    """Bulk update due dates (shift or change EMI day)."""
    updated_count = await loan_schedule_service.bulk_update_dates(
        db=db,
        account_id=update_data.account_id,
        workspace_id=workspace_id,
        from_emi_number=update_data.from_emi_number,
        shift_days=update_data.shift_days,
        new_day_of_month=update_data.new_day_of_month,
    )

    return {"updated_count": updated_count}


@router.put("/schedule/{entry_id}/status", response_model=LoanScheduleEntryRead)
async def mark_entry_status(
    entry_id: uuid.UUID,
    status_data: StatusUpdate,
    db: AsyncSession = Depends(get_db),
    workspace_id: uuid.UUID = Depends(require_workspace_access),
):
    """Mark a schedule entry's payment status."""
    updated = await loan_schedule_service.update_schedule_entry(
        db=db,
        entry_id=entry_id,
        workspace_id=workspace_id,
        update_data={"payment_status": status_data.payment_status},
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Schedule entry not found")

    # Fetch and return the updated entry
    from app.models.loan_schedule import LoanAmortizationSchedule
    from sqlalchemy import select

    result = await db.execute(
        select(LoanAmortizationSchedule).where(
            LoanAmortizationSchedule.id == entry_id,
            LoanAmortizationSchedule.workspace_id == workspace_id,
        )
    )
    entry = result.scalar_one()
    return entry

