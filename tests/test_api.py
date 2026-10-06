import pytest
import json


def test_root_endpoint(client):
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert "AI Interview Intelligence" in data["service"]


def test_resume_upload_and_retrieve(client):
    # Upload via raw_text form
    res = client.post(
        "/resume/upload",
        data={"raw_text": "Alex Taylor\nEmail: alex@example.com\nSkills: Python, FastAPI, React, Docker, SQL.\nExperience: Built REST microservices.\nEducation: B.Tech CSE."}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["candidate_name"] == "Alex Taylor"
    assert "Python" in data["skills"]
    assert "resume_score" in data
    resume_id = data["id"]

    # Retrieve by ID
    get_res = client.get(f"/resume/{resume_id}")
    assert get_res.status_code == 200
    assert get_res.json()["candidate_name"] == "Alex Taylor"


def test_interview_session_flow_end_to_end(client, golden_answers):
    # 1. Start session
    start_payload = {
        "mode": "technical",
        "difficulty": "medium",
        "number_of_questions": 2,
        "target_role": "Backend Engineer"
    }
    start_res = client.post("/interview/start", json=start_payload)
    assert start_res.status_code == 200
    session_data = start_res.json()
    session_id = session_data["session_id"]
    questions = session_data["questions"]
    assert len(questions) == 2

    # 2. Check session status
    status_res = client.get(f"/interview/{session_id}")
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "in_progress"

    # 3. Submit answer
    q0 = questions[0]
    ans_payload = {
        "session_id": session_id,
        "question_id": q0["id"],
        "question_text": q0["question"],
        "transcript": golden_answers["strong"],
        "response_time": 25.0,
        "wpm": 130.0,
        "filler_count": 0
    }
    ans_res = client.post(f"/interview/{session_id}/answer", json=ans_payload)
    assert ans_res.status_code == 200
    eval_data = ans_res.json()
    assert eval_data["score"] >= 80.0
    assert "strengths" in eval_data

    # 4. Generate follow-up
    fu_payload = {
        "session_id": session_id,
        "question_id": q0["id"],
        "question": q0["question"],
        "answer": golden_answers["strong"]
    }
    fu_res = client.post("/interview/followup", json=fu_payload)
    assert fu_res.status_code == 200
    assert "followup_question" in fu_res.json()

    # 5. Complete session
    comp_payload = {
        "eye_contact_percent": 80.0,
        "blink_rate": 18.0,
        "pause_rate": 1.8
    }
    comp_res = client.post(f"/interview/{session_id}/complete", json=comp_payload)
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert comp_data["status"] == "completed"
    assert "readiness_score" in comp_data
    assert "subscores" in comp_data

    # 6. Retrieve report
    rep_res = client.get(f"/report/{session_id}")
    assert rep_res.status_code == 200
    rep_data = rep_res.json()
    assert rep_data["session_id"] == session_id
    assert len(rep_data["answers"]) == 1
    assert "radar_data" in rep_data

    # 7. Check progress
    prog_res = client.get("/progress")
    assert prog_res.status_code == 200
    prog_data = prog_res.json()
    assert prog_data["total_interviews"] >= 1


def test_fix_my_answer_endpoint(client):
    payload = {
        "question": "Describe a difficult bug you fixed.",
        "answer": "I worked on a slow query and helped make it faster with indexes.",
        "target_role": "Software Engineer"
    }
    res = client.post("/answer/improve", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "improved_answer" in data
    assert "star_breakdown" in data
    assert "vocabulary_suggestions" in data
    assert len(data["weaknesses"]) > 0


def test_validation_error_consistent_shape(client):
    """Validation errors must return uniform structure with error code and details."""
    # Send empty payload to endpoint expecting mandatory fields
    res = client.post("/interview/followup", json={})
    assert res.status_code == 422
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "message" in data["error"]
    assert "details" in data["error"]
    assert len(data["error"]["details"]) > 0


def test_not_found_error_consistent_shape(client):
    """404 errors must return uniform structure."""
    res = client.get("/interview/999999")
    assert res.status_code == 404
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert "message" in data["error"]


def test_empty_transcript_safe_handling(client):
    """Empty or whitespace-only transcript must not cause 500 error or division by zero."""
    # 1. Start session
    start_res = client.post("/interview/start", json={"mode": "technical", "number_of_questions": 1})
    session_id = start_res.json()["session_id"]
    q_id = start_res.json()["questions"][0]["id"]

    # 2. Submit completely empty transcript with 0 duration
    ans_res = client.post(
        f"/interview/{session_id}/answer",
        json={
            "session_id": session_id,
            "question_id": q_id,
            "transcript": "   ",
            "response_time": 0.0,
            "duration_seconds": 0.0,
            "wpm": 0.0,
            "filler_count": 0
        }
    )
    assert ans_res.status_code == 200
    data = ans_res.json()
    assert data["score"] <= 35.0
    assert "dimensions" in data


def test_resume_analyze_endpoint(client):
    """Test POST /resume/analyze with direct text payload."""
    res = client.post(
        "/resume/analyze",
        json={"text": "Dev Jane\nSkills: Python, Django, Docker, PostgreSQL\nExperience: Senior Backend Developer"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["candidate_name"] == "Dev Jane"
    assert "Python" in data["skills"]
    assert "resume_score" in data


def test_interview_legacy_routes_and_lookups(client, golden_answers):
    """
    Test legacy aliases and lookup routes:
    - POST /interview/answer
    - POST /interview/submit
    - GET /interview/result/{session_id}
    - GET /interview/latest
    - GET /interview/all
    - POST /answer/{answer_id}/improve
    """
    # 1. Start a session
    start_res = client.post("/interview/start", json={"mode": "technical", "number_of_questions": 1})
    assert start_res.status_code == 200
    session_id = start_res.json()["session_id"]
    q_id = start_res.json()["questions"][0]["id"]
    q_text = start_res.json()["questions"][0]["question"]

    # 2. Test legacy POST /interview/answer alias
    ans_res = client.post(
        "/interview/answer",
        json={
            "session_id": session_id,
            "question_id": q_id,
            "question_text": q_text,
            "transcript": golden_answers["average"],
            "response_time": 20.0,
            "wpm": 120.0,
            "filler_count": 1
        }
    )
    assert ans_res.status_code == 200
    answer_id = ans_res.json()["answer_id"]
    assert "engine_used" in ans_res.json()

    # 3. Test POST /answer/{answer_id}/improve
    improve_res = client.post(f"/answer/{answer_id}/improve", json={})
    assert improve_res.status_code == 200
    assert "improved_answer" in improve_res.json()

    # 4. Test legacy POST /interview/submit alias
    sub_res = client.post(
        "/interview/submit",
        json={
            "session_id": session_id,
            "eye_contact_percent": 85.0,
            "blink_rate": 19.0,
            "pause_rate": 2.0
        }
    )
    assert sub_res.status_code == 200

    # 5. Test GET /interview/result/{session_id}
    res_res = client.get(f"/interview/result/{session_id}")
    assert res_res.status_code == 200
    assert "final_score" in res_res.json()

    # 6. Test GET /interview/latest
    latest_res = client.get("/interview/latest")
    assert latest_res.status_code == 200
    assert latest_res.json()["session_id"] == session_id

    # 7. Test GET /interview/all
    all_res = client.get("/interview/all")
    assert all_res.status_code == 200
    assert isinstance(all_res.json(), list)
    assert len(all_res.json()) >= 1


def test_camera_off_session_complete_and_report(client, golden_answers):
    """
    Test complete camera-off path:
    - eye_contact_percent and blink_rate sent as None
    - weights re-normalized to 0.375, 0.375, 0.25, 0.0
    - report shows delivery_measured: false, delivery_score: None
    - answers in report include engine_used and prompt_version
    """
    # 1. Start session
    start_res = client.post("/interview/start", json={"mode": "technical", "number_of_questions": 1})
    session_id = start_res.json()["session_id"]
    q_id = start_res.json()["questions"][0]["id"]
    q_text = start_res.json()["questions"][0]["question"]

    # 2. Submit answer
    ans_res = client.post(
        f"/interview/{session_id}/answer",
        json={
            "session_id": session_id,
            "question_id": q_id,
            "question_text": q_text,
            "transcript": golden_answers["strong"],
            "response_time": 30.0,
            "wpm": 130.0,
            "filler_count": 0
        }
    )
    assert ans_res.status_code == 200

    # 3. Complete session with camera off (null sensors)
    comp_res = client.post(
        f"/interview/{session_id}/complete",
        json={
            "eye_contact_percent": None,
            "blink_rate": None,
            "pause_rate": 2.0
        }
    )
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert comp_data["delivery_measured"] is False
    assert comp_data["subscores"]["delivery"] is None
    assert comp_data["weights_used"] == {
        "communication": 0.375,
        "technical": 0.375,
        "delivery": 0.0,
        "resume_consistency": 0.25
    }

    # 4. Fetch report
    rep_res = client.get(f"/report/{session_id}")
    assert rep_res.status_code == 200
    rep_data = rep_res.json()
    assert rep_data["delivery_measured"] is False
    assert rep_data["subscores"]["delivery"] is None
    top_improvs = rep_data["insights"]["top_improvements"] if isinstance(rep_data["insights"], dict) else rep_data["insights"]
    assert any("not measured" in ins.lower() for ins in top_improvs)
    assert len(rep_data["answers"]) == 1
    first_ans = rep_data["answers"][0]
    assert first_ans["engine_used"] == "rubric"
    assert first_ans["prompt_version"] == "v1.0"


