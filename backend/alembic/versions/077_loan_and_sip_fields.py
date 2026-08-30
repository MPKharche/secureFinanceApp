"""loan product fields on accounts; SIP fields on assets

Revision ID: 077
Revises: 076
Create Date: 2026-08-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "077"
down_revision: Union[str, None] = "076"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("loan_kind", sa.String(length=50), nullable=True))
    op.add_column(
        "accounts",
        sa.Column("original_principal", sa.Numeric(precision=15, scale=2), nullable=True),
    )
    op.add_column(
        "accounts",
        sa.Column("interest_rate", sa.Numeric(precision=8, scale=4), nullable=True),
    )
    op.add_column("accounts", sa.Column("tenure_months", sa.Integer(), nullable=True))
    op.add_column(
        "accounts",
        sa.Column("emi_amount", sa.Numeric(precision=15, scale=2), nullable=True),
    )
    op.add_column("accounts", sa.Column("disbursed_on", sa.Date(), nullable=True))
    op.add_column("accounts", sa.Column("emi_day", sa.SmallInteger(), nullable=True))

    op.add_column(
        "assets",
        sa.Column("sip_amount", sa.Numeric(precision=15, scale=2), nullable=True),
    )
    op.add_column("assets", sa.Column("sip_day", sa.SmallInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("assets", "sip_day")
    op.drop_column("assets", "sip_amount")
    op.drop_column("accounts", "emi_day")
    op.drop_column("accounts", "disbursed_on")
    op.drop_column("accounts", "emi_amount")
    op.drop_column("accounts", "tenure_months")
    op.drop_column("accounts", "interest_rate")
    op.drop_column("accounts", "original_principal")
    op.drop_column("accounts", "loan_kind")
