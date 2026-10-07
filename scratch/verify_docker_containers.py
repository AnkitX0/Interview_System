import requests
import json
import time

BASE_API = "http://localhost:8001"
FRONTEND = "http://localhost:5173"

def run_e2e_docker_verification():
    print(f"1. Verifying Frontend at {FRONTEND}...")
    r_front = requests.get(FRONTEND)
    assert r_front.status_code == 200, f"Frontend returned {r_front.status_code}"
    assert "<!doctype html>" in r_front.text.lower(), "Frontend did not return HTML"
    print("   [PASS] Frontend is serving SPA HTML correctly.")

    print(f"2. Verifying MediaPipe Asset Delivery from Frontend Container...")
    r_media = requests.get(f"{FRONTEND}/mediapipe/face_mesh/face_mesh_solution_packed_assets.data")
    assert r_media.status_code == 200, f"MediaPipe asset returned {r_media.status_code}"
    assert len(r_media.content) > 3000000, f"MediaPipe asset size mismatch: {len(r_media.content)}"
    print(f"   [PASS] MediaPipe asset delivered ({len(r_media.content)} bytes).")

    print(f"3. Verifying Backend Root Health at {BASE_API}...")
    r_health = requests.get(f"{BASE_API}/")
    assert r_health.status_code == 200, f"Backend root returned {r_health.status_code}"
    health_data = r_health.json()
    assert health_data.get("status") == "online", f"Unexpected health status: {health_data}"
    print(f"   [PASS] Backend health: {health_data}")

    session = requests.Session()

    test_email = f"docker_user_{int(time.time())}@example.com"
    test_password = "Password123!"

    print(f"4. Testing Registration ({test_email})...")
    r_reg = session.post(
        f"{BASE_API}/auth/register",
        json={"email": test_email, "password": test_password},
        headers={"Origin": FRONTEND}
    )
    assert r_reg.status_code == 200, f"Registration failed: {r_reg.status_code} {r_reg.text}"
    user_data = r_reg.json()
    print(f"   [PASS] Registered user id {user_data.get('user', {}).get('id')}")

    print("5. Testing /auth/me cookie authentication...")
    r_me = session.get(f"{BASE_API}/auth/me", headers={"Origin": FRONTEND})
    assert r_me.status_code == 200, f"/auth/me failed: {r_me.status_code} {r_me.text}"
    print(f"   [PASS] Authenticated user email: {r_me.json().get('email')}")

    print("6. Testing Resume Upload & Analysis...")
    sample_resume = (
        "Jane Doe\n"
        "Email: jane.doe@example.com | Phone: 555-0199 | San Francisco, CA\n"
        "PROFESSIONAL SUMMARY\n"
        "Senior Backend Engineer with 5+ years building FastAPI microservices and PostgreSQL.\n"
        "TECHNICAL SKILLS\n"
        "Python, FastAPI, PostgreSQL, Redis, Docker, Kubernetes\n"
        "EXPERIENCE\n"
        "Senior Engineer - CloudTech (2021 - Present)\n"
        "- Architected high-throughput REST APIs using FastAPI and PostgreSQL.\n"
        "- Implemented Redis caching, reducing p99 latency by 45%.\n"
        "EDUCATION\n"
        "B.Tech in Computer Science, Tech University (2017 - 2021)\n"
    )
    r_resume = session.post(
        f"{BASE_API}/resume/upload",
        data={"raw_text": sample_resume},
        headers={"Origin": FRONTEND}
    )
    assert r_resume.status_code == 200, f"Resume upload failed: {r_resume.status_code} {r_resume.text}"
    resume_resp = r_resume.json()
    resume_id = resume_resp.get("id")
    print(f"   [PASS] Resume parsed & saved with resume_id: {resume_id}")

    print("7. Testing Interview Initialization (DRILL mode)...")
    r_start = session.post(
        f"{BASE_API}/interview/start",
        json={
            "role": "Backend Engineer",
            "experience_level": "Senior",
            "policy_mode": "DRILL",
            "resume_id": resume_id
        },
        headers={"Origin": FRONTEND}
    )
    assert r_start.status_code == 200, f"Interview start failed: {r_start.status_code} {r_start.text}"
    start_data = r_start.json()
    interview_session_id = start_data.get("session_id")
    questions = start_data.get("questions", [])
    assert len(questions) > 0, "No questions returned in start"
    q1 = questions[0]
    q1_text = q1.get("question") or q1.get("question_text")
    print(f"   [PASS] Session {interview_session_id} started. Q1: {q1_text[:60]}...")

    print("8. Testing Answer Submission (Question 1)...")
    ans1_payload = {
        "session_id": interview_session_id,
        "question_id": q1.get("id"),
        "question_text": q1_text,
        "transcript": "We partitioned our PostgreSQL database by tenant key and used Redis caches with a cache-aside pattern to reduce latency and protect the primary database under peak traffic.",
        "head_alignment_percent": 82.0,
        "blink_rate": 18.0,
        "duration_seconds": 25.0
    }
    r_ans1 = session.post(
        f"{BASE_API}/interview/{interview_session_id}/answer",
        json=ans1_payload,
        headers={"Origin": FRONTEND}
    )
    assert r_ans1.status_code == 200, f"Answer 1 failed: {r_ans1.status_code} {r_ans1.text}"
    ans1_resp = r_ans1.json()
    print(f"   [PASS] Answer 1 submitted. Score: {ans1_resp.get('score')}")

    print("9. Testing 'Skip / I Don't Know' on Question...")
    r_skip = session.post(
        f"{BASE_API}/interview/{interview_session_id}/skip",
        headers={"Origin": FRONTEND}
    )
    assert r_skip.status_code == 200, f"Skip failed: {r_skip.status_code} {r_skip.text}"
    skip_resp = r_skip.json()
    print(f"   [PASS] Question skipped. Skip response: done={skip_resp.get('done')}")

    next_q = skip_resp.get("question")
    if not next_q and not skip_resp.get("done"):
        r_next = session.post(f"{BASE_API}/interview/{interview_session_id}/next", headers={"Origin": FRONTEND})
        if r_next.status_code == 200:
            next_q = r_next.json().get("question")

    if next_q:
        q_text = next_q.get("question") or next_q.get("question_text")
        print(f"10. Testing Answer Submission on Question ({q_text[:50]}...)...")
        ans2_payload = {
            "session_id": interview_session_id,
            "question_id": next_q.get("id"),
            "question_text": q_text,
            "transcript": "We implemented exponential backoff with jitter and circuit breakers to prevent cascade failures when downstream microservices degrade.",
            "head_alignment_percent": 85.0,
            "blink_rate": 17.5,
            "duration_seconds": 22.0
        }
        r_ans2 = session.post(
            f"{BASE_API}/interview/{interview_session_id}/answer",
            json=ans2_payload,
            headers={"Origin": FRONTEND}
        )
        assert r_ans2.status_code == 200, f"Answer 2 failed: {r_ans2.status_code} {r_ans2.text}"
        print(f"   [PASS] Answer submitted. Score: {r_ans2.json().get('score')}")

    print("11. Testing 'End Interview' (/complete)...")
    r_comp = session.post(
        f"{BASE_API}/interview/{interview_session_id}/complete",
        headers={"Origin": FRONTEND}
    )
    assert r_comp.status_code == 200, f"Complete failed: {r_comp.status_code} {r_comp.text}"
    print(f"   [PASS] Interview completed: {r_comp.json()}")

    print("12. Fetching Report (/report/{sessionId})...")
    r_rep = session.get(
        f"{BASE_API}/report/{interview_session_id}",
        headers={"Origin": FRONTEND}
    )
    assert r_rep.status_code == 200, f"Report failed: {r_rep.status_code} {r_rep.text}"
    rep_data = r_rep.json()
    print(f"   [PASS] Report generated! Overall Readiness Score: {rep_data.get('overall_score')}")
    print(f"          Technical: {rep_data.get('technical_score')}, Delivery: {rep_data.get('delivery_score')}")
    print(f"          Questions evaluated: {len(rep_data.get('question_evaluations', []))}")

    return test_email, interview_session_id, rep_data.get('overall_score')

if __name__ == "__main__":
    email, s_id, score = run_e2e_docker_verification()
    print(f"\nALL DOCKER HTTP & WORKFLOW CHECKS PASSED SUCCESSFULLY!")
    print(f"Session ID: {s_id}, User: {email}, Score: {score}")
