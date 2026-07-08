"""tenant theme: studio-wide appearance (accent preset + colour mode)

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-07-08 12:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = 'c3d4e5f6a7b8'
down_revision: str | None = 'a1b2c3d4e5f6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'tenants',
        sa.Column(
            'theme_preset',
            sa.String(length=32),
            nullable=False,
            server_default='emerald',
        ),
    )
    op.add_column(
        'tenants',
        sa.Column(
            'theme_mode',
            sa.String(length=16),
            nullable=False,
            server_default='light',
        ),
    )


def downgrade() -> None:
    op.drop_column('tenants', 'theme_mode')
    op.drop_column('tenants', 'theme_preset')
