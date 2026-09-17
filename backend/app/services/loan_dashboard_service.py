"""Loan dashboard service for EMI dashboard."""
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
import uuid

from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.loan_schedule import LoanSchedule
from app.services.loan_analytics_service import LoanAnalyticsService


async def get_dashboard_summary(
    session: AsyncSession,
    workspace_id: uuid.UUID,
) -> dict:
    """
    Get dashboard summary with KPIs.
    
    Returns:
        - total_monthly_emi: Sum of all active loan EMIs
        - total_outstanding: Sum of all outstanding principal
        - principal_paid_ytd: Principal paid year-to-date
        - interest_paid_ytd: Interest paid year-to-date
        - active_loan_count: Number of active loans
        - debt_free_date: Estimated debt-free date
        - months_to_debt_free: Months until debt-free
    """
    analytics_service = LoanAnalyticsService(session)
    
    # Get all active loans for workspace
    from app.models.loan_schedule import LoanSchedule
    from app.models.account import Account
    
    # Get active loans
    loans_query = select(Account).where(
        and_(
            Account.workspace_id == workspace_id,
            Account.account_type == "loan",
            Account.is_closed == False,
        )
    )
    result = await session.execute(loans_query)
    active_loans = result.scalars().all()
    
    if not active_loans:
        return {
            "total_monthly_emi": Decimal("0"),
            "total_outstanding": Decimal("0"),
            "principal_paid_ytd": Decimal("0"),
            "interest_paid_ytd": Decimal("0"),
            "active_loan_count": 0,
            "debt_free_date": None,
            "months_to_debt_free": 0,
        }
    
    total_monthly_emi = Decimal("0")
    total_outstanding = Decimal("0")
    principal_paid_ytd = Decimal("0")
    interest_paid_ytd = Decimal("0")
    latest_debt_free_date = None
    
    current_year = date.today().year
    ytd_start = date(current_year, 1, 1)
    
    for loan in active_loans:
        # Get loan summary
        summary = await analytics_service.get_loan_summary(loan.id)
        
        total_monthly_emi += Decimal(str(summary.get("emi_amount", 0)))
        total_outstanding += Decimal(str(summary.get("outstanding_principal", 0)))
        
        # Get YTD payments
        ytd_query = select(
            func.sum(LoanSchedule.principal_component),
            func.sum(LoanSchedule.interest_component),
        ).where(
            and_(
                LoanSchedule.loan_id == loan.id,
                LoanSchedule.payment_status == "paid",
                LoanSchedule.due_date >= ytd_start,
            )
        )
        ytd_result = await session.execute(ytd_query)
        ytd_principal, ytd_interest = ytd_result.one()
        
        principal_paid_ytd += Decimal(str(ytd_principal or 0))
        interest_paid_ytd += Decimal(str(ytd_interest or 0))
        
        # Get last unpaid schedule entry for debt-free date
        last_entry_query = select(LoanSchedule).where(
            and_(
                LoanSchedule.loan_id == loan.id,
                LoanSchedule.payment_status == "unpaid",
            )
        ).order_by(LoanSchedule.due_date.desc()).limit(1)
        last_result = await session.execute(last_entry_query)
        last_entry = last_result.scalar_one_or_none()
        
        if last_entry and (latest_debt_free_date is None or last_entry.due_date > latest_debt_free_date):
            latest_debt_free_date = last_entry.due_date
    
    months_to_debt_free = 0
    if latest_debt_free_date:
        months_to_debt_free = (latest_debt_free_date.year - date.today().year) * 12 + (
            latest_debt_free_date.month - date.today().month
        )
    
    return {
        "total_monthly_emi": total_monthly_emi,
        "total_outstanding": total_outstanding,
        "principal_paid_ytd": principal_paid_ytd,
        "interest_paid_ytd": interest_paid_ytd,
        "active_loan_count": len(active_loans),
        "debt_free_date": latest_debt_free_date,
        "months_to_debt_free": max(0, months_to_debt_free),
    }


