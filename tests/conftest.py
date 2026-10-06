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


from backend.services.auth_service import hash_password, create_access_token
from backend.config import AUTH_COOKIE_NAME


@pytest.fixture
def test_user(db_session):
    user = db_session.query(models.User).filter(models.User.email == "testuser@example.com").first()
    if not user:
        user = models.User(
            email="testuser@example.com",
            password_hash=hash_password("testpassword1234"),
            full_name="Default Tester"
        )
        db_session.add(user)
        db_session.flush()
        profile = models.UserProfile(user_id=user.id, target_role="Software Engineer")
        db_session.add(profile)
        db_session.commit()
        db_session.refresh(user)
    return user


@pytest.fixture
def client(db_session, test_user):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    token = create_access_token(test_user.id)
    with TestClient(app) as test_client:
        test_client.headers["Authorization"] = f"Bearer {token}"
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def unauth_client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        test_client.cookies.clear()
        test_client.headers.pop("Authorization", None)
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def client_b(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    user_b = db_session.query(models.User).filter(models.User.email == "user_b@example.com").first()
    if not user_b:
        user_b = models.User(
            email="user_b@example.com",
            password_hash=hash_password("userbpassword1234"),
            full_name="User B"
        )
        db_session.add(user_b)
        db_session.flush()
        profile = models.UserProfile(user_id=user_b.id, target_role="Product Manager")
        db_session.add(profile)
        db_session.commit()
        db_session.refresh(user_b)
    token_b = create_access_token(user_b.id)
    with TestClient(app) as test_client:
        test_client.headers["Authorization"] = f"Bearer {token_b}"
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

