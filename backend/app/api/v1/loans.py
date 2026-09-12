"""Loan schedule API routes."""
import csv
import io
import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.workspace_context import WorkspaceContext, current_workspace, current_writable_workspace
from sqlalchemy import select

from app.models.account import Account
from app.schemas.loan_schedule import (
    LoanScheduleEntryRead,
    LoanScheduleEntryUpdate,
    BulkUpdateDatesRequest,
    MarkPaymentStatusRequest,
    PrepaymentCreate,
    PrepaymentSimulation,
    PrepaymentRead,
    AutoLinkRequest,
)
from app.schemas.loan_commitment import (
    CombinedSimulationRequest,
    CommitmentCreate,
    CommitmentRead,
)
from app.services import loan_schedule_service, loan_payment_service
from app.services import loan_combined_simulation_service, loan_commitment_service

router = APIRouter()


@router.get("/{account_id}/schedule", response_model=list[LoanScheduleEntryRead])
async def get_loan_schedule(
    account_id: uuid.UUID,
    status: Optional[str] = Query(None, pattern="^(scheduled|paid|partial|missed|skipped)$"),
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Retrieve amortization schedule for a loan account."""
    entries = await loan_schedule_service.get_schedule(
        db=db,
        account_id=account_id,
        workspace_id=workspace.id,
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
                Account.workspace_id == workspace.id,
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

    return entries


@router.get("/{account_id}/schedule/export")
async def export_schedule_csv(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Export loan schedule as CSV."""
    entries = await loan_schedule_service.get_schedule(
        db=db,
        account_id=account_id,
        workspace_id=workspace.id,
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
    update_data: LoanScheduleEntryUpdate,
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Update a single schedule entry (due date, EMI amount, etc)."""
    updated = await loan_schedule_service.update_schedule_entry(
        db=db,
        entry_id=entry_id,
        workspace_id=workspace.id,
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
            LoanAmortizationSchedule.workspace_id == workspace.id,
        )
    )
    entry = result.scalar_one()
    return entry


@router.post("/schedule/bulk-update-dates")
async def bulk_update_dates(
    update_data: BulkUpdateDatesRequest,
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Bulk update due dates (shift or change EMI day)."""
    updated_count = await loan_schedule_service.bulk_update_dates(
        db=db,
        account_id=update_data.account_id,
        workspace_id=workspace.id,
        from_emi_number=update_data.from_emi_number,
        shift_days=update_data.shift_days,
        new_day_of_month=update_data.new_day_of_month,
    )

    return {"updated_count": updated_count}


@router.put("/schedule/{entry_id}/status", response_model=LoanScheduleEntryRead)
async def mark_entry_status(
    entry_id: uuid.UUID,
    status_data: MarkPaymentStatusRequest,
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Mark a schedule entry's payment status."""
    updated = await loan_schedule_service.update_schedule_entry(
        db=db,
        entry_id=entry_id,
        workspace_id=workspace.id,
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
            LoanAmortizationSchedule.workspace_id == workspace.id,
        )
    )
    entry = result.scalar_one()
    return entry



@router.post("/prepayments/simulate")
async def simulate_prepayment(
    simulation_data: PrepaymentSimulation,
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Simulate prepayment options (reduce_emi vs reduce_tenure)."""
    result = await loan_payment_service.simulate_prepayment(
        db=db,
        account_id=simulation_data.account_id,
        workspace_id=workspace.id,
        prepayment_amount=simulation_data.prepayment_amount,
        annual_interest_rate=simulation_data.annual_interest_rate,
        current_emi_number=simulation_data.current_emi_number,
    )

    return result


@router.post("/prepayments", response_model=PrepaymentRead)
async def record_prepayment(
    prepayment_data: PrepaymentCreate,
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Record a prepayment and regenerate schedule."""
    prepayment = await loan_payment_service.record_prepayment(
        db=db,
        account_id=prepayment_data.account_id,
        workspace_id=workspace.id,
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
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """List prepayment history for a loan account."""
    from app.models.loan_prepayment import LoanPrepayment
    from sqlalchemy import select

    result = await db.execute(
        select(LoanPrepayment)
        .where(
            LoanPrepayment.account_id == account_id,
            LoanPrepayment.workspace_id == workspace.id,
        )
        .order_by(LoanPrepayment.created_at.desc())
    )
    prepayments = result.scalars().all()
    return prepayments


@router.post("/schedule/auto-link")
async def auto_link_transactions(
    link_data: AutoLinkRequest,
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Auto-link transactions to schedule entries with confidence scoring."""
    from app.schemas.loan_schedule import AutoLinkRequest
    
    matches = await loan_payment_service.auto_link_transactions(
        db=db,
        account_id=link_data.account_id,
        workspace_id=workspace.id,
        date_tolerance_days=link_data.date_tolerance_days,
        amount_tolerance_percent=link_data.amount_tolerance_percent,
    )

    return {"linked_count": len(matches), "matches": matches}


@router.post("/schedule/{entry_id}/link", response_model=LoanScheduleEntryRead)
async def manual_link_transaction(
    entry_id: uuid.UUID,
    link_data: dict,
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Manually link a transaction to a schedule entry."""
    transaction_id = uuid.UUID(link_data["transaction_id"])
    
    # Update the schedule entry
    updated = await loan_schedule_service.update_schedule_entry(
        db=db,
        entry_id=entry_id,
        workspace_id=workspace.id,
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
            LoanAmortizationSchedule.workspace_id == workspace.id,
        )
    )
    entry = result.scalar_one()
    return entry


@router.get("/{account_id}/overview")
async def get_loan_overview(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Get loan overview metrics (progress, principal/interest breakdown)."""
    from app.services import loan_analytics_service
    
    overview = await loan_analytics_service.get_loan_overview(
        db=db,
        account_id=account_id,
        workspace_id=workspace.id,
    )

    if not overview:
        raise HTTPException(status_code=404, detail="Account not found")

    return overview


@router.get("/{account_id}/breakdown")
async def get_yearly_breakdown(
    account_id: uuid.UUID,
    group_by: str = Query("year", pattern="^(year|quarter|month)$"),
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Get yearly/quarterly/monthly breakdown of payments."""
    from app.services import loan_analytics_service
    
    breakdown = await loan_analytics_service.get_yearly_breakdown(
        db=db,
        account_id=account_id,
        workspace_id=workspace.id,
        group_by=group_by,
    )

    return breakdown


@router.get("/debt-ratios")
async def calculate_debt_ratios(
    monthly_income: Optional[Decimal] = None,
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Calculate debt-to-income and other financial ratios."""
    from app.services import loan_analytics_service
    
    ratios = await loan_analytics_service.calculate_debt_ratios(
        db=db,
        workspace_id=workspace.id,
        monthly_income=monthly_income,
    )

    return ratios


@router.get("/dashboard")
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Get dashboard summary with next payments, recent activity, and alerts."""
    from app.services import loan_analytics_service
    
    summary = await loan_analytics_service.get_dashboard_summary(
        db=db,
        workspace_id=workspace.id,
    )

    return summary


@router.post("/schedule/regenerate")
async def regenerate_schedule(
    regenerate_data: dict,
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Regenerate loan schedule from a specific EMI number with new parameters."""
    from decimal import Decimal
    from datetime import date
    
    account_id = uuid.UUID(regenerate_data["account_id"])
    from_emi_number = regenerate_data["from_emi_number"]
    new_principal = Decimal(regenerate_data["new_principal"])
    new_annual_rate = Decimal(regenerate_data["new_annual_rate"])
    new_tenure_months = regenerate_data["new_tenure_months"]
    start_date = date.fromisoformat(regenerate_data["start_date"])

    if from_emi_number < 1:
        raise HTTPException(status_code=422, detail="from_emi_number must be >= 1")

    entries = await loan_schedule_service.regenerate_schedule(
        db=db,
        account_id=account_id,
        workspace_id=workspace.id,
        from_emi_number=from_emi_number,
        new_principal=new_principal,
        new_annual_rate=new_annual_rate,
        new_tenure_months=new_tenure_months,
        start_date=start_date,
    )

    if not entries:
        raise HTTPException(status_code=404, detail="Account not found")

    # Get the new version number
    new_version = entries[0].schedule_version if entries else None

    return {
        "new_schedule_version": new_version,
        "entries_created": len(entries),
    }


@router.post("/schedule/bulk-mark-status")
async def bulk_mark_status(
    bulk_data: dict,
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Bulk mark payment status for multiple schedule entries."""
    entry_ids = [uuid.UUID(id_str) for id_str in bulk_data["entry_ids"]]
    payment_status = bulk_data["payment_status"]
    
    if payment_status not in ["scheduled", "paid", "partial", "missed", "skipped"]:
        raise HTTPException(status_code=422, detail="Invalid payment_status")
    
    from app.models.loan_schedule import LoanAmortizationSchedule
    from sqlalchemy import update
    
    stmt = (
        update(LoanAmortizationSchedule)
        .where(
            LoanAmortizationSchedule.id.in_(entry_ids),
            LoanAmortizationSchedule.workspace_id == workspace.id,
        )
        .values(payment_status=payment_status)
    )
    
    result = await db.execute(stmt)
    await db.commit()
    
    return {"updated_count": result.rowcount}


@router.post("/schedule/bulk-delete")
async def bulk_delete_schedules(
    bulk_data: dict,
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Bulk delete schedule entries for specific accounts and version."""
    account_ids = [uuid.UUID(id_str) for id_str in bulk_data["account_ids"]]
    schedule_version = bulk_data["schedule_version"]
    
    from app.models.loan_schedule import LoanAmortizationSchedule
    from sqlalchemy import delete
    
    stmt = (
        delete(LoanAmortizationSchedule)
        .where(
            LoanAmortizationSchedule.account_id.in_(account_ids),
            LoanAmortizationSchedule.schedule_version == schedule_version,
            LoanAmortizationSchedule.workspace_id == workspace.id,
        )
    )
    
    result = await db.execute(stmt)
    await db.commit()
    
    return {"deleted_count": result.rowcount}


@router.post("/schedule/bulk-export")
async def bulk_export_schedules(
    bulk_data: dict,
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Bulk export schedules for multiple loans as ZIP file."""
    import zipfile
    from io import BytesIO
    
    account_ids = [uuid.UUID(id_str) for id_str in bulk_data["account_ids"]]
    
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for account_id in account_ids:
            entries = await loan_schedule_service.get_schedule(
                db=db,
                account_id=account_id,
                workspace_id=workspace.id,
            )
            
            if entries:
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow([
                    "EMI Number", "Due Date", "Principal", "Interest",
                    "EMI Amount", "Opening Balance", "Closing Balance", "Status"
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
                
                zip_file.writestr(f"loan_{account_id}_schedule.csv", output.getvalue())
    
    zip_buffer.seek(0)
    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=loan_schedules.zip"},
    )


@router.post("/calculate-emi")
async def calculate_emi(
    calc_data: dict,
    db: AsyncSession = Depends(get_async_session),
):
    """Calculate EMI for given loan parameters."""
    from decimal import Decimal
    
    principal = Decimal(calc_data["principal"])
    annual_rate = Decimal(calc_data["annual_rate"])
    tenure_months = calc_data["tenure_months"]
    
    if principal <= 0 or tenure_months <= 0:
        raise HTTPException(status_code=422, detail="Principal and tenure must be positive")
    
    emi = loan_schedule_service.calculate_emi(principal, annual_rate, tenure_months)
    total_payment = emi * tenure_months
    total_interest = total_payment - principal
    
    return {
        "emi_amount": str(emi),
        "total_interest": str(total_interest),
        "total_payment": str(total_payment),
    }


@router.post("/validate-schedule")
async def validate_schedule(
    validate_data: dict,
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Validate schedule integrity (balance continuity, EMI consistency)."""
    from decimal import Decimal
    from sqlalchemy import select
    from app.models.loan_schedule import LoanAmortizationSchedule
    
    account_id = uuid.UUID(validate_data["account_id"])
    
    result = await db.execute(
        select(LoanAmortizationSchedule)
        .where(
            LoanAmortizationSchedule.account_id == account_id,
            LoanAmortizationSchedule.workspace_id == workspace.id,
        )
        .order_by(LoanAmortizationSchedule.schedule_version, LoanAmortizationSchedule.emi_number)
    )
    entries = result.scalars().all()
    
    issues = []
    is_valid = True
    
    for i, entry in enumerate(entries):
        # Check balance continuity
        expected_closing = entry.opening_balance - entry.principal_component
        if abs(entry.closing_balance - expected_closing) > Decimal("0.01"):
            issues.append(f"EMI {entry.emi_number}: Balance mismatch")
            is_valid = False
        
        # Check EMI sum
        expected_emi = entry.principal_component + entry.interest_component
        if abs(entry.emi_amount - expected_emi) > Decimal("0.01"):
            issues.append(f"EMI {entry.emi_number}: EMI component mismatch")
            is_valid = False
        
        # Check opening balance continuity
        if i > 0 and entries[i-1].schedule_version == entry.schedule_version:
            if abs(entry.opening_balance - entries[i-1].closing_balance) > Decimal("0.01"):
                issues.append(f"EMI {entry.emi_number}: Opening balance doesn't match previous closing")
                is_valid = False
    
    return {"is_valid": is_valid, "issues": issues}


@router.get("/summary")
async def get_loan_summary(
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Get summary of all loans in workspace."""
    from sqlalchemy import select, func
    from app.models.account import Account
    from app.models.loan_schedule import LoanAmortizationSchedule
    
    # Get all loan accounts
    result = await db.execute(
        select(Account).where(
            Account.workspace_id == workspace.id,
            Account.subtype == "loan",
        )
    )
    accounts = result.scalars().all()
    
    total_outstanding = sum(abs(acc.balance) for acc in accounts)
    
    # Get total monthly EMI
    total_emi = Decimal("0.00")
    for acc in accounts:
        result = await db.execute(
            select(LoanAmortizationSchedule.emi_amount)
            .where(
                LoanAmortizationSchedule.account_id == acc.id,
                LoanAmortizationSchedule.schedule_version == acc.current_schedule_version,
                LoanAmortizationSchedule.payment_status == "scheduled",
            )
            .limit(1)
        )
        emi = result.scalar()
        if emi:
            total_emi += emi
    
    return {
        "total_loans": len(accounts),
        "total_outstanding": str(total_outstanding),
        "total_monthly_emi": str(total_emi),
        "accounts": [{"id": str(acc.id), "name": acc.name, "balance": str(acc.balance)} for acc in accounts],
    }


@router.post("/calculate-savings")
async def calculate_prepayment_savings(
    savings_data: dict,
    db: AsyncSession = Depends(get_async_session),
):
    """Calculate interest savings from prepayment."""
    from decimal import Decimal
    import math
    
    remaining_principal = Decimal(savings_data["remaining_principal"])
    annual_rate = Decimal(savings_data["annual_rate"])
    remaining_months = savings_data["remaining_months"]
    prepayment_amount = Decimal(savings_data["prepayment_amount"])
    
    # Calculate original interest
    original_emi = loan_schedule_service.calculate_emi(remaining_principal, annual_rate, remaining_months)
    original_total = original_emi * remaining_months
    original_interest = original_total - remaining_principal
    
    # After prepayment principal
    new_principal = remaining_principal - prepayment_amount
    
    # Reduce EMI option
    new_emi = loan_schedule_service.calculate_emi(new_principal, annual_rate, remaining_months)
    new_total_reduce_emi = new_emi * remaining_months
    new_interest_reduce_emi = new_total_reduce_emi - new_principal
    savings_reduce_emi = original_interest - new_interest_reduce_emi
    
    # Reduce tenure option
    if annual_rate == Decimal("0.00"):
        new_months = int((new_principal / original_emi).quantize(Decimal("1"), rounding=ROUND_UP))
    else:
        monthly_rate = annual_rate / Decimal("1200")
        new_months = math.ceil(
            math.log(original_emi / (original_emi - new_principal * monthly_rate)) / 
            math.log(1 + float(monthly_rate))
        )
    
    new_total_reduce_tenure = original_emi * new_months
    new_interest_reduce_tenure = new_total_reduce_tenure - new_principal
    savings_reduce_tenure = original_interest - new_interest_reduce_tenure
    months_saved = remaining_months - new_months
    
    return {
        "interest_saved_reduce_emi": str(savings_reduce_emi),
        "interest_saved_reduce_tenure": str(savings_reduce_tenure),
        "months_saved_reduce_tenure": months_saved,
        "new_emi_reduce_emi": str(new_emi),
        "new_tenure_reduce_tenure": new_months,
    }


@router.post("/simulations/early-payment")
async def simulate_early_payment(
    simulation_data: dict,
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Simulate early payment scenarios (reduce EMI vs reduce tenure)."""
    from app.services import loan_simulation_service
    from decimal import Decimal
    from datetime import date as dt_date

    account_id = uuid.UUID(simulation_data["account_id"])
    prepayment_amount = Decimal(str(simulation_data["prepayment_amount"]))
    prepayment_date = dt_date.fromisoformat(simulation_data.get("prepayment_date", date.today().isoformat()))

    result = await loan_simulation_service.simulate_early_payment(
        session=db,
        account_id=account_id,
        prepayment_amount=prepayment_amount,
        prepayment_date=prepayment_date,
    )

    return result


@router.post("/simulations/preclosure")
async def simulate_preclosure(
    simulation_data: dict,
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Simulate loan pre-closure and calculate payoff amount."""
    from app.services import loan_simulation_service
    from datetime import date as dt_date

    account_id = uuid.UUID(simulation_data["account_id"])
    closure_date = dt_date.fromisoformat(simulation_data.get("closure_date", date.today().isoformat()))

    result = await loan_simulation_service.simulate_preclosure(
        session=db,
        account_id=account_id,
        closure_date=closure_date,
    )

    return result


@router.post("/simulations/interest-rate-change")
async def simulate_interest_rate_change(
    simulation_data: dict,
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Simulate impact of interest rate change."""
    from app.services import loan_simulation_service
    from decimal import Decimal
    from datetime import date as dt_date

    account_id = uuid.UUID(simulation_data["account_id"])
    new_interest_rate = Decimal(str(simulation_data["new_interest_rate"]))
    effective_from_date = dt_date.fromisoformat(simulation_data.get("effective_from_date", date.today().isoformat()))

    result = await loan_simulation_service.simulate_interest_rate_change(
        session=db,
        account_id=account_id,
        new_interest_rate=new_interest_rate,
        effective_from_date=effective_from_date,
    )

    return result


async def _require_loan_account(
    db: AsyncSession, account_id: uuid.UUID, workspace_id: uuid.UUID
) -> Account:
    result = await db.execute(
        select(Account).where(Account.id == account_id, Account.workspace_id == workspace_id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.post("/simulations/combined")
async def simulate_combined_scenarios(
    body: CombinedSimulationRequest,
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    """Combined scenario ground: prepay + recurring + rate changes (+ EMI holiday) interplay."""
    await _require_loan_account(db, body.account_id, workspace.id)
    try:
        return await loan_combined_simulation_service.simulate_combined(
            session=db,
            account_id=body.account_id,
            events=[e.model_dump(mode="json") for e in body.events],
            strategy=body.strategy,
            as_of_date=body.as_of_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/commitments", response_model=list[CommitmentRead])
async def list_loan_commitments(
    account_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_workspace),
):
    return await loan_commitment_service.list_commitments(
        db, workspace.id, account_id=account_id
    )


@router.post("/commitments", response_model=CommitmentRead)
async def create_loan_commitment(
    body: CommitmentCreate,
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_writable_workspace),
):
    await _require_loan_account(db, body.account_id, workspace.id)
    try:
        return await loan_commitment_service.commit_plan_action(
            db,
            workspace_id=workspace.id,
            user_id=workspace.user_id,
            account_id=body.account_id,
            kind=body.kind,
            amount=body.amount,
            start_date=body.start_date,
            end_date=body.end_date,
            day_of_month=body.day_of_month,
            funding_account_id=body.funding_account_id,
            category_id=body.category_id,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/commitments/{commitment_id}/cancel", response_model=CommitmentRead)
async def cancel_loan_commitment(
    commitment_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_session),
    workspace: WorkspaceContext = Depends(current_writable_workspace),
):
    try:
        return await loan_commitment_service.cancel_commitment(
            db, commitment_id, workspace.id
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
