import pytest
from backend.main import app

def test_interview_turns_endpoint_and_skip_persistence(client):
    # 1. Start an interview session
    start_payload = {
        "mode": "technical",
        "difficulty": "medium",
        "target_role": "Backend Engineer",
        "question_count": 5
    }
    start_resp = client.post("/interview/start", json=start_payload)
    assert start_resp.status_code == 200
    session_data = start_resp.json()
    session_id = session_data["session_id"]

    # 2. Query turns initially - should be empty list
    turns_resp = client.get(f"/interview/{session_id}/turns")
    assert turns_resp.status_code == 200
    turns_data = turns_resp.json()
    assert turns_data["session_id"] == session_id
    assert turns_data["total_turns"] == 0
    assert turns_data["turns"] == []

    # 3. Submit a skipped question
    skip_payload = {
        "session_id": session_id,
        "question_id": 1,
        "question_text": "Explain PostgreSQL MVCC internals.",
        "reason": "candidate_skipped"
    }
    skip_resp = client.post(f"/interview/{session_id}/skip", json=skip_payload)
    assert skip_resp.status_code == 200
    skip_data = skip_resp.json()
    assert "turn_id" in skip_data

    # 4. Turns endpoint should now return 1 turn, with answer_status="SKIPPED" and score=None
    turns_resp_2 = client.get(f"/interview/{session_id}/turns")
    assert turns_resp_2.status_code == 200
    turns_data_2 = turns_resp_2.json()
    assert turns_data_2["total_turns"] == 1
    t1 = turns_data_2["turns"][0]
    assert t1["answer_status"] == "SKIPPED"
    assert t1["evaluation_status"] == "NOT_APPLICABLE"
    assert t1["score"] is None

    # 5. Submit an empty answer
    empty_ans_payload = {
        "session_id": session_id,
        "question_id": 2,
        "question_text": "How does redis caching work?",
        "transcript": "",
        "response_time": 5.0,
        "duration_seconds": 5.0,
        "wpm": 0.0,
        "filler_count": 0
    }
    ans_resp = client.post(f"/interview/{session_id}/answer", json=empty_ans_payload)
    assert ans_resp.status_code == 200
    ans_data = ans_resp.json()
    assert ans_data["answer_status"] == "EMPTY"
    assert ans_data["evaluation_status"] == "NOT_APPLICABLE"

    # 6. Submit a meaningful answer
    full_ans_payload = {
        "session_id": session_id,
        "question_id": 3,
        "question_text": "Describe ACID properties in relational databases.",
        "transcript": "ACID stands for Atomicity, Consistency, Isolation, and Durability. In PostgreSQL, isolation is achieved using multi-version concurrency control.",
        "response_time": 15.0,
        "duration_seconds": 15.0,
        "wpm": 80.0,
        "filler_count": 0
    }
    full_resp = client.post(f"/interview/{session_id}/answer", json=full_ans_payload)
    assert full_resp.status_code == 200
    full_data = full_resp.json()
    assert full_data["answer_status"] == "ANSWERED"
    assert full_data["evaluation_status"] == "EVALUATED"
    assert full_data["score"] is not None

    # 7. Turns endpoint should now reflect 3 total turns
    turns_resp_3 = client.get(f"/interview/{session_id}/turns")
    assert turns_resp_3.status_code == 200
    turns_data_3 = turns_resp_3.json()
    assert turns_data_3["total_turns"] == 3
