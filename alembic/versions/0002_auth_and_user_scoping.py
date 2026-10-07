"""auth_and_user_scoping

Revision ID: 0002_auth_and_user_scoping
Revises: 0001_initial_schema
Create Date: 2026-10-06 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0002_auth_and_user_scoping'
down_revision: Union[str, Sequence[str], None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # 1. users table
    if 'users' not in existing_tables:
        op.create_table(
            'users',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('email', sa.String(), unique=True, index=True, nullable=False),
            sa.Column('password_hash', sa.String(), nullable=False),
            sa.Column('full_name', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        )

    # 2. user_profile table
    if 'user_profile' not in existing_tables:
        op.create_table(
            'user_profile',
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('target_role', sa.String(), nullable=True),
            sa.Column('domain', sa.String(), nullable=True),
            sa.Column('experience_level', sa.String(), nullable=True),
            sa.Column('university', sa.String(), nullable=True),
            sa.Column('graduation_year', sa.Integer(), nullable=True),
            sa.Column('current_status', sa.String(), nullable=True),
            sa.Column('target_companies', sa.JSON(), nullable=True),
            sa.Column('interview_goal', sa.String(), nullable=True),
            sa.Column('weekly_practice_goal', sa.Integer(), nullable=True),
        )

    # 3. Add user_id column to resumes if missing
    if 'resumes' in existing_tables:
        cols = [c['name'] for c in inspector.get_columns('resumes')]
        if 'user_id' not in cols:
            op.add_column('resumes', sa.Column('user_id', sa.Integer(), nullable=True))
            try:
                op.create_index('ix_resumes_user_id', 'resumes', ['user_id'])
            except Exception:
                pass

    # 4. Add user_id column to interview_sessions if missing
    if 'interview_sessions' in existing_tables:
        cols = [c['name'] for c in inspector.get_columns('interview_sessions')]
        if 'user_id' not in cols:
            op.add_column('interview_sessions', sa.Column('user_id', sa.Integer(), nullable=True))
            try:
                op.create_index('ix_interview_sessions_user_id', 'interview_sessions', ['user_id'])
            except Exception:
                pass

    # 5. voice_metrics table
    if 'voice_metrics' not in existing_tables:
        op.create_table(
            'voice_metrics',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('answer_id', sa.Integer(), sa.ForeignKey('interview_answers.id', ondelete='CASCADE'), unique=True, nullable=False, index=True),
            sa.Column('words_per_minute', sa.Float(), nullable=True),
            sa.Column('filler_word_count', sa.Integer(), nullable=True),
            sa.Column('avg_pause_duration', sa.Float(), nullable=True),
            sa.Column('longest_pause', sa.Float(), nullable=True),
            sa.Column('pause_count', sa.Integer(), nullable=True),
            sa.Column('silence_ratio', sa.Float(), nullable=True),
            sa.Column('vocabulary_diversity_score', sa.Float(), nullable=True),
            sa.Column('speech_source', sa.String(), server_default='speech', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        )

    # 6. consent_records table
    if 'consent_records' not in existing_tables:
        op.create_table(
            'consent_records',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('consent_type', sa.String(), nullable=False),
            sa.Column('policy_version', sa.String(), nullable=False),
            sa.Column('granted', sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'consent_records' in existing_tables:
        op.drop_table('consent_records')

    if 'voice_metrics' in existing_tables:
        op.drop_table('voice_metrics')

    if 'interview_sessions' in existing_tables:
        cols = [c['name'] for c in inspector.get_columns('interview_sessions')]
        if 'user_id' in cols:
            with op.batch_alter_table('interview_sessions') as batch_op:
                batch_op.drop_column('user_id')

    if 'resumes' in existing_tables:
        cols = [c['name'] for c in inspector.get_columns('resumes')]
        if 'user_id' in cols:
            with op.batch_alter_table('resumes') as batch_op:
                batch_op.drop_column('user_id')

    if 'user_profile' in existing_tables:
        op.drop_table('user_profile')

    if 'users' in existing_tables:
        op.drop_table('users')
