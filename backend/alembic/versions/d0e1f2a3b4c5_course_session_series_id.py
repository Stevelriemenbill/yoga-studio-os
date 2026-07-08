"""course session series_id

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-07-08 21:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

import app.db.types

revision: str = 'd0e1f2a3b4c5'
down_revision: str | None = 'c9d0e1f2a3b4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'course_sessions',
        sa.Column('series_id', app.db.types.GUID(), nullable=True),
    )
    op.create_index(
        'ix_course_sessions_series_id',
        'course_sessions',
        ['series_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_course_sessions_series_id', table_name='course_sessions')
    op.drop_column('course_sessions', 'series_id')
