"""course/session location + online, registration_info, course attachments

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-08 16:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

import app.db.types

revision: str = 'f6a7b8c9d0e1'
down_revision: str | None = 'e5f6a7b8c9d0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Course: default location / online / registration info
    op.add_column('courses', sa.Column('location', sa.String(length=255), nullable=True))
    op.add_column(
        'courses',
        sa.Column(
            'is_online',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column('courses', sa.Column('online_url', sa.String(length=500), nullable=True))
    op.add_column('courses', sa.Column('registration_info', sa.Text(), nullable=True))

    # Session: per-occurrence overrides (nullable -> inherit from course)
    op.add_column(
        'course_sessions', sa.Column('location', sa.String(length=255), nullable=True)
    )
    op.add_column(
        'course_sessions', sa.Column('is_online', sa.Boolean(), nullable=True)
    )
    op.add_column(
        'course_sessions', sa.Column('online_url', sa.String(length=500), nullable=True)
    )

    # Course attachments
    op.create_table(
        'course_attachments',
        sa.Column('course_id', app.db.types.GUID(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('stored_name', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=120), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_course_attachments_course_id'),
        'course_attachments',
        ['course_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_course_attachments_tenant_id'),
        'course_attachments',
        ['tenant_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_course_attachments_tenant_id'), table_name='course_attachments'
    )
    op.drop_index(
        op.f('ix_course_attachments_course_id'), table_name='course_attachments'
    )
    op.drop_table('course_attachments')

    op.drop_column('course_sessions', 'online_url')
    op.drop_column('course_sessions', 'is_online')
    op.drop_column('course_sessions', 'location')

    op.drop_column('courses', 'registration_info')
    op.drop_column('courses', 'online_url')
    op.drop_column('courses', 'is_online')
    op.drop_column('courses', 'location')
