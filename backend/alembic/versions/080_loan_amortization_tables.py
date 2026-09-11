"""loan amortization schedules and prepayments

Revision ID: 080
Revises: 079
Create Date: 2026-08-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "080"
down_revision: Union[str, None] = "078"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to accounts table
    op.add_column(
        "accounts",
        sa.Column("current_schedule_version", sa.Integer(), server_default="1", nullable=False),
    )
    op.add_column("accounts", sa.Column("last_payment_date", sa.Date(), nullable=True))
    op.add_column(
        "accounts",
        sa.Column("total_prepayments", sa.Numeric(precision=15, scale=2), server_default="0.00", nullable=False),
    )

    # Create loan_amortization_schedules table
    op.create_table(
        "loan_amortization_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schedule_version", sa.Integer(), nullable=False),
        sa.Column("emi_number", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("principal_component", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("interest_component", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("emi_amount", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("opening_balance", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("closing_balance", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("payment_status", sa.String(length=20), server_default="scheduled", nullable=False),
        sa.Column("actual_payment_date", sa.Date(), nullable=True),
        sa.Column("actual_amount_paid", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("linked_transaction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["linked_transaction_id"], ["transactions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "schedule_version", "emi_number", name="uq_account_version_emi"),
    )
    op.create_index(
        "ix_loan_amortization_schedules_account_id", "loan_amortization_schedules", ["account_id"], unique=False
    )
    op.create_index(
        "ix_loan_amortization_schedules_due_date", "loan_amortization_schedules", ["due_date"], unique=False
    )
    op.create_index(
        "ix_loan_amortization_schedules_payment_status",
        "loan_amortization_schedules",
        ["payment_status"],
        unique=False,
    )
    op.create_index(
        "ix_loan_amortization_schedules_schedule_version",
        "loan_amortization_schedules",
        ["schedule_version"],
        unique=False,
    )
    op.create_index(
        "ix_loan_amortization_schedules_workspace_id", "loan_amortization_schedules", ["workspace_id"], unique=False
    )

    # Create loan_prepayments table
    op.create_table(
        "loan_prepayments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("prepayment_amount", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("prepayment_date", sa.Date(), nullable=False),
        sa.Column("recalculation_method", sa.String(length=20), nullable=False),
        sa.Column("schedule_version_before", sa.Integer(), nullable=False),
        sa.Column("schedule_version_after", sa.Integer(), nullable=False),
        sa.Column("tenure_change_months", sa.Integer(), nullable=True),
        sa.Column("emi_change_amount", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_loan_prepayments_account_id", "loan_prepayments", ["account_id"], unique=False)
    op.create_index("ix_loan_prepayments_prepayment_date", "loan_prepayments", ["prepayment_date"], unique=False)
    op.create_index("ix_loan_prepayments_workspace_id", "loan_prepayments", ["workspace_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_loan_prepayments_workspace_id", table_name="loan_prepayments")
    op.drop_index("ix_loan_prepayments_prepayment_date", table_name="loan_prepayments")
    op.drop_index("ix_loan_prepayments_account_id", table_name="loan_prepayments")
    op.drop_table("loan_prepayments")

    op.drop_index("ix_loan_amortization_schedules_workspace_id", table_name="loan_amortization_schedules")
    op.drop_index("ix_loan_amortization_schedules_schedule_version", table_name="loan_amortization_schedules")
    op.drop_index("ix_loan_amortization_schedules_payment_status", table_name="loan_amortization_schedules")
    op.drop_index("ix_loan_amortization_schedules_due_date", table_name="loan_amortization_schedules")
    op.drop_index("ix_loan_amortization_schedules_account_id", table_name="loan_amortization_schedules")
    op.drop_table("loan_amortization_schedules")

    op.drop_column("accounts", "total_prepayments")
    op.drop_column("accounts", "last_payment_date")
    op.drop_column("accounts", "current_schedule_version")
