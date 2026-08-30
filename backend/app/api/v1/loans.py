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
    PrepaymentCreate,
    PrepaymentSimulation,
    PrepaymentRead,
    AutoLinkRequest,
)
from app.services import loan_schedule_service, loan_payment_service

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



@router.post("/prepayments/simulate")
async def simulate_prepayment(
    simulation_data: PrepaymentSimulation,
    db: AsyncSession = Depends(get_db),
    workspace_id: uuid.UUID = Depends(require_workspace_access),
):
    """Simulate prepayment options (reduce_emi vs reduce_tenure)."""
    result = await loan_payment_service.simulate_prepayment(
        db=db,
        account_id=simulation_data.account_id,
        workspace_id=workspace_id,
        prepayment_amount=simulation_data.prepayment_amount,
        annual_interest_rate=simulation_data.annual_interest_rate,
        current_emi_number=simulation_data.current_emi_number,
    )

    return result


@router.post("/prepayments", response_model=PrepaymentRead)
async def record_prepayment(
    prepayment_data: PrepaymentCreate,
    db: AsyncSession = Depends(get_db),
    workspace_id: uuid.UUID = Depends(require_workspace_access),
):
    """Record a prepayment and regenerate schedule."""
    prepayment = await loan_payment_service.record_prepayment(
        db=db,
        account_id=prepayment_data.account_id,
        workspace_id=workspace_id,
        prepayment_amount=prepayment_data.prepayment_amount,
        annual_interest_rate=prepayment_data.annual_interest_rate,
        current_emi_number=prepayment_data.current_emi_number,
        recalculation_method=prepayment_data.recalculation_method,
    )

    if not prepayment:
        raise HTTPException(status_code=404, detail="Account not found")

    return prepayment


@router.get("/{account_id}/prepayments", response_model=list[PrepaymentRead])
async def list_prepayments(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    workspace_id: uuid.UUID = Depends(require_workspace_access),
):
    """List prepayment history for a loan account."""
    from app.models.loan_prepayment import LoanPrepayment
    from sqlalchemy import select

    result = await db.execute(
        select(LoanPrepayment)
        .where(
            LoanPrepayment.account_id == account_id,
            LoanPrepayment.workspace_id == workspace_id,
        )
        .order_by(LoanPrepayment.created_at.desc())
    )
    prepayments = result.scalars().all()
    return prepayments


@router.post("/schedule/auto-link")
async def auto_link_transactions(
    link_data: AutoLinkRequest,
    db: AsyncSession = Depends(get_db),
    workspace_id: uuid.UUID = Depends(require_workspace_access),
):
    """Auto-link transactions to schedule entries with confidence scoring."""
    from app.schemas.loan_schedule import AutoLinkRequest
    
    matches = await loan_payment_service.auto_link_transactions(
        db=db,
        account_id=link_data.account_id,
        workspace_id=workspace_id,
        date_tolerance_days=link_data.date_tolerance_days,
        amount_tolerance_percent=link_data.amount_tolerance_percent,
    )

    return {"linked_count": len(matches), "matches": matches}


@router.post("/schedule/{entry_id}/link", response_model=LoanScheduleEntryRead)
async def manual_link_transaction(
    entry_id: uuid.UUID,
    link_data: dict,
    db: AsyncSession = Depends(get_db),
    workspace_id: uuid.UUID = Depends(require_workspace_access),
):
    """Manually link a transaction to a schedule entry."""
    transaction_id = uuid.UUID(link_data["transaction_id"])
    
    # Update the schedule entry
    updated = await loan_schedule_service.update_schedule_entry(
        db=db,
        entry_id=entry_id,
        workspace_id=workspace_id,
        update_data={
            "linked_transaction_id": transaction_id,
            "payment_status": "paid",
        },
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
