import os
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, declarative_base

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "interview.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
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
    """Initializes the database schema using Alembic versioned migrations."""
    root_dir = os.path.dirname(BASE_DIR)
    ini_path = os.path.join(root_dir, "alembic.ini")
    if os.path.exists(ini_path):
        from alembic.config import Config
        from alembic import command
        from alembic.script import ScriptDirectory
        from alembic.migration import MigrationContext

        alembic_cfg = Config(ini_path)
        alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)

        # Fast idempotent check: if DB is already at head, skip upgrade
        try:
            with engine.connect() as conn:
                ctx = MigrationContext.configure(conn)
                current_rev = ctx.get_current_revision()
                script = ScriptDirectory.from_config(alembic_cfg)
                head_rev = script.get_current_head()
                if current_rev and current_rev == head_rev:
                    return
        except Exception:
            pass

        command.upgrade(alembic_cfg, "head")
    else:
        Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()