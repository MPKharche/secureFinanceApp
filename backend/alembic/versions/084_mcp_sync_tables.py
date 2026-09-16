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
    # MCP sync tables - execute separately for asyncpg compatibility
    op.execute("""
        CREATE TABLE IF NOT EXISTS hermes_checkpoints (
            id SERIAL PRIMARY KEY,
            key VARCHAR(255) UNIQUE NOT NULL,
            value TEXT,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    op.execute("""
        CREATE TABLE IF NOT EXISTS mcp_call_log (
            id SERIAL PRIMARY KEY,
            tool_name VARCHAR(255),
            args JSONB,
            result JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    op.execute("""
        CREATE TABLE IF NOT EXISTS pending_transactions (
            id SERIAL PRIMARY KEY,
            transaction_data JSONB,
            status VARCHAR(50),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

def downgrade():
    op.execute('DROP TABLE IF EXISTS hermes_checkpoints CASCADE')
    op.execute('DROP TABLE IF EXISTS mcp_call_log CASCADE')
    op.execute('DROP TABLE IF EXISTS pending_transactions CASCADE')
