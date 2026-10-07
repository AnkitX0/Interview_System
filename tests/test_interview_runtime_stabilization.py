import pytest
from fastapi.testclient import TestClient
from backend.services.resume_service import validate_resume_document

def test_resume_quality_gate_30page_code_rejection():
    """Verifies that 30-page PDF / code-heavy documents are rejected by quality gate."""
    garbage_code_text = (
        "String url = \"jdbc:mysql://localhost:3306/college\";\n"
        "INFO: Server startup in 1842 ms...\n"
        "<option>B.Tech CSE</option>\n"
        "input { width: 100%; padding: 8px; }\n"
        "Exception in thread \"main\" java.lang.NullPointerException at com.example.Main.main\n"
        "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100));\n"
    ) * 30

    is_valid, msg, details = validate_resume_document(garbage_code_text, filename="30page_code.pdf", page_count=30)
    assert is_valid is False
    assert "doesn't appear to be a resume" in msg or "code" in msg.lower() or "markup" in msg.lower()


def test_resume_upload_endpoint_rejects_garbage(client: TestClient):
    """Verifies POST /resume/upload returns 400 Bad Request when non-resume code dump is provided."""
    garbage_code_text = (
        "String url = \"jdbc:mysql://localhost:3306/college\";\n"
        "INFO: Server startup in 1842 ms...\n"
        "<option>B.Tech CSE</option>\n"
        "input { width: 100%; padding: 8px; }\n"
        "Exception in thread \"main\" java.lang.NullPointerException at com.example.Main.main\n"
        "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100));\n"
    ) * 20

    res = client.post("/resume/upload", data={"raw_text": garbage_code_text})
    assert res.status_code == 400
    assert "doesn't appear to be a resume" in res.json()["error"]["message"] or "code" in res.json()["error"]["message"].lower()


def test_interview_completion_idempotency(client: TestClient):
    """Verifies POST /interview/{session_id}/complete can be called repeatedly without error."""
    start_res = client.post("/interview/start", json={"mode": "technical", "number_of_questions": 2})
    assert start_res.status_code == 200
    session_id = start_res.json()["session_id"]

    # Submit answer
    client.post(f"/interview/{session_id}/answer", json={
        "session_id": session_id,
        "question_id": 1,
        "transcript": "ACID properties ensure transaction reliability.",
        "response_time": 15.0,
        "duration_seconds": 15.0,
        "wpm": 130.0
    })

    # Complete session first time
    comp1 = client.post(f"/interview/{session_id}/complete", json={})
    assert comp1.status_code == 200
    r1 = comp1.json()

    # Complete session second time (idempotency check)
    comp2 = client.post(f"/interview/{session_id}/complete", json={})
    assert comp2.status_code == 200
    r2 = comp2.json()

    assert r1["session_id"] == r2["session_id"]
    assert r1["status"] == "completed"
    assert r2["status"] == "completed"
