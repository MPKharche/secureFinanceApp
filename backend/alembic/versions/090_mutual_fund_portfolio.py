"""mutual_fund_portfolio

Revision ID: 090_mutual_fund_portfolio
Revises: 089
Create Date: 2026-09-17 16:30:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '090_mutual_fund_portfolio'
down_revision = '088_add_goal_templates_fields'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('mutual_fund_metadata',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('isin', sa.String(12), nullable=False),
        sa.Column('scheme_name', sa.String(200), nullable=False),
        sa.Column('amc_name', sa.String(100), nullable=False),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('sub_category', sa.String(50), nullable=True),
        sa.Column('plan_type', sa.String(20), nullable=True),
        sa.Column('expense_ratio', sa.Numeric(5, 4), nullable=True),
        sa.Column('aum', sa.Numeric(18, 2), nullable=True),
        sa.Column('launch_date', sa.Date(), nullable=True),
        sa.Column('last_updated', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_mutual_fund_metadata_isin', 'mutual_fund_metadata', ['isin'], unique=True)
    
    op.create_table('mutual_fund_sips',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('frequency', sa.Enum('monthly', 'quarterly', 'weekly', name='sip_frequency'), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('status', sa.Enum('active', 'paused', 'completed', name='sip_status'), nullable=False),
        sa.Column('next_due_date', sa.Date(), nullable=True),
        sa.Column('auto_debit', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('bank_mandate_id', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_mutual_fund_sips_workspace_id', 'mutual_fund_sips', ['workspace_id'])
    op.create_index('ix_mutual_fund_sips_asset_id', 'mutual_fund_sips', ['asset_id'])
    
    op.create_table('goal_assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('goal_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['goal_id'], ['goals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_goal_assets_goal_id', 'goal_assets', ['goal_id'])
    op.create_index('ix_goal_assets_asset_id', 'goal_assets', ['asset_id'])
    
    op.add_column('assets', sa.Column('folio_number', sa.String(50), nullable=True))
    op.add_column('assets', sa.Column('amc_name', sa.String(100), nullable=True))
    op.add_column('assets', sa.Column('plan_type', sa.String(20), nullable=True))

def downgrade():
    op.drop_column('assets', 'plan_type')
    op.drop_column('assets', 'amc_name')
    op.drop_column('assets', 'folio_number')
    op.drop_table('goal_assets')
    op.drop_table('mutual_fund_sips')
    op.drop_table('mutual_fund_metadata')
