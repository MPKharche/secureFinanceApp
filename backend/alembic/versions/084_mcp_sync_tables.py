"""add mcp sync tables

Revision ID: 084_mcp_sync_tables
Revises: 083
Create Date: 2026-09-16 01:21:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '084_mcp_sync_tables'
down_revision = '083'
branch_labels = None
depends_on = None

def upgrade():
    # Read and execute SQL from migrations directory
    import pathlib
    sql_file = pathlib.Path(__file__).parent.parent.parent.parent / 'mcp-proxy' / 'migrations' / '001_add_sync_tables.sql'
    with open(sql_file) as f:
        op.execute(f.read())

def downgrade():
    op.execute('DROP TABLE IF EXISTS hermes_checkpoints CASCADE')
    op.execute('DROP TABLE IF EXISTS mcp_call_log CASCADE')
    op.execute('DROP TABLE IF EXISTS pending_transactions CASCADE')
