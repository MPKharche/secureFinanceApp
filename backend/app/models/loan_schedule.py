import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.transaction import Transaction


class LoanAmortizationSchedule(Base):
    __tablename__ = "loan_amortization_schedules"
    __table_args__ = (
        UniqueConstraint("account_id", "schedule_version", "emi_number", name="uq_account_version_emi"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    schedule_version: Mapped[int] = mapped_column(Integer, default=1, index=True)
    emi_number: Mapped[int] = mapped_column(Integer)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    principal_component: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=2))
    interest_component: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=2))
    emi_amount: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=2))
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=2))
    closing_balance: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=2))
    payment_status: Mapped[str] = mapped_column(
        String(20), default="scheduled", index=True
    )  # scheduled, paid, partial, missed, skipped
    actual_payment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    actual_amount_paid: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=15, scale=2), nullable=True)
    linked_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    account: Mapped["Account"] = relationship(back_populates="loan_schedules")
    linked_transaction: Mapped[Optional["Transaction"]] = relationship()
