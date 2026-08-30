import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.transaction import Transaction


class LoanPrepayment(Base):
    __tablename__ = "loan_prepayments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )
    prepayment_amount: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=2))
    prepayment_date: Mapped[date] = mapped_column(Date, index=True)
    recalculation_method: Mapped[str] = mapped_column(
        String(20)
    )  # reduce_emi, reduce_tenure
    schedule_version_before: Mapped[int] = mapped_column(Integer)
    schedule_version_after: Mapped[int] = mapped_column(Integer)
    tenure_change_months: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    emi_change_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=15, scale=2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    account: Mapped["Account"] = relationship(back_populates="loan_prepayments")
    transaction: Mapped[Optional["Transaction"]] = relationship()
