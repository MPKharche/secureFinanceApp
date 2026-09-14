"""loan prepayment penalty fee ledger link

Revision ID: 082
Revises: 081
Create Date: 2026-09-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "082"
down_revision: Union[str, None] = "081"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "loan_prepayments",
        sa.Column("penalty_amount", sa.Numeric(precision=15, scale=2), nullable=True),
    )
    op.add_column(
        "loan_prepayments",
        sa.Column("penalty_rate", sa.Numeric(precision=8, scale=4), nullable=True),
    )
    op.add_column(
        "loan_prepayments",
        sa.Column("penalty_basis", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "loan_prepayments",
        sa.Column("penalty_transaction_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_loan_prepayments_penalty_transaction_id",
        "loan_prepayments",
        "transactions",
        ["penalty_transaction_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_loan_prepayments_penalty_transaction_id",
        "loan_prepayments",
        type_="foreignkey",
    )
    op.drop_column("loan_prepayments", "penalty_transaction_id")
    op.drop_column("loan_prepayments", "penalty_basis")
    op.drop_column("loan_prepayments", "penalty_rate")
    op.drop_column("loan_prepayments", "penalty_amount")
