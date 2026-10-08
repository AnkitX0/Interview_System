"""password_reset

Revision ID: 0007_password_reset
Revises: 0006_email_verification
Create Date: 2026-10-08 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0007_password_reset'
down_revision: Union[str, Sequence[str], None] = '0006_email_verification'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    user_cols = [c['name'] for c in inspector.get_columns('users')]

    with op.batch_alter_table('users') as batch_op:
        if 'password_reset_token_hash' not in user_cols:
            batch_op.add_column(sa.Column('password_reset_token_hash', sa.String(), nullable=True))
        if 'password_reset_expires_at' not in user_cols:
            batch_op.add_column(sa.Column('password_reset_expires_at', sa.DateTime(timezone=True), nullable=True))
        if 'password_reset_used_at' not in user_cols:
            batch_op.add_column(sa.Column('password_reset_used_at', sa.DateTime(timezone=True), nullable=True))
        if 'password_reset_sent_at' not in user_cols:
            batch_op.add_column(sa.Column('password_reset_sent_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('password_reset_sent_at')
        batch_op.drop_column('password_reset_used_at')
        batch_op.drop_column('password_reset_expires_at')
        batch_op.drop_column('password_reset_token_hash')
