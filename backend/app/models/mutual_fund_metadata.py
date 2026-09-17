import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MutualFundMetadata(Base):
    """Reference data for Indian mutual fund schemes."""
    
    __tablename__ = "mutual_fund_metadata"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    isin: Mapped[str] = mapped_column(String(12), unique=True, nullable=False, index=True)
    scheme_name: Mapped[str] = mapped_column(String(200), nullable=False)
    amc_name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sub_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    plan_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    expense_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=5, scale=4), nullable=True)
    aum: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=18, scale=2), nullable=True)
    launch_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
