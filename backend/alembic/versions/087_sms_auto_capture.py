"""sms_auto_capture_tables

Revision ID: 087_sms_auto_capture
Revises: 086_add_tax_tables
Create Date: 2026-09-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '087_sms_auto_capture'
down_revision = '086_add_tax_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Create sms_logs table
    op.create_table(
        'sms_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sender', sa.String(50), nullable=False),
        sa.Column('body', sa.Text, nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processed', sa.Boolean, server_default='false', nullable=False),
        sa.Column('processing_status', sa.String(20), server_default='pending', nullable=False),
        sa.Column('parsed_data', postgresql.JSONB, nullable=True),
        sa.Column('confidence', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('transactions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_sms_logs_workspace', 'sms_logs', ['workspace_id'])
    op.create_index('idx_sms_logs_workspace_status', 'sms_logs', ['workspace_id', 'processing_status'])
    op.create_index('idx_sms_logs_user_received', 'sms_logs', ['user_id', 'received_at'])
    op.create_index('idx_sms_logs_sender_body_received', 'sms_logs', ['sender', 'body', 'received_at'])

    # Create merchant_mappings table
    op.create_table(
        'merchant_mappings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('merchant_name_normalized', sa.String(255), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('categories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('transaction_count', sa.Integer, server_default='1', nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('workspace_id', 'merchant_name_normalized', name='uq_merchant_per_workspace')
    )
    op.create_index('idx_merchant_mappings_workspace', 'merchant_mappings', ['workspace_id'])

    # Create sms_review_queue table
    op.create_table(
        'sms_review_queue',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('sms_log_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('sms_logs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('review_type', sa.String(30), nullable=False),
        sa.Column('status', sa.String(20), server_default='pending', nullable=False),
        sa.Column('review_data', postgresql.JSONB, nullable=False),
        sa.Column('resolution_notes', sa.String(500), nullable=True),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_sms_review_queue_workspace', 'sms_review_queue', ['workspace_id'])
    op.create_index('idx_sms_review_queue_workspace_status', 'sms_review_queue', ['workspace_id', 'status'])
    op.create_index('idx_sms_review_queue_user_status', 'sms_review_queue', ['user_id', 'status'])


def downgrade():
    op.drop_index('idx_sms_review_queue_user_status', 'sms_review_queue')
    op.drop_index('idx_sms_review_queue_workspace_status', 'sms_review_queue')
    op.drop_index('idx_sms_review_queue_workspace', 'sms_review_queue')
    op.drop_table('sms_review_queue')
    
    op.drop_index('idx_merchant_mappings_workspace', 'merchant_mappings')
    op.drop_table('merchant_mappings')
    
    op.drop_index('idx_sms_logs_sender_body_received', 'sms_logs')
    op.drop_index('idx_sms_logs_user_received', 'sms_logs')
    op.drop_index('idx_sms_logs_workspace_status', 'sms_logs')
    op.drop_index('idx_sms_logs_workspace', 'sms_logs')
    op.drop_table('sms_logs')
