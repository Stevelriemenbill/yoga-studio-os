"""training programs, cohorts, enrollments

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-07-08 22:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

import app.db.types

revision: str = 'e1f2a3b4c5d6'
down_revision: str | None = 'd0e1f2a3b4c5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'training_programs',
        sa.Column('id', app.db.types.GUID(), nullable=False),
        sa.Column('tenant_id', app.db.types.GUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('duration_months', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_training_programs_tenant_id', 'training_programs', ['tenant_id']
    )

    op.create_table(
        'training_cohorts',
        sa.Column('id', app.db.types.GUID(), nullable=False),
        sa.Column('tenant_id', app.db.types.GUID(), nullable=False),
        sa.Column('program_id', app.db.types.GUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['program_id'], ['training_programs.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_training_cohorts_tenant_id', 'training_cohorts', ['tenant_id']
    )
    op.create_index(
        'ix_training_cohorts_program_id', 'training_cohorts', ['program_id']
    )

    op.create_table(
        'training_enrollments',
        sa.Column('id', app.db.types.GUID(), nullable=False),
        sa.Column('tenant_id', app.db.types.GUID(), nullable=False),
        sa.Column('cohort_id', app.db.types.GUID(), nullable=False),
        sa.Column('member_id', app.db.types.GUID(), nullable=False),
        sa.Column('enrolled_on', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['cohort_id'], ['training_cohorts.id'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['member_id'], ['members.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'cohort_id', 'member_id', name='uq_enrollment_cohort_member'
        ),
    )
    op.create_index(
        'ix_training_enrollments_tenant_id', 'training_enrollments', ['tenant_id']
    )
    op.create_index(
        'ix_training_enrollments_cohort_id', 'training_enrollments', ['cohort_id']
    )
    op.create_index(
        'ix_training_enrollments_member_id', 'training_enrollments', ['member_id']
    )

    op.add_column(
        'training_requirements',
        sa.Column('program_id', app.db.types.GUID(), nullable=True),
    )
    op.create_index(
        'ix_training_requirements_program_id',
        'training_requirements',
        ['program_id'],
    )
    op.create_foreign_key(
        'fk_training_requirements_program_id',
        'training_requirements',
        'training_programs',
        ['program_id'],
        ['id'],
        ondelete='CASCADE',
    )

    op.add_column(
        'course_sessions',
        sa.Column('cohort_id', app.db.types.GUID(), nullable=True),
    )
    op.create_index(
        'ix_course_sessions_cohort_id', 'course_sessions', ['cohort_id']
    )
    op.create_foreign_key(
        'fk_course_sessions_cohort_id',
        'course_sessions',
        'training_cohorts',
        ['cohort_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint(
        'fk_course_sessions_cohort_id', 'course_sessions', type_='foreignkey'
    )
    op.drop_index('ix_course_sessions_cohort_id', table_name='course_sessions')
    op.drop_column('course_sessions', 'cohort_id')

    op.drop_constraint(
        'fk_training_requirements_program_id',
        'training_requirements',
        type_='foreignkey',
    )
    op.drop_index(
        'ix_training_requirements_program_id', table_name='training_requirements'
    )
    op.drop_column('training_requirements', 'program_id')

    op.drop_index(
        'ix_training_enrollments_member_id', table_name='training_enrollments'
    )
    op.drop_index(
        'ix_training_enrollments_cohort_id', table_name='training_enrollments'
    )
    op.drop_index(
        'ix_training_enrollments_tenant_id', table_name='training_enrollments'
    )
    op.drop_table('training_enrollments')

    op.drop_index(
        'ix_training_cohorts_program_id', table_name='training_cohorts'
    )
    op.drop_index(
        'ix_training_cohorts_tenant_id', table_name='training_cohorts'
    )
    op.drop_table('training_cohorts')

    op.drop_index(
        'ix_training_programs_tenant_id', table_name='training_programs'
    )
    op.drop_table('training_programs')
