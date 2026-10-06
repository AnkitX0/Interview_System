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
