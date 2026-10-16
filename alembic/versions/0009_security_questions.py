"""security_questions
Revision ID: 0009_security_questions
Revises: 0008_otp_verification_attempts
Create Date: 2026-10-16 11:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0009_security_questions'
down_revision: Union[str, Sequence[str], None] = '0008_otp_verification_attempts'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    user_cols = [c['name'] for c in inspector.get_columns('users')]

    with op.batch_alter_table('users') as batch_op:
        if 'security_question' not in user_cols:
            batch_op.add_column(sa.Column('security_question', sa.String(), nullable=True))
        if 'security_answer_hash' not in user_cols:
            batch_op.add_column(sa.Column('security_answer_hash', sa.String(), nullable=True))
        if 'recovery_attempts' not in user_cols:
            batch_op.add_column(sa.Column('recovery_attempts', sa.Integer(), server_default='0', nullable=False))


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('recovery_attempts')
        batch_op.drop_column('security_answer_hash')
        batch_op.drop_column('security_question')
