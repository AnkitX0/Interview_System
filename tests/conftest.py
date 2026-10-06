import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.database import Base, get_db
import backend.models as models
from backend.main import app

# Shared in-memory test database for clean, isolated testing
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    # Seed sample questions for testing
    sample_questions = [
        ("Explain REST API architecture.", "Technical", "medium", "backend"),
        ("What is Docker and why is it used?", "Technical", "medium", "backend"),
        ("What is time complexity?", "Technical", "easy", "backend"),
        ("What is a microservices architecture?", "Technical", "hard", "backend"),
        ("Tell me about yourself.", "HR", "easy", "general"),
        ("Why should we hire you?", "HR", "easy", "general"),
        ("Describe a challenging project you worked on.", "Behavioral", "medium", "general"),
        ("Tell me about a time you failed.", "Behavioral", "medium", "general"),
        ("Your project failed in production. What do you do?", "Pressure", "hard", "general"),
        ("A teammate is underperforming. How do you handle it?", "Pressure", "hard", "general"),
    ]
    for q_text, cat, diff, role in sample_questions:
        db.add(models.QuestionBank(
            question_text=q_text,
            category=cat,
            difficulty=diff,
            role=role
        ))
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def golden_answers():
    return {
        "weak": "I did some coding. It was basically good stuff. I fixed bugs.",
        "average": (
            "In my project, we used FastAPI and PostgreSQL to build backend REST endpoints. "
            "I worked on optimizing database queries and fixing performance bottlenecks because requests were slow. "
            "This improved response times and made the system run better."
        ),
        "strong": (
            "In our production distributed payments platform, we faced critical latency spikes where database query "
            "times exceeded 450ms during peak transaction windows. My objective was to eliminate table lock contention "
            "and restore sub-100ms API response SLAs without downtime. I analyzed query execution plans, architected an "
            "asynchronous write-through caching layer using Redis, and added composite indexes to our high-frequency tables. "
            "Furthermore, I evaluated the tradeoff between cache consistency and network overhead. As a result, p99 latency "
            "was reduced by 65% from 450ms to 120ms, and system throughput successfully scaled to 15,000 requests per second."
        )
    }

