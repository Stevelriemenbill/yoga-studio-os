"""join_requests table

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-07-08 19:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

import app.db.types

revision: str = 'b8c9d0e1f2a3'
down_revision: str | None = 'a7b8c9d0e1f2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'join_requests',
        sa.Column('first_name', sa.String(length=120), nullable=False),
        sa.Column('last_name', sa.String(length=120), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('member_id', app.db.types.GUID(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', app.db.types.GUID(), nullable=False),
        sa.Column('tenant_id', app.db.types.GUID(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['member_id'], ['members.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_join_requests_email'), 'join_requests', ['email'], unique=False
    )
    op.create_index(
        op.f('ix_join_requests_tenant_id'),
        'join_requests',
        ['tenant_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_join_requests_tenant_id'), table_name='join_requests')
    op.drop_index(op.f('ix_join_requests_email'), table_name='join_requests')
    op.drop_table('join_requests')
