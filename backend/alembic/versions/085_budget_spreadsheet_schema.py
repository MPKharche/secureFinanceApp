"""budget_spreadsheet_schema

Revision ID: 085_budget_spreadsheet_schema
Revises: 084_mcp_sync_tables
Create Date: 2026-09-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '085_budget_spreadsheet_schema'
down_revision = '084_mcp_sync_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Add columns to categories
    op.add_column('categories', sa.Column('category_type', sa.String(20), server_default='expense', nullable=False))
    op.add_column('categories', sa.Column('enable_rollover', sa.Boolean, server_default='false', nullable=False))
    
    # Add column to goals
    op.add_column('goals', sa.Column('linked_category_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), server_default='{}', nullable=False))
    
    # Create budget_templates table
    op.create_table(
        'budget_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('template_data', postgresql.JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('workspace_id', 'name', name='uq_template_name_per_workspace')
    )
    op.create_index('idx_budget_templates_workspace', 'budget_templates', ['workspace_id'])
    
    # Create budget_scenarios table
    op.create_table(
        'budget_scenarios',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('base_month', sa.Date, nullable=False),
        sa.Column('adjustments', postgresql.JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('workspace_id', 'name', name='uq_scenario_name_per_workspace')
    )
    op.create_index('idx_budget_scenarios_workspace', 'budget_scenarios', ['workspace_id'])
    
    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('metadata', postgresql.JSONB, server_default='{}', nullable=False),
        sa.Column('read', sa.Boolean, server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    )
    op.create_index('idx_notifications_user_unread', 'notifications', ['user_id', 'read', sa.text('created_at DESC')])


def downgrade():
    op.drop_index('idx_notifications_user_unread', 'notifications')
    op.drop_table('notifications')
    op.drop_index('idx_budget_scenarios_workspace', 'budget_scenarios')
    op.drop_table('budget_scenarios')
    op.drop_index('idx_budget_templates_workspace', 'budget_templates')
    op.drop_table('budget_templates')
    op.drop_column('goals', 'linked_category_ids')
    op.drop_column('categories', 'enable_rollover')
    op.drop_column('categories', 'category_type')
