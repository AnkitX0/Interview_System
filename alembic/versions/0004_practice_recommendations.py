"""practice_recommendations

Revision ID: 0004_practice_recommendations
Revises: 0003_intelligence_layer
Create Date: 2026-10-06 20:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0004_practice_recommendations'
down_revision: Union[str, Sequence[str], None] = '0003_intelligence_layer'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'practice_recommendations' not in existing_tables:
        op.create_table(
            'practice_recommendations',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('source_session_id', sa.Integer(), sa.ForeignKey('interview_sessions.id', ondelete='SET NULL'), nullable=True, index=True),
            sa.Column('weakness_type', sa.String(), nullable=False),
            sa.Column('dimension', sa.String(), nullable=False),
            sa.Column('priority', sa.Integer(), server_default='1', nullable=False),
            sa.Column('rationale', sa.Text(), nullable=False),
            sa.Column('practice_type', sa.String(), nullable=False),
            sa.Column('target_count', sa.Integer(), server_default='5', nullable=False),
            sa.Column('difficulty', sa.String(), server_default='medium', nullable=False),
            sa.Column('status', sa.String(), server_default='pending', nullable=False),
            sa.Column('decision_metadata', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'practice_recommendations' in existing_tables:
        op.drop_table('practice_recommendations')
