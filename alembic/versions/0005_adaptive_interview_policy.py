"""adaptive_interview_policy

Revision ID: 0005_adaptive_interview_policy
Revises: 0004_practice_recommendations
Create Date: 2026-10-07 10:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0005_adaptive_interview_policy'
down_revision: Union[str, Sequence[str], None] = '0004_practice_recommendations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    session_cols = [c['name'] for c in inspector.get_columns('interview_sessions')]

    with op.batch_alter_table('interview_sessions') as batch_op:
        if 'question_mode' not in session_cols:
            batch_op.add_column(sa.Column('question_mode', sa.String(), server_default='ADAPTIVE', nullable=True))
        if 'session_policy' not in session_cols:
            batch_op.add_column(sa.Column('session_policy', sa.String(), server_default='STANDARD', nullable=True))
        if 'interview_state' not in session_cols:
            batch_op.add_column(sa.Column('interview_state', sa.String(), server_default='STARTING', nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('interview_sessions') as batch_op:
        batch_op.drop_column('interview_state')
        batch_op.drop_column('session_policy')
        batch_op.drop_column('question_mode')
