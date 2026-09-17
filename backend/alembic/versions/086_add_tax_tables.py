"""add tax tables and user dob

Revision ID: 086_add_tax_tables
Revises: 085_budget_spreadsheet_schema
Create Date: 2026-09-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '086_add_tax_tables'
down_revision = '085_budget_spreadsheet_schema'
branch_labels = None
depends_on = None


def upgrade():
    # Add date_of_birth to users
    op.add_column('users', sa.Column('date_of_birth', sa.Date(), nullable=True))
    
    # Create tax_income_sources
    op.create_table(
        'tax_income_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('financial_year', sa.String(10), nullable=False),
        sa.Column('salary_annual', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('rental_income', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('interest_income', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('dividend_income', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('capital_gains_short_term', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('capital_gains_long_term', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('business_income', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('other_income', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('basic_salary', sa.DECIMAL(12, 2), nullable=True),
        sa.Column('hra_received', sa.DECIMAL(12, 2), nullable=True),
        sa.Column('special_allowance', sa.DECIMAL(12, 2), nullable=True),
        sa.Column('salary_auto_detected', sa.Boolean(), server_default='false'),
        sa.Column('interest_auto_detected', sa.Boolean(), server_default='false'),
        sa.Column('last_auto_detection_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'financial_year', name='uq_tax_income_user_fy')
    )
    op.create_index('idx_tax_income_user_fy', 'tax_income_sources', ['user_id', 'financial_year'])
    
    # Create tax_deductions
    op.create_table(
        'tax_deductions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('financial_year', sa.String(10), nullable=False),
        sa.Column('epf_employee', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('ppf', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('elss', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('lic_premium', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('nsc', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('tuition_fees', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('principal_repayment_home_loan', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('other_80c', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('nps_additional', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('health_insurance_self', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('health_insurance_parents', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('parents_are_senior_citizens', sa.Boolean(), server_default='false'),
        sa.Column('preventive_checkup', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('education_loan_interest', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('donations_100_percent', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('donations_50_percent', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('savings_interest_claimed', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('home_loan_interest', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('property_is_self_occupied', sa.Boolean(), server_default='true'),
        sa.Column('rent_paid_annual', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('city', sa.String(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'financial_year', name='uq_tax_deductions_user_fy')
    )
    op.create_index('idx_tax_deductions_user_fy', 'tax_deductions', ['user_id', 'financial_year'])
    
    # Create tax_projections
    op.create_table(
        'tax_projections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('financial_year', sa.String(10), nullable=False),
        sa.Column('old_regime_gross_income', sa.DECIMAL(12, 2), nullable=True),
        sa.Column('old_regime_total_deductions', sa.DECIMAL(12, 2), nullable=True),
        sa.Column('old_regime_taxable_income', sa.DECIMAL(12, 2), nullable=True),
        sa.Column('old_regime_tax_liability', sa.DECIMAL(12, 2), nullable=True),
        sa.Column('old_regime_cess', sa.DECIMAL(12, 2), nullable=True),
        sa.Column('old_regime_total_tax', sa.DECIMAL(12, 2), nullable=True),
        sa.Column('new_regime_gross_income', sa.DECIMAL(12, 2), nullable=True),
        sa.Column('new_regime_taxable_income', sa.DECIMAL(12, 2), nullable=True),
        sa.Column('new_regime_tax_liability', sa.DECIMAL(12, 2), nullable=True),
        sa.Column('new_regime_cess', sa.DECIMAL(12, 2), nullable=True),
        sa.Column('new_regime_total_tax', sa.DECIMAL(12, 2), nullable=True),
        sa.Column('recommended_regime', sa.String(10), nullable=True),
        sa.Column('savings_with_recommendation', sa.DECIMAL(12, 2), nullable=True),
        sa.Column('tds_deducted', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('advance_tax_paid', sa.DECIMAL(12, 2), server_default='0'),
        sa.Column('tax_due_or_refund', sa.DECIMAL(12, 2), nullable=True),
        sa.Column('calculated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('is_stale', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'financial_year', name='uq_tax_projections_user_fy')
    )
    op.create_index('idx_tax_projections_user_fy', 'tax_projections', ['user_id', 'financial_year'])
    op.create_index('idx_tax_projections_stale', 'tax_projections', ['user_id', 'is_stale'], 
                    postgresql_where=sa.text('is_stale = true'))
    
    # Create tax_events_log
    op.create_table(
        'tax_events_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('financial_year', sa.String(10), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('event_data', postgresql.JSONB, nullable=True),
        sa.Column('triggered_recalculation', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('idx_tax_events_user', 'tax_events_log', ['user_id', sa.text('created_at DESC')])


def downgrade():
    op.drop_index('idx_tax_events_user', 'tax_events_log')
    op.drop_table('tax_events_log')
    op.drop_index('idx_tax_projections_stale', 'tax_projections')
    op.drop_index('idx_tax_projections_user_fy', 'tax_projections')
    op.drop_table('tax_projections')
    op.drop_index('idx_tax_deductions_user_fy', 'tax_deductions')
    op.drop_table('tax_deductions')
    op.drop_index('idx_tax_income_user_fy', 'tax_income_sources')
    op.drop_table('tax_income_sources')
    op.drop_column('users', 'date_of_birth')
