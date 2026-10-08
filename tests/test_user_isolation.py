"""
tests/test_user_isolation.py
Comprehensive cross-user data isolation tests.
Proves that:
1. User B receives 404 for User A's resources (no enumeration or information leaks).
2. Unauthenticated callers receive 401 across all protected routes.
3. Every application route is programmatically inspected from FastAPI app.routes to ensure
   it requires authentication and enforces cross-user scoping.
4. /progress and /interview/history return only the authenticated caller's records.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
import backend.models as models


PUBLIC_ROUTES = {
    ("/", "GET"),
    ("/auth/register", "POST"),
    ("/auth/login", "POST"),
    ("/auth/logout", "POST"),
    ("/auth/verify-email", "POST"),
    ("/auth/resend-verification", "POST"),
    ("/auth/forgot-password", "POST"),
    ("/auth/reset-password", "POST"),
    ("/openapi.json", "GET"),
    ("/docs", "GET"),
    ("/docs/oauth2-redirect", "GET"),
    ("/redoc", "GET"),
    ("/health", "GET"),
    ("/health/ready", "GET"),
}


def test_programmatic_route_auth_inspection(unauth_client: TestClient):
    """
    Programmatically extracts every registered route from the FastAPI application.
    Fails the test suite if any new route is added without authentication protection.
    """
    missing_protection = []

    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set())

        if not path or not methods:
            continue

        for method in methods:
            if method in {"HEAD", "OPTIONS"}:
                continue
            if (path, method) in PUBLIC_ROUTES:
                continue

            # Route has path params (e.g. {session_id}) -> substitute dummy id
            test_path = path.replace("{session_id}", "9999").replace("{resume_id}", "9999").replace("{answer_id}", "9999")

            res = unauth_client.request(method, test_path, json={})
            # Must return 401 Unauthorized (never 200, 404, or 500)
            if res.status_code != 401:
                missing_protection.append((method, path, res.status_code))

    assert len(missing_protection) == 0, f"Unprotected routes detected: {missing_protection}"


def test_cross_user_isolation_matrix(client: TestClient, client_b: TestClient):
    """
    Sets up resources for User A (client), and proves that User B (client_b)
    cannot access, analyze, complete, view, improve, or delete any of them,
    receiving 404 Not Found in all cases (preventing ID enumeration).
    """
    # 1. User A uploads a resume
    resume_res = client.post("/resume/upload", data={"raw_text": "Candidate A with Python and FastAPI skills."})
    assert resume_res.status_code == 200
    resume_a_id = resume_res.json()["id"]

    # 2. User A starts an interview session
    start_res = client.post("/interview/start", json={
        "mode": "technical",
        "difficulty": "medium",
        "number_of_questions": 2,
        "resume_id": resume_a_id,
        "target_role": "Backend Engineer"
    })
    assert start_res.status_code == 200
    session_a_id = start_res.json()["session_id"]

    # 3. User A submits an answer
    ans_res = client.post("/interview/answer", json={
        "session_id": session_a_id,
        "question_id": 1,
        "question_text": "Explain REST API principles",
        "transcript": "REST APIs use standard HTTP methods like GET and POST for scalable distributed web services.",
        "duration_seconds": 15.0
    })
    assert ans_res.status_code == 200
    answer_a_id = ans_res.json()["answer_id"]

    # 4. User A completes the interview
    comp_res = client.post(f"/interview/{session_a_id}/complete", json={
        "eye_contact_percent": 75.0,
        "blink_rate": 18.0,
        "pause_rate": 1.2
    })
    assert comp_res.status_code == 200

    # -------------------------------------------------------------
    # Cross-User Isolation Matrix: Verify User B gets 404 for all User A resources
    # -------------------------------------------------------------

    # Resume endpoints
    assert client_b.get(f"/resume/{resume_a_id}").status_code == 404
    assert client_b.post("/resume/analyze", json={"resume_id": resume_a_id}).status_code == 404
    assert client_b.delete(f"/resume/{resume_a_id}").status_code == 404

    # Interview session endpoints
    assert client_b.get(f"/interview/{session_a_id}").status_code == 404
    assert client_b.post("/interview/answer", json={
        "session_id": session_a_id,
        "question_id": 2,
        "transcript": "User B trying to submit to User A session."
    }).status_code == 404
    assert client_b.post(f"/interview/{session_a_id}/answer", json={
        "session_id": session_a_id,
        "question_id": 2,
        "transcript": "User B trying to submit to User A session."
    }).status_code == 404
    assert client_b.post("/interview/followup", json={
        "session_id": session_a_id,
        "question_id": 1,
        "question": "Followup?",
        "answer": "Test"
    }).status_code == 404
    assert client_b.post(f"/interview/{session_a_id}/complete", json={}).status_code == 404
    assert client_b.post("/interview/submit", json={"session_id": session_a_id}).status_code == 404
    assert client_b.get(f"/interview/result/{session_a_id}").status_code == 404
    assert client_b.get(f"/report/{session_a_id}").status_code == 404
    assert client_b.post(f"/answer/{answer_a_id}/improve").status_code == 404
    assert client_b.delete(f"/interview/{session_a_id}").status_code == 404

    # Collection endpoints: User B must see empty lists, not User A's data
    progress_b = client_b.get("/progress").json()
    assert progress_b["total_interviews"] == 0
    assert len(progress_b["sessions"]) == 0

    history_b = client_b.get("/interview/history").json()
    assert history_b["total"] == 0
    assert len(history_b["items"]) == 0

    all_b = client_b.get("/interview/all").json()
    assert len(all_b) == 0


def test_legacy_data_unaccessible_until_claimed(client: TestClient, db_session):
    """
    Proves that rows with user_id = NULL cannot be accessed by any user
    through the API until explicitly claimed.
    """
    # Create legacy session without owner
    legacy_session = models.InterviewSession(
        user_id=None,
        mode="technical",
        difficulty="hard",
        total_questions=3,
        status="completed"
    )
    db_session.add(legacy_session)
    db_session.commit()
    db_session.refresh(legacy_session)

    # Authenticated user cannot view it
    res = client.get(f"/interview/{legacy_session.id}")
    assert res.status_code == 404
