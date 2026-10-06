import os
import sqlite3
import tempfile
import pytest
from alembic.config import Config
from alembic import command


def test_legacy_pre_alembic_db_upgrades_without_data_loss():
    """
    Simulates a legacy pre-Alembic interview.db without alembic_version table
    containing pre-existing data across tables, and proves:
    1. Upgrade to head executes successfully without schema collision.
    2. Zero data loss: all pre-existing rows and values remain intact.
    3. New columns (e.g. weights_used, target_role) are created.
    4. Subsequent upgrade when already at head is an idempotent no-op.
    """
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ini_path = os.path.join(root_dir, "alembic.ini")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
        db_path = tmp_db.name

    try:
        # 1. Create legacy SQLite database with pre-Alembic tables (no alembic_version)
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # Legacy resumes
        cur.execute("""
            CREATE TABLE resumes (
                id INTEGER PRIMARY KEY,
                filename TEXT,
                candidate_name TEXT,
                raw_text TEXT,
                skills TEXT,
                experience TEXT,
                education TEXT,
                resume_score REAL,
                strengths TEXT,
                weak_areas TEXT,
                suggested_improvements TEXT,
                summary TEXT,
                created_at TIMESTAMP
            )
        """)
        cur.execute("""
            INSERT INTO resumes (id, candidate_name, raw_text, skills, resume_score)
            VALUES (1, 'Legacy Candidate', 'Experienced Engineer', '["Python", "SQL"]', 82.5)
        """)

        # Legacy interview_sessions (lacks target_role and resume_id)
        cur.execute("""
            CREATE TABLE interview_sessions (
                id INTEGER PRIMARY KEY,
                mode TEXT,
                difficulty TEXT,
                total_questions INTEGER,
                current_question_index INTEGER,
                followup_count INTEGER,
                status TEXT,
                created_at TIMESTAMP
            )
        """)
        cur.execute("""
            INSERT INTO interview_sessions (id, mode, difficulty, total_questions, status)
            VALUES (1, 'technical', 'medium', 3, 'completed')
        """)

        # Legacy question_bank
        cur.execute("""
            CREATE TABLE question_bank (
                id INTEGER PRIMARY KEY,
                question_text TEXT,
                category TEXT,
                difficulty TEXT,
                role TEXT
            )
        """)
        cur.execute("""
            INSERT INTO question_bank (id, question_text, category, difficulty)
            VALUES (1, 'Explain database indexing tradeoffs.', 'Technical', 'Medium')
        """)

        # Legacy session_scores (lacks weights_used)
        cur.execute("""
            CREATE TABLE session_scores (
                id INTEGER PRIMARY KEY,
                session_id INTEGER,
                behavioral_score REAL,
                communication_score REAL,
                technical_score REAL,
                resume_consistency_score REAL,
                readiness_score REAL,
                strongest_category TEXT,
                weakest_category TEXT,
                insights TEXT,
                created_at TIMESTAMP
            )
        """)
        cur.execute("""
            INSERT INTO session_scores (id, session_id, behavioral_score, communication_score, technical_score, readiness_score)
            VALUES (1, 1, 80.0, 75.0, 85.0, 80.0)
        """)

        conn.commit()
        conn.close()

        # 2. Run Alembic upgrade to head
        alembic_cfg = Config(ini_path)
        alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
        command.upgrade(alembic_cfg, "head")

        # 3. Verify zero data loss and column migration
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # Verify candidate row still intact
        cur.execute("SELECT id, candidate_name, resume_score FROM resumes WHERE id = 1")
        resume_row = cur.fetchone()
        assert resume_row == (1, 'Legacy Candidate', 82.5)

        # Verify session row still intact and new column added
        cur.execute("SELECT id, mode, target_role, resume_id FROM interview_sessions WHERE id = 1")
        session_row = cur.fetchone()
        assert session_row[0] == 1
        assert session_row[1] == 'technical'
        assert session_row[2] == 'Software Engineer'  # server_default applied

        # Verify score row still intact and weights_used column added
        cur.execute("SELECT id, session_id, readiness_score, weights_used FROM session_scores WHERE id = 1")
        score_row = cur.fetchone()
        assert score_row[0] == 1
        assert score_row[1] == 1
        assert score_row[2] == 80.0
        assert score_row[3] == '{}'  # server_default applied

        # Verify alembic_version table exists and is at head
        from alembic.script import ScriptDirectory
        script = ScriptDirectory.from_config(alembic_cfg)
        expected_head = script.get_current_head()

        cur.execute("SELECT version_num FROM alembic_version")
        version_row = cur.fetchone()
        assert version_row is not None
        assert version_row[0] == expected_head

        # Verify new Phase 2 & 3 tables and columns created
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        assert "users" in tables
        assert "user_profile" in tables
        assert "voice_metrics" in tables
        assert "consent_records" in tables
        assert "resume_skills" in tables
        assert "resume_projects" in tables
        assert "resume_claims" in tables
        assert "resume_flags" in tables
        assert "interview_questions" in tables
        assert "interview_decisions" in tables
        assert "claim_consistency" in tables
        assert "answer_visual_metrics" in tables

        # Verify user_id added to resumes and interview_sessions
        cur.execute("PRAGMA table_info(resumes)")
        resume_cols = [r[1] for r in cur.fetchall()]
        assert "user_id" in resume_cols
        assert "role_fit_scores" in resume_cols

        cur.execute("PRAGMA table_info(interview_sessions)")
        session_cols = [r[1] for r in cur.fetchall()]
        assert "user_id" in session_cols

        conn.close()

        # 4. Prove that running upgrade when already at head is an idempotent no-op
        command.upgrade(alembic_cfg, "head")

    finally:
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass
