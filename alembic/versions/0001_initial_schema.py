"""initial_7_table_schema_and_nullable_metrics

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-06 15:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0001_initial_schema'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # 1. Resumes
    if 'resumes' not in existing_tables:
        op.create_table(
            'resumes',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('filename', sa.String(), nullable=True),
            sa.Column('candidate_name', sa.String(), nullable=True, server_default='Candidate'),
            sa.Column('raw_text', sa.Text(), nullable=True),
            sa.Column('skills', sa.Text(), nullable=True),
            sa.Column('experience', sa.Text(), nullable=True),
            sa.Column('education', sa.Text(), nullable=True),
            sa.Column('resume_score', sa.Float(), nullable=True, server_default='75.0'),
            sa.Column('strengths', sa.Text(), nullable=True, server_default='[]'),
            sa.Column('weak_areas', sa.Text(), nullable=True, server_default='[]'),
            sa.Column('suggested_improvements', sa.Text(), nullable=True, server_default='[]'),
            sa.Column('summary', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True)
        )

    # 2. Interview Sessions
    if 'interview_sessions' not in existing_tables:
        op.create_table(
            'interview_sessions',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('resume_id', sa.Integer(), sa.ForeignKey('resumes.id'), nullable=True),
            sa.Column('mode', sa.String(), nullable=True),
            sa.Column('difficulty', sa.String(), nullable=True),
            sa.Column('target_role', sa.String(), nullable=True, server_default='Software Engineer'),
            sa.Column('total_questions', sa.Integer(), nullable=True),
            sa.Column('current_question_index', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('followup_count', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('status', sa.String(), nullable=True, server_default='in_progress'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True)
        )
    else:
        # Check for missing columns in existing table
        cols = [c['name'] for c in inspector.get_columns('interview_sessions')]
        with op.batch_alter_table('interview_sessions') as batch_op:
            if 'resume_id' not in cols:
                batch_op.add_column(sa.Column('resume_id', sa.Integer(), sa.ForeignKey('resumes.id'), nullable=True))
            if 'target_role' not in cols:
                batch_op.add_column(sa.Column('target_role', sa.String(), nullable=True, server_default='Software Engineer'))

    # 3. Question Bank
    if 'question_bank' not in existing_tables:
        op.create_table(
            'question_bank',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('question_text', sa.Text(), nullable=False),
            sa.Column('category', sa.String(), nullable=True),
            sa.Column('difficulty', sa.String(), nullable=True),
            sa.Column('role', sa.String(), nullable=True)
        )

    # 4. Interview Answers
    if 'interview_answers' not in existing_tables:
        op.create_table(
            'interview_answers',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('session_id', sa.Integer(), sa.ForeignKey('interview_sessions.id'), nullable=True),
            sa.Column('question_id', sa.Integer(), nullable=True),
            sa.Column('question_text', sa.Text(), nullable=True),
            sa.Column('transcript', sa.Text(), nullable=True),
            sa.Column('response_time', sa.Float(), nullable=True),
            sa.Column('duration_seconds', sa.Float(), nullable=True, server_default='0.0'),
            sa.Column('wpm', sa.Float(), nullable=True, server_default='0.0'),
            sa.Column('filler_count', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True)
        )
    else:
        cols = [c['name'] for c in inspector.get_columns('interview_answers')]
        with op.batch_alter_table('interview_answers') as batch_op:
            if 'question_text' not in cols:
                batch_op.add_column(sa.Column('question_text', sa.Text(), nullable=True))
            if 'duration_seconds' not in cols:
                batch_op.add_column(sa.Column('duration_seconds', sa.Float(), nullable=True, server_default='0.0'))
            if 'wpm' not in cols:
                batch_op.add_column(sa.Column('wpm', sa.Float(), nullable=True, server_default='0.0'))
            if 'filler_count' not in cols:
                batch_op.add_column(sa.Column('filler_count', sa.Integer(), nullable=True, server_default='0'))

    # 5. Answer Evaluations
    if 'answer_evaluations' not in existing_tables:
        op.create_table(
            'answer_evaluations',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('answer_id', sa.Integer(), sa.ForeignKey('interview_answers.id'), nullable=True),
            sa.Column('structure_score', sa.Float(), nullable=True, server_default='70.0'),
            sa.Column('clarity_score', sa.Float(), nullable=True, server_default='70.0'),
            sa.Column('depth_score', sa.Float(), nullable=True, server_default='70.0'),
            sa.Column('technical_score', sa.Float(), nullable=True, server_default='70.0'),
            sa.Column('reasoning_score', sa.Float(), nullable=True, server_default='70.0'),
            sa.Column('star_score', sa.Float(), nullable=True, server_default='70.0'),
            sa.Column('consistency_score', sa.Float(), nullable=True, server_default='75.0'),
            sa.Column('overall_score', sa.Float(), nullable=True, server_default='70.0'),
            sa.Column('strengths', sa.Text(), nullable=True, server_default='[]'),
            sa.Column('weaknesses', sa.Text(), nullable=True, server_default='[]'),
            sa.Column('missing_concepts', sa.Text(), nullable=True, server_default='[]'),
            sa.Column('suggestions', sa.Text(), nullable=True, server_default='[]'),
            sa.Column('engine_used', sa.String(), nullable=True, server_default='rubric'),
            sa.Column('prompt_version', sa.String(), nullable=True, server_default='v1.0')
        )
    else:
        cols = [c['name'] for c in inspector.get_columns('answer_evaluations')]
        with op.batch_alter_table('answer_evaluations') as batch_op:
            if 'engine_used' not in cols:
                batch_op.add_column(sa.Column('engine_used', sa.String(), nullable=True, server_default='rubric'))
            if 'prompt_version' not in cols:
                batch_op.add_column(sa.Column('prompt_version', sa.String(), nullable=True, server_default='v1.0'))

    # 6. Follow-up Questions
    if 'followup_questions' not in existing_tables:
        op.create_table(
            'followup_questions',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('session_id', sa.Integer(), sa.ForeignKey('interview_sessions.id'), nullable=True),
            sa.Column('parent_question_id', sa.Integer(), nullable=True),
            sa.Column('followup_text', sa.Text(), nullable=True)
        )

    # 7. Behavioral Metrics (Nullable columns for unmeasured sensors)
    if 'behavioral_metrics' not in existing_tables:
        op.create_table(
            'behavioral_metrics',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('session_id', sa.Integer(), sa.ForeignKey('interview_sessions.id'), nullable=True),
            sa.Column('eye_contact_percent', sa.Float(), nullable=True),
            sa.Column('blink_rate', sa.Float(), nullable=True),
            sa.Column('pause_rate', sa.Float(), nullable=True)
        )

    # 8. Session Scores
    if 'session_scores' not in existing_tables:
        op.create_table(
            'session_scores',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('session_id', sa.Integer(), sa.ForeignKey('interview_sessions.id'), nullable=True),
            sa.Column('behavioral_score', sa.Float(), nullable=True, server_default='0.0'),
            sa.Column('communication_score', sa.Float(), nullable=True, server_default='0.0'),
            sa.Column('technical_score', sa.Float(), nullable=True, server_default='0.0'),
            sa.Column('resume_consistency_score', sa.Float(), nullable=True, server_default='0.0'),
            sa.Column('readiness_score', sa.Float(), nullable=True, server_default='0.0'),
            sa.Column('strongest_category', sa.String(), nullable=True, server_default='Communication'),
            sa.Column('weakest_category', sa.String(), nullable=True, server_default='Technical'),
            sa.Column('insights', sa.Text(), nullable=True, server_default='[]'),
            sa.Column('weights_used', sa.Text(), nullable=True, server_default='{}'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True)
        )
    else:
        cols = [c['name'] for c in inspector.get_columns('session_scores')]
        with op.batch_alter_table('session_scores') as batch_op:
            if 'weights_used' not in cols:
                batch_op.add_column(sa.Column('weights_used', sa.Text(), nullable=True, server_default='{}'))


def downgrade() -> None:
    pass
