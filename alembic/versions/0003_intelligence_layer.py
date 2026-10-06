"""intelligence_layer

Revision ID: 0003_intelligence_layer
Revises: 0002_auth_and_user_scoping
Create Date: 2026-10-06 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0003_intelligence_layer'
down_revision: Union[str, Sequence[str], None] = '0002_auth_and_user_scoping'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # 1. resume_skills table
    if 'resume_skills' not in existing_tables:
        op.create_table(
            'resume_skills',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('resume_id', sa.Integer(), sa.ForeignKey('resumes.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('category', sa.String(), nullable=False),
            sa.Column('confidence', sa.Float(), server_default='1.0', nullable=True),
            sa.Column('evidenced', sa.Boolean(), server_default='1', nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        )

    # 2. resume_projects table
    if 'resume_projects' not in existing_tables:
        op.create_table(
            'resume_projects',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('resume_id', sa.Integer(), sa.ForeignKey('resumes.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('title', sa.String(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('technologies', sa.JSON(), nullable=True),
            sa.Column('bullets', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        )

    # 3. resume_claims table
    if 'resume_claims' not in existing_tables:
        op.create_table(
            'resume_claims',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('resume_id', sa.Integer(), sa.ForeignKey('resumes.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('project_id', sa.Integer(), sa.ForeignKey('resume_projects.id', ondelete='SET NULL'), nullable=True, index=True),
            sa.Column('claim_text', sa.Text(), nullable=False),
            sa.Column('claim_type', sa.String(), server_default='general', nullable=False),
            sa.Column('technologies', sa.JSON(), nullable=True),
            sa.Column('has_metric', sa.Boolean(), server_default='0', nullable=True),
            sa.Column('probe_priority', sa.Float(), server_default='0.5', nullable=True),
            sa.Column('reasons', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        )

    # 4. resume_flags table
    if 'resume_flags' not in existing_tables:
        op.create_table(
            'resume_flags',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('resume_id', sa.Integer(), sa.ForeignKey('resumes.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('claim_id', sa.Integer(), sa.ForeignKey('resume_claims.id', ondelete='CASCADE'), nullable=True, index=True),
            sa.Column('flag_type', sa.String(), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('severity', sa.String(), server_default='info', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        )

    # 5. interview_questions table
    if 'interview_questions' not in existing_tables:
        op.create_table(
            'interview_questions',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('session_id', sa.Integer(), sa.ForeignKey('interview_sessions.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('sequence_order', sa.Integer(), nullable=False),
            sa.Column('question_text', sa.Text(), nullable=False),
            sa.Column('question_type', sa.String(), server_default='bank', nullable=False),
            sa.Column('source', sa.String(), server_default='bank', nullable=False),
            sa.Column('claim_id', sa.Integer(), sa.ForeignKey('resume_claims.id', ondelete='SET NULL'), nullable=True, index=True),
            sa.Column('ladder_stage', sa.String(), nullable=True),
            sa.Column('difficulty', sa.String(), server_default='medium', nullable=True),
            sa.Column('time_limit_seconds', sa.Integer(), nullable=True),
            sa.Column('generated_reason', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        )

    # 6. interview_decisions table
    if 'interview_decisions' not in existing_tables:
        op.create_table(
            'interview_decisions',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('session_id', sa.Integer(), sa.ForeignKey('interview_sessions.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('turn', sa.Integer(), nullable=False),
            sa.Column('decision', sa.String(), nullable=False),
            sa.Column('reason', sa.Text(), nullable=False),
            sa.Column('inputs', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        )

    # 7. claim_consistency table
    if 'claim_consistency' not in existing_tables:
        op.create_table(
            'claim_consistency',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('session_id', sa.Integer(), sa.ForeignKey('interview_sessions.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('claim_id', sa.Integer(), sa.ForeignKey('resume_claims.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('label', sa.String(), server_default='unverified', nullable=False),
            sa.Column('evidence', sa.JSON(), nullable=True),
            sa.Column('answers_considered', sa.Integer(), server_default='0', nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        )

    # 8. answer_visual_metrics table
    if 'answer_visual_metrics' not in existing_tables:
        op.create_table(
            'answer_visual_metrics',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('answer_id', sa.Integer(), sa.ForeignKey('interview_answers.id', ondelete='CASCADE'), unique=True, nullable=False, index=True),
            sa.Column('head_alignment_percent', sa.Float(), nullable=True),
            sa.Column('blink_rate', sa.Float(), nullable=True),
            sa.Column('head_movement_variance', sa.Float(), nullable=True),
            sa.Column('face_visibility_ratio', sa.Float(), nullable=True),
            sa.Column('head_shift_count', sa.Integer(), nullable=True),
            sa.Column('frames_sampled', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        )

    # Add columns to resumes
    if 'resumes' in existing_tables:
        resume_cols = [c['name'] for c in inspector.get_columns('resumes')]
        if 'role_fit_scores' not in resume_cols:
            op.add_column('resumes', sa.Column('role_fit_scores', sa.JSON(), nullable=True))
        if 'risk_areas' not in resume_cols:
            op.add_column('resumes', sa.Column('risk_areas', sa.JSON(), nullable=True))

    # Add columns to answer_evaluations
    if 'answer_evaluations' in existing_tables:
        eval_cols = [c['name'] for c in inspector.get_columns('answer_evaluations')]
        if 'verification_risk_score' not in eval_cols:
            op.add_column('answer_evaluations', sa.Column('verification_risk_score', sa.Float(), nullable=True))
        if 'verification_risk_level' not in eval_cols:
            op.add_column('answer_evaluations', sa.Column('verification_risk_level', sa.String(), nullable=True))
        if 'verification_risk_evidence' not in eval_cols:
            op.add_column('answer_evaluations', sa.Column('verification_risk_evidence', sa.JSON(), nullable=True))
        if 'verification_risk_explanation' not in eval_cols:
            op.add_column('answer_evaluations', sa.Column('verification_risk_explanation', sa.Text(), nullable=True))

    # Add column to session_scores
    if 'session_scores' in existing_tables:
        score_cols = [c['name'] for c in inspector.get_columns('session_scores')]
        if 'consistency_source' not in score_cols:
            op.add_column('session_scores', sa.Column('consistency_source', sa.String(), server_default='heuristic', nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    for tbl in [
        'answer_visual_metrics',
        'claim_consistency',
        'interview_decisions',
        'interview_questions',
        'resume_flags',
        'resume_claims',
        'resume_projects',
        'resume_skills',
    ]:
        if tbl in existing_tables:
            op.drop_table(tbl)
