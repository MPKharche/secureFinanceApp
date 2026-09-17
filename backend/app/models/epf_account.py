import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class EPFAccount(Base):
    """Employee Provident Fund account tracking."""
    __tablename__ = "epf_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    uan_number: Mapped[Optional[str]] = mapped_column(String(12), nullable=True, index=True)
    epfo_member_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    account_name: Mapped[str] = mapped_column(String(255))
    
    employee_balance: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=2), default=Decimal("0.00"))
    employer_balance: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=2), default=Decimal("0.00"))
    
    current_interest_rate: Mapped[Decimal] = mapped_column(Numeric(precision=5, scale=2), default=Decimal("8.25"))
    
    current_employer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    monthly_basic_salary: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=15, scale=2), nullable=True)
    date_of_joining: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expected_retirement_age: Mapped[int] = mapped_column(Integer, default=58)
    
    is_active: Mapped[bool] = mapped_column(default=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    
    contributions: Mapped[list["EPFContribution"]] = relationship(back_populates="epf_account", cascade="all, delete-orphan")
    withdrawals: Mapped[list["EPFWithdrawal"]] = relationship(back_populates="epf_account", cascade="all, delete-orphan")


class EPFContribution(Base):
    """Monthly EPF contribution record."""
    __tablename__ = "epf_contributions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    epf_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("epf_accounts.id", ondelete="CASCADE"), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    
    contribution_month: Mapped[date] = mapped_column(Date, index=True)
    
    employee_contribution: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=2))
    employer_contribution: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=2))
    
    interest_earned: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=2), default=Decimal("0.00"))
    
    employee_balance: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=2))
    employer_balance: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=2))
    
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    epf_account: Mapped["EPFAccount"] = relationship(back_populates="contributions")


class EPFWithdrawal(Base):
    """EPF withdrawal or advance record."""
    __tablename__ = "epf_withdrawals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    epf_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("epf_accounts.id", ondelete="CASCADE"), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    
    withdrawal_date: Mapped[date] = mapped_column(Date, index=True)
    withdrawal_type: Mapped[str] = mapped_column(String(50))
    
    form_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    employee_amount: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=2))
    employer_amount: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=2))
    
    purpose: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    is_taxable: Mapped[bool] = mapped_column(default=False)
    tax_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=15, scale=2), nullable=True)
    
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    epf_account: Mapped["EPFAccount"] = relationship(back_populates="withdrawals")
