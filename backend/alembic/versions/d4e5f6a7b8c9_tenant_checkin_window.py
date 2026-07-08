"""tenant check-in window: per-studio configurable time window (minutes)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-08 13:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = 'd4e5f6a7b8c9'
down_revision: str | None = 'c3d4e5f6a7b8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'tenants',
        sa.Column(
            'checkin_opens_before',
            sa.Integer(),
            nullable=False,
            server_default='30',
        ),
    )
    op.add_column(
        'tenants',
        sa.Column(
            'checkin_closes_after',
            sa.Integer(),
            nullable=False,
            server_default='15',
        ),
    )
    op.add_column(
        'tenants',
        sa.Column(
            'checkin_late_threshold',
            sa.Integer(),
            nullable=False,
            server_default='5',
        ),
    )


def downgrade() -> None:
    op.drop_column('tenants', 'checkin_late_threshold')
    op.drop_column('tenants', 'checkin_closes_after')
    op.drop_column('tenants', 'checkin_opens_before')
