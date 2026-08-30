import uuid
from datetime import date
from dateutil.relativedelta import relativedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.loan_schedule import LoanAmortizationSchedule


def calculate_emi(principal: Decimal, annual_rate: Decimal, tenure_months: int) -> Decimal:
    """Calculate EMI using reducing balance method.

    Formula: EMI = P × r × (1 + r)^n / ((1 + r)^n - 1)
    Where:
        P = Principal amount
        r = Monthly interest rate (annual_rate / 12 / 100)
        n = Tenure in months
    """
    if annual_rate == Decimal("0.00"):
        # Zero interest: EMI = principal / tenure
        return (principal / Decimal(tenure_months)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    monthly_rate = annual_rate / Decimal("1200")  # annual_rate / 12 / 100
    numerator = principal * monthly_rate * ((Decimal("1") + monthly_rate) ** tenure_months)
    denominator = ((Decimal("1") + monthly_rate) ** tenure_months) - Decimal("1")
    emi = (numerator / denominator).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return emi


async def generate_amortization_schedule(
    session: AsyncSession, account_id: uuid.UUID, version: int = 1
) -> list[LoanAmortizationSchedule]:
    """Generate full amortization schedule for a loan account.

    Uses reducing balance method to calculate principal and interest
    components for each EMI.
    """
    # Fetch loan account
    result = await session.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one()

    if account.type != "loan":
        raise ValueError(f"Account {account_id} is not a loan account")

    if not all([account.original_principal, account.interest_rate, account.tenure_months, account.disbursed_on]):
        raise ValueError(f"Account {account_id} missing required loan fields")

    principal = account.original_principal
    annual_rate = account.interest_rate
    tenure_months = account.tenure_months
    disbursed_on = account.disbursed_on
    emi_day = account.emi_day or disbursed_on.day

    # Calculate EMI if not provided
    emi_amount = account.emi_amount
    if not emi_amount:
        emi_amount = calculate_emi(principal, annual_rate, tenure_months)

    monthly_rate = annual_rate / Decimal("1200") if annual_rate > 0 else Decimal("0")
    remaining_principal = principal
    entries = []

    for i in range(1, tenure_months + 1):
        # Calculate due date: disbursed_on + i months, adjusted to emi_day
        due_date = disbursed_on + relativedelta(months=i)
        # Adjust to emi_day, handling month-end edge cases
        try:
            due_date = due_date.replace(day=emi_day)
        except ValueError:
            # emi_day exceeds days in month (e.g., 31 in Feb), use last day
            due_date = due_date + relativedelta(day=31)

        opening_balance = remaining_principal
        interest_component = (opening_balance * monthly_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        principal_component = emi_amount - interest_component

        # Last EMI: principal_component = remaining balance (avoid rounding residual)
        if i == tenure_months:
            principal_component = opening_balance
            interest_component = emi_amount - principal_component

        closing_balance = opening_balance - principal_component
        remaining_principal = closing_balance

        entry = LoanAmortizationSchedule(
            id=uuid.uuid4(),
            account_id=account_id,
            workspace_id=account.workspace_id,
            schedule_version=version,
            emi_number=i,
            due_date=due_date,
            principal_component=principal_component,
            interest_component=interest_component,
            emi_amount=emi_amount,
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            payment_status="scheduled",
        )
        entries.append(entry)
        session.add(entry)

    await session.commit()
    return entries


async def get_schedule(
    session: AsyncSession,
    account_id: uuid.UUID,
    version: Optional[int] = None,
    filters: Optional[dict] = None,
) -> list[LoanAmortizationSchedule]:
    """Retrieve amortization schedule with optional filters."""
    # Fetch current version if not specified
    if version is None:
        result = await session.execute(select(Account.current_schedule_version).where(Account.id == account_id))
        version = result.scalar_one()

    query = select(LoanAmortizationSchedule).where(
        LoanAmortizationSchedule.account_id == account_id, LoanAmortizationSchedule.schedule_version == version
    )

    if filters:
        if "payment_status" in filters:
            query = query.where(LoanAmortizationSchedule.payment_status == filters["payment_status"])
        if "from_date" in filters:
            query = query.where(LoanAmortizationSchedule.due_date >= filters["from_date"])
        if "to_date" in filters:
            query = query.where(LoanAmortizationSchedule.due_date <= filters["to_date"])

    query = query.order_by(LoanAmortizationSchedule.emi_number)

    result = await session.execute(query)
    return list(result.scalars().all())
