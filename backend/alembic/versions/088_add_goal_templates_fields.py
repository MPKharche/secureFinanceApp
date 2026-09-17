"""add goal templates fields

Revision ID: 088
Revises: 087
Create Date: 2026-09-17 15:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '088'
down_revision = '087'
branch_labels = None
depends_on = None


def upgrade():
    # Add priority and template_type fields to goals table
    op.add_column('goals', sa.Column('priority', sa.Integer(), nullable=True))
    op.add_column('goals', sa.Column('template_type', sa.String(length=50), nullable=True))


def downgrade():
    op.drop_column('goals', 'template_type')
    op.drop_column('goals', 'priority')
