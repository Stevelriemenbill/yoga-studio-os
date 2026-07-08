"""student notes: private teacher notes for guiding students

Revision ID: a1b2c3d4e5f6
Revises: 9f9cf699d2c8
Create Date: 2026-07-08 10:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Text

import app.db.types

revision: str = 'a1b2c3d4e5f6'
down_revision: str | None = '9f9cf699d2c8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'student_notes',
        sa.Column('member_id', app.db.types.GUID(), nullable=False),
        sa.Column('author_id', app.db.types.GUID(), nullable=True),
        sa.Column('body', Text(), nullable=False),
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
        sa.ForeignKeyConstraint(['member_id'], ['members.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_student_notes_member_id'), 'student_notes', ['member_id'], unique=False
    )
    op.create_index(
        op.f('ix_student_notes_tenant_id'), 'student_notes', ['tenant_id'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_student_notes_tenant_id'), table_name='student_notes')
    op.drop_index(op.f('ix_student_notes_member_id'), table_name='student_notes')
    op.drop_table('student_notes')
