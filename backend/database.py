import os
import sqlite3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "interview.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def init_db():
    Base.metadata.create_all(bind=engine)

    # Automatic safe migration for existing SQLite tables
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            col_map = {
                "interview_sessions": [
                    ("resume_id", "INTEGER"),
                    ("target_role", "TEXT")
                ],
                "interview_answers": [
                    ("question_text", "TEXT"),
                    ("duration_seconds", "REAL"),
                    ("wpm", "REAL"),
                    ("filler_count", "INTEGER")
                ],
                "answer_evaluations": [
                    ("technical_score", "REAL"),
                    ("reasoning_score", "REAL"),
                    ("star_score", "REAL"),
                    ("consistency_score", "REAL"),
                    ("strengths", "TEXT"),
                    ("weaknesses", "TEXT"),
                    ("missing_concepts", "TEXT"),
                    ("suggestions", "TEXT")
                ],
                "session_scores": [
                    ("communication_score", "REAL"),
                    ("technical_score", "REAL"),
                    ("resume_consistency_score", "REAL"),
                    ("readiness_score", "REAL"),
                    ("strongest_category", "TEXT"),
                    ("weakest_category", "TEXT"),
                    ("insights", "TEXT"),
                    ("created_at", "DATETIME")
                ]
            }
            for table, cols in col_map.items():
                cursor.execute(f"PRAGMA table_info({table});")
                existing = [c[1] for c in cursor.fetchall()]
                for col_name, col_type in cols:
                    if col_name not in existing:
                        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type};")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Migration note: {e}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()