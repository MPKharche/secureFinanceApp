"""loan transaction linking

Revision ID: 083
Revises: 082
Create Date: 2026-09-16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '083'
down_revision = '082'
branch_labels = None
depends_on = None


def upgrade():
    # Add linked_transaction_ids column for multiple transaction support
    op.add_column('loan_amortization_schedules',
        sa.Column('linked_transaction_ids', sa.String(length=500), nullable=True)
    )
    
    # Migrate existing linked_transaction_id to new field
    op.execute("""
        UPDATE loan_amortization_schedules
        SET linked_transaction_ids = linked_transaction_id::text
        WHERE linked_transaction_id IS NOT NULL
    """)


def downgrade():
    op.drop_column('loan_amortization_schedules', 'linked_transaction_ids')
