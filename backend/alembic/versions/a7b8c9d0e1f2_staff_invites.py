"""staff_invites table

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-07-08 18:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

import app.db.types

revision: str = 'a7b8c9d0e1f2'
down_revision: str | None = 'f6a7b8c9d0e1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'staff_invites',
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_id', app.db.types.GUID(), nullable=True),
        sa.Column('invited_by', app.db.types.GUID(), nullable=True),
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
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['invited_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_staff_invites_email'), 'staff_invites', ['email'], unique=False
    )
    op.create_index(
        op.f('ix_staff_invites_tenant_id'),
        'staff_invites',
        ['tenant_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_staff_invites_tenant_id'), table_name='staff_invites')
    op.drop_index(op.f('ix_staff_invites_email'), table_name='staff_invites')
    op.drop_table('staff_invites')
