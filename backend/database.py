import os
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, declarative_base

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "interview.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")
# Support hosting platforms that provide postgres:// prefix (e.g. Render, Railway)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def init_db():
    """Initializes the database schema using Alembic versioned migrations and creates any missing tables."""
    import backend.models  # Ensure all model tables are registered with Base.metadata

    root_dir = os.path.dirname(BASE_DIR)
    ini_path = os.path.join(root_dir, "alembic.ini")
    if os.path.exists(ini_path):
        from alembic.config import Config
        from alembic import command

        alembic_cfg = Config(ini_path)
        alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)

        try:
            command.upgrade(alembic_cfg, "head")
        except Exception:
            pass

    Base.metadata.create_all(bind=engine)

    # Automatically add new columns if existing SQLite DB was created earlier
    if DATABASE_URL.startswith("sqlite"):
        try:
            with engine.connect() as conn:
                # 1. user_profile columns
                existing_up = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(user_profile)").fetchall()]
                up_cols = {
                    "phone": "VARCHAR",
                    "location": "VARCHAR",
                    "bio": "TEXT",
                    "degree": "VARCHAR",
                    "skills_categorized": "JSON",
                    "professional_links": "JSON",
                }
                for col, col_type in up_cols.items():
                    if col not in existing_up:
                        conn.exec_driver_sql(f"ALTER TABLE user_profile ADD COLUMN {col} {col_type}")

                # 2. interview_answers columns
                existing_ia = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(interview_answers)").fetchall()]
                ia_cols = {
                    "answer_status": "VARCHAR DEFAULT 'ANSWERED'",
                    "evaluation_status": "VARCHAR DEFAULT 'EVALUATED'",
                    "score": "FLOAT",
                    "topic": "VARCHAR",
                    "category": "VARCHAR",
                    "resume_reference": "TEXT",
                }
                for col, col_def in ia_cols.items():
                    if col not in existing_ia:
                        conn.exec_driver_sql(f"ALTER TABLE interview_answers ADD COLUMN {col} {col_def}")

                # 3. users email verification and password reset columns
                existing_u = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()]
                u_cols = {
                    "email_verified": "BOOLEAN DEFAULT 1",
                    "verification_token_hash": "VARCHAR",
                    "verification_expires_at": "DATETIME",
                    "verification_used_at": "DATETIME",
                    "verification_sent_at": "DATETIME",
                    "password_reset_token_hash": "VARCHAR",
                    "password_reset_expires_at": "DATETIME",
                    "password_reset_used_at": "DATETIME",
                    "password_reset_sent_at": "DATETIME",
                }
                for col, col_def in u_cols.items():
                    if col not in existing_u:
                        conn.exec_driver_sql(f"ALTER TABLE users ADD COLUMN {col} {col_def}")

                conn.commit()
        except Exception:
            pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()