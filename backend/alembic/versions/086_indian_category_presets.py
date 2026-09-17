"""add indian category presets

Revision ID: 086
Revises: 085
Create Date: 2026-09-17
"""
from typing import Sequence, Union

from alembic import op

revision: str = "086"
down_revision: Union[str, None] = "085"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No schema changes needed - Indian categories will be added via
    # updated DEFAULT_CATEGORIES_I18N dict in category_service.py
    # This migration exists as a marker for the feature addition
    pass


def downgrade() -> None:
    # Categories are user data - no automatic deletion on downgrade
    pass