async def get_upcoming_payments(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    days: int = 30,
) -> list[dict]:
    """
    Get upcoming EMI payments for next N days.
    
    Returns list of upcoming payment schedule entries.
    """
    from app.models.account import Account
    
    today = date.today()
    end_date = today + timedelta(days=days)
    
    # Query upcoming payments
    query = (
        select(LoanSchedule, Account.name)
        .join(Account, LoanSchedule.loan_id == Account.id)
        .where(
            and_(
                Account.workspace_id == workspace_id,
                Account.account_type == "loan",
                LoanSchedule.payment_status == "unpaid",
                LoanSchedule.due_date >= today,
                LoanSchedule.due_date <= end_date,
            )
        )
        .order_by(LoanSchedule.due_date)
    )
    
    result = await session.execute(query)
    rows = result.all()
    
    payments = []
    for schedule_entry, loan_name in rows:
        days_until = (schedule_entry.due_date - today).days
        payments.append({
            "schedule_entry_id": str(schedule_entry.id),
            "loan_id": str(schedule_entry.loan_id),
            "loan_name": loan_name,
            "due_date": schedule_entry.due_date,
            "emi_amount": schedule_entry.emi_amount,
            "principal_component": schedule_entry.principal_component,
            "interest_component": schedule_entry.interest_component,
            "payment_status": schedule_entry.payment_status,
            "days_until_due": days_until,
        })
    
    return payments


async def calculate_debt_health(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    monthly_income: Decimal,
    other_obligations: Decimal = Decimal("0"),
) -> dict:
    """
    Calculate debt health metrics (DTI and FOIR).
    
    DTI (Debt-to-Income): Total monthly debt / Monthly income
    FOIR (Fixed Obligation to Income Ratio): (EMI + other obligations) / Monthly income
    
    Healthy thresholds:
    - DTI < 36%: Good
    - DTI 36-43%: Moderate
    - DTI > 43%: High
    
    - FOIR < 40%: Good
    - FOIR 40-50%: Moderate
    - FOIR > 50%: High
    """
    summary = await get_dashboard_summary(session, workspace_id)
    total_emi = summary["total_monthly_emi"]
    
    if monthly_income <= 0:
        return {
            "dti": None,
            "foir": None,
            "status": "unknown",
            "breakdown": {},
            "thresholds": {},
            "recommendations": ["Please provide valid monthly income"],
        }
    
    dti = float(total_emi / monthly_income)
    foir = float((total_emi + other_obligations) / monthly_income)
    
    # Determine status
    if dti < 0.36 and foir < 0.40:
        status = "good"
        recommendations = ["Your debt levels are healthy. Consider investing surplus income."]
    elif dti < 0.43 and foir < 0.50:
        status = "moderate"
        recommendations = [
            "Your debt levels are moderate. Focus on paying down high-interest loans.",
            "Avoid taking on additional debt until your ratios improve.",
        ]
    else:
        status = "high"
        recommendations = [
            "Your debt levels are high. Prioritize debt repayment.",
            "Consider prepayment strategies to reduce EMI burden.",
            "Avoid new loans or credit until debt is under control.",
        ]
    
    return {
        "dti": dti,
        "foir": foir,
        "status": status,
        "breakdown": {
            "monthly_income": float(monthly_income),
            "total_emi": float(total_emi),
            "other_obligations": float(other_obligations),
            "total_obligations": float(total_emi + other_obligations),
        },
        "thresholds": {
            "dti_good": 0.36,
            "dti_high": 0.43,
            "foir_good": 0.40,
            "foir_high": 0.50,
        },
        "recommendations": recommendations,
    }


async def generate_emi_timeline(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    months: int = 24,
) -> list[dict]:
    """
    Generate month-by-month EMI timeline.
    
    Shows total EMI, principal, interest for each month.
    """
    from app.models.account import Account
    
    today = date.today()
    timeline = []
    
    for month_offset in range(months):
        month_start = date(today.year, today.month, 1) + timedelta(days=30 * month_offset)
        month_end = month_start + timedelta(days=32)
        month_end = date(month_end.year, month_end.month, 1) - timedelta(days=1)
        
        # Query payments for this month
        query = (
            select(
                func.sum(LoanSchedule.emi_amount),
                func.sum(LoanSchedule.principal_component),
                func.sum(LoanSchedule.interest_component),
                func.count(LoanSchedule.id),
            )
            .join(Account, LoanSchedule.loan_id == Account.id)
            .where(
                and_(
                    Account.workspace_id == workspace_id,
                    Account.account_type == "loan",
                    LoanSchedule.due_date >= month_start,
                    LoanSchedule.due_date <= month_end,
                )
            )
        )
        
        result = await session.execute(query)
        total_emi, total_principal, total_interest, payment_count = result.one()
        
        timeline.append({
            "month": month_start.strftime("%Y-%m"),
            "month_label": month_start.strftime("%b %Y"),
            "total_emi": float(total_emi or 0),
            "total_principal": float(total_principal or 0),
            "total_interest": float(total_interest or 0),
            "payment_count": payment_count or 0,
        })
    
    return timeline
