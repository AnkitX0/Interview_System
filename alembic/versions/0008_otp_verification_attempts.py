"""otp_verification_attempts

Revision ID: 0008_otp_verification_attempts
Revises: 0007_password_reset
Create Date: 2026-10-16 10:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0008_otp_verification_attempts'
down_revision: Union[str, Sequence[str], None] = '0007_password_reset'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    user_cols = [c['name'] for c in inspector.get_columns('users')]

    with op.batch_alter_table('users') as batch_op:
        if 'verification_attempts' not in user_cols:
            batch_op.add_column(sa.Column('verification_attempts', sa.Integer(), server_default='0', nullable=False))


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('verification_attempts')
