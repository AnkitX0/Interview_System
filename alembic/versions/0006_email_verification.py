"""email_verification

Revision ID: 0006_email_verification
Revises: 0005_adaptive_interview_policy
Create Date: 2026-10-08 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0006_email_verification'
down_revision: Union[str, Sequence[str], None] = '0005_adaptive_interview_policy'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    user_cols = [c['name'] for c in inspector.get_columns('users')]

    with op.batch_alter_table('users') as batch_op:
        if 'email_verified' not in user_cols:
            batch_op.add_column(sa.Column('email_verified', sa.Boolean(), server_default='1', nullable=False))
        if 'verification_token_hash' not in user_cols:
            batch_op.add_column(sa.Column('verification_token_hash', sa.String(), nullable=True))
        if 'verification_expires_at' not in user_cols:
            batch_op.add_column(sa.Column('verification_expires_at', sa.DateTime(timezone=True), nullable=True))
        if 'verification_used_at' not in user_cols:
            batch_op.add_column(sa.Column('verification_used_at', sa.DateTime(timezone=True), nullable=True))
        if 'verification_sent_at' not in user_cols:
            batch_op.add_column(sa.Column('verification_sent_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('verification_sent_at')
        batch_op.drop_column('verification_used_at')
        batch_op.drop_column('verification_expires_at')
        batch_op.drop_column('verification_token_hash')
        batch_op.drop_column('email_verified')
