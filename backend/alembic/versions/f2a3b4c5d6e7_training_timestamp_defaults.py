"""add timestamp defaults to training cohort tables

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-07-08 23:30:00.000000

The training_programs/cohorts/enrollments tables were created with NOT NULL
created_at/updated_at columns but no server default, so plain INSERTs (which
rely on the DB default) fail. This backfills the default on existing DBs.
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = 'f2a3b4c5d6e7'
down_revision: str | None = 'e1f2a3b4c5d6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ('training_programs', 'training_cohorts', 'training_enrollments')


def upgrade() -> None:
    for table in _TABLES:
        for col in ('created_at', 'updated_at'):
            op.alter_column(
                table,
                col,
                server_default=sa.text('(CURRENT_TIMESTAMP)'),
            )


def downgrade() -> None:
    for table in _TABLES:
        for col in ('created_at', 'updated_at'):
            op.alter_column(table, col, server_default=None)
