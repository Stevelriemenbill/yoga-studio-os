"""conversations + messages tables

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-07-08 20:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

import app.db.types

revision: str = 'c9d0e1f2a3b4'
down_revision: str | None = 'b8c9d0e1f2a3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'conversations',
        sa.Column('user_low_id', app.db.types.GUID(), nullable=False),
        sa.Column('user_high_id', app.db.types.GUID(), nullable=False),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(['user_low_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_high_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'tenant_id', 'user_low_id', 'user_high_id', name='uq_conversations_pair'
        ),
    )
    op.create_index(
        op.f('ix_conversations_tenant_id'), 'conversations', ['tenant_id'], unique=False
    )
    op.create_index(
        op.f('ix_conversations_user_low_id'),
        'conversations',
        ['user_low_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_conversations_user_high_id'),
        'conversations',
        ['user_high_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_conversations_last_message_at'),
        'conversations',
        ['last_message_at'],
        unique=False,
    )

    op.create_table(
        'messages',
        sa.Column('conversation_id', app.db.types.GUID(), nullable=False),
        sa.Column('sender_id', app.db.types.GUID(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ['conversation_id'], ['conversations.id'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_messages_tenant_id'), 'messages', ['tenant_id'], unique=False
    )
    op.create_index(
        op.f('ix_messages_conversation_id'),
        'messages',
        ['conversation_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_messages_sender_id'), 'messages', ['sender_id'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_messages_sender_id'), table_name='messages')
    op.drop_index(op.f('ix_messages_conversation_id'), table_name='messages')
    op.drop_index(op.f('ix_messages_tenant_id'), table_name='messages')
    op.drop_table('messages')

    op.drop_index(
        op.f('ix_conversations_last_message_at'), table_name='conversations'
    )
    op.drop_index(op.f('ix_conversations_user_high_id'), table_name='conversations')
    op.drop_index(op.f('ix_conversations_user_low_id'), table_name='conversations')
    op.drop_index(op.f('ix_conversations_tenant_id'), table_name='conversations')
    op.drop_table('conversations')
