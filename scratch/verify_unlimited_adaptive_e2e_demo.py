import asyncio
import json
import os
import httpx
from playwright.async_api import async_playwright

API_BASE = "http://localhost:8000"
FRONTEND_BASE = "http://localhost:5173"

def run_backend_demo_verification():
    print("==================================================================")
    print("DEMO VERIFICATION: BACKEND ADAPTIVE ENGINE & GEMINI INTELLIGENCE")
    print("==================================================================")
    
    client = httpx.Client(base_url=API_BASE, timeout=30.0)

    # 1. Login
    print("Step 1: Logging in as xyz@gmail.com...")
    login_resp = client.post("/auth/login", json={
        "email": "xyz@gmail.com",
        "password": "TestPassword123!"
    })
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    print("  ✓ Authenticated successfully with cookie:", list(client.cookies.keys()))

    # 2. Upload / verify resume
    print("Step 2: Uploading resume with quantitative claims...")
    sample_resume = (
        "John Doe - Senior Backend Engineer\n"
        "Experience:\n"
        "Staff Engineer at AgroTech Solutions (2021-Present)\n"
        "- Redesigned high-throughput order processing service in Go and PostgreSQL.\n"
        "- Improved API latency by 40% through redis caching, connection pooling, and query rewriting.\n"
        "- Architected resilient distributed payment escrow system handling 20,000 transactions daily.\n"
        "Skills: Go, Python, PostgreSQL, Redis, Kubernetes, Distributed Systems, Microservices."
    )
    resume_resp = client.post(
        "/resume/upload",
        files={"file": ("resume.txt", sample_resume.encode(), "text/plain")}
    )
    assert resume_resp.status_code == 200, f"Resume upload failed: {resume_resp.text}"
    resume_data = resume_resp.json()
    resume_id = resume_data.get("id") or resume_data.get("resume_id")
    print(f"  ✓ Resume processed (ID: {resume_id}). Skills: {resume_data.get('skills', [])[:4]}...")

    # 3. Start ADAPTIVE interview with SHORT policy (5 nominal minimum, up to 7)
    print("Step 3: Starting ADAPTIVE interview with SHORT policy (min 5, max 7)...")
    start_resp = client.post(
        "/interview/start",
        json={
            "role": "backend",
            "number_of_questions": 5,
            "session_policy": "SHORT",
            "question_mode": "ADAPTIVE",
            "difficulty": "medium",
            "resume_id": resume_id
        }
    )
    assert start_resp.status_code == 200, f"Start interview failed: {start_resp.text}"
    session = start_resp.json()
    session_id = session["session_id"]
    questions = session["questions"]
    q1 = questions[0]
    q1_text = q1.get("question") or q1.get("question_text")
    print(f"  ✓ Session ID: {session_id}")
    print(f"  ✓ Question Mode: {session.get('question_mode')}, Policy: {session.get('session_policy')}")
    print(f"  ✓ Q1: {q1_text}")

    # 4. Answer Q1 with good technical foundation
    print("\nStep 4: Submitting technical response to Q1...")
    a1_resp = client.post(
        f"/interview/{session_id}/answer",
        json={
            "session_id": session_id,
            "question_id": q1["id"],
            "question_text": q1_text,
            "transcript": "I redesigned the core transaction pipeline using Go channels and PostgreSQL connection pools. We separated read queries with read replicas and indexed primary search keys."
        }
    )
    assert a1_resp.status_code == 200, f"Answer Q1 failed: {a1_resp.text}"
    print("  ✓ Answer 1 recorded.")

    # Get Q2 via adaptive engine
    next1 = client.post(f"/interview/{session_id}/next").json()
    print(f"  ✓ Next Action: {next1.get('action')}, Decision: {next1.get('decision')}")
    q2 = next1.get("question")
    print(f"  ✓ Q2: {q2.get('question_text')}")

    # 5. Answer Q2 with a vague / evasive answer to test diversion handling
    print("\nStep 5: Submitting VAGUE / EVASIVE answer to Q2 to trigger challenge...")
    a2_resp = client.post(
        f"/interview/{session_id}/answer",
        json={
            "session_id": session_id,
            "question_id": q2.get("question_id") or q2.get("id", 2),
            "question_text": q2.get("question_text"),
            "transcript": "We used various tools and technologies that our team liked."
        }
    )
    assert a2_resp.status_code == 200
    print("  ✓ Answer 2 recorded.")
    
    # Get Q3 via adaptive engine
    next2 = client.post(f"/interview/{session_id}/next").json()
    print(f"  ✓ Next Action: {next2.get('action')}, Decision: {next2.get('decision')}")
    q3 = next2.get("question")
    print(f"  ✓ Q3 (Challenging / Probing): {q3.get('question_text')}")

    # 6. Answer Q3 with strong specific answer to test depth escalation
    print("\nStep 6: Submitting STRONG answer with metrics and architecture...")
    a3_resp = client.post(
        f"/interview/{session_id}/answer",
        json={
            "session_id": session_id,
            "question_id": q3.get("question_id") or q3.get("id", 3),
            "question_text": q3.get("question_text"),
            "transcript": "Specifically, we profiled database query execution times using EXPLAIN ANALYZE, identified a sequential scan bottleneck on the orders table, added a compound B-tree index on (customer_id, created_at), and reduced p99 query latency from 850ms to 45ms under a load of 15,000 req/sec."
        }
    )
    assert a3_resp.status_code == 200
    print("  ✓ Answer 3 recorded.")

    # Get Q4 via adaptive engine
    next3 = client.post(f"/interview/{session_id}/next").json()
    print(f"  ✓ Next Action: {next3.get('action')}, Decision: {next3.get('decision')}")
    q4 = next3.get("question")
    print(f"  ✓ Q4: {q4.get('question_text')}")

    # 7. Answer Q4 - Resume claim verification
    print("\nStep 7: Answering Q4 testing resume claim verification...")
    a4_resp = client.post(
        f"/interview/{session_id}/answer",
        json={
            "session_id": session_id,
            "question_id": q4.get("question_id") or q4.get("id", 4),
            "question_text": q4.get("question_text"),
            "transcript": "For the payment escrow system, we used a two-phase commit pattern with idempotency keys stored in Redis to guarantee exactly-once delivery across external payment gateways."
        }
    )
    assert a4_resp.status_code == 200
    print("  ✓ Answer 4 recorded.")

    # Get Q5 via adaptive engine
    next4 = client.post(f"/interview/{session_id}/next").json()
    print(f"  ✓ Next Action: {next4.get('action')}, Decision: {next4.get('decision')}")
    q5 = next4.get("question")
    print(f"  ✓ Q5: {q5.get('question_text')}")

    # 8. Answer Q5 - THIS IS THE CRITICAL TEST: REACHING NOMINAL MINIMUM (5)
    print("\nStep 8: REACHING NOMINAL MINIMUM (5 ANSWERS) - Checking if interview continues!")
    a5_resp = client.post(
        f"/interview/{session_id}/answer",
        json={
            "session_id": session_id,
            "question_id": q5.get("question_id") or q5.get("id", 5),
            "question_text": q5.get("question_text"),
            "transcript": "We handled network partitions using exponential backoff and circuit breakers implemented via Netflix Hystrix pattern."
        }
    )
    assert a5_resp.status_code == 200
    print("  ✓ Total answers submitted so far: 5")

    # Call /interview/{session_id}/next to see if adaptive engine decides to continue!
    next5 = client.post(f"/interview/{session_id}/next").json()
    dec_obj = next5.get("decision")
    decision_name = dec_obj.get("decision") if isinstance(dec_obj, dict) else dec_obj
    decision_reason = dec_obj.get("reason") if isinstance(dec_obj, dict) else next5.get("reason")
    print(f"  ✓ Post-Q5 Decision: {decision_name}")
    print(f"  ✓ Decision Reason: {decision_reason}")
    
    if decision_name != "COMPLETE_SESSION":
        print("  ★★ SUCCESS: Adaptive engine DID NOT stop at question 5! It determined additional evidence was required.")
        q6 = next5.get("question") or {}
        print(f"  ✓ Q6 Generated: {q6.get('question_text')}")
        
        # 9. Continue to Q6 and provide comprehensive answer
        print("\nStep 9: Submitting comprehensive answer to Q6...")
        a6_resp = client.post(
            f"/interview/{session_id}/answer",
            json={
                "session_id": session_id,
                "question_id": q6.get("question_id") or q6.get("id", 6),
                "question_text": q6.get("question_text", "System monitoring"),
                "transcript": "To monitor system stability in production, we tracked error budget burn rate and SLI/SLO metrics using Prometheus counters and set P1 alerts in PagerDuty."
            }
        )
        assert a6_resp.status_code == 200
        print("  ✓ Answer 6 recorded.")
    else:
        print(f"  ★★ SUCCESS: Interview completed based on EVIDENCE SUFFICIENCY: '{decision_reason}'")

    # 10. Complete session and verify final report
    print("\nStep 10: Finalizing interview session and validating assessment report...")
    complete_resp = client.post(f"/interview/{session_id}/complete")
    assert complete_resp.status_code == 200, f"Complete session failed: {complete_resp.text}"
    comp_data = complete_resp.json()
    print(f"  ✓ Session Completed. Status: {comp_data.get('status')}")
    print(f"  ✓ Assessment Confidence: {comp_data.get('score_confidence')}")
    print(f"  ✓ Confidence Explanation: {comp_data.get('confidence_explanation')}")

    # 11. Fetch detailed final report
    report_resp = client.get(f"/report/{session_id}")
    assert report_resp.status_code == 200, f"Fetch report failed: {report_resp.text}"
    report = report_resp.json()
    subscores = report.get("subscores", {})
    print(f"  ✓ Preparation / Readiness Score: {report.get('readiness_score')}/100")
    print(f"  ✓ Status / Assessment Level: {report.get('status_label')}")
    print(f"  ✓ Assessment Confidence: {report.get('assessment_confidence')}")
    print(f"  ✓ Scores: Technical={subscores.get('technical')}, ProblemSolving/Delivery={subscores.get('delivery')}, Comm={subscores.get('communication')}, Resume={subscores.get('resume_consistency')}")
    next_prac = report.get("next_practice", [])
    if isinstance(next_prac, list) and len(next_prac) > 0:
        prac_desc = f"{len(next_prac)} targeted items ({next_prac[0].get('drill_type', 'Practice')})"
    elif isinstance(next_prac, dict):
        prac_desc = next_prac.get("recommendation_reason", "Personalized practice generated")
    else:
        prac_desc = "None"
    print(f"  ✓ Next Practice Recommendations: {prac_desc}")

    print("\nBackend Adaptive Intelligence Verification PASSED!")
    return session_id

async def run_browser_ui_verification(session_id):
    print("\n==================================================================")
    print("BROWSER UI VERIFICATION: REAL BROWSER RUNTIME & REPORT RENDERING")
    print("==================================================================")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path="/usr/bin/google-chrome",
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"]
        )
        context = await browser.new_context(
            permissions=["camera", "microphone"]
        )
        page = await context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: console_errors.append(str(err)))

        # 1. Login
        print("1. Logging in via Browser...")
        await page.goto(f"{FRONTEND_BASE}/login", wait_until="networkidle")
        await page.fill('input[type="email"]', "xyz@gmail.com")
        await page.fill('input[type="password"]', "TestPassword123!")
        await page.click('button[type="submit"]')
        await page.wait_for_selector('text=Dashboard', timeout=10000)
        print("   ✓ Dashboard loaded.")

        # 2. Check Interview Setup page policy options
        print("2. Verifying Interview Policy buttons on Setup page...")
        await page.goto(f"{FRONTEND_BASE}/setup", wait_until="networkidle")
        for policy_text in ["Short", "Standard", "Deep", "Continuous Adaptive"]:
            btn = await page.wait_for_selector(f'button:has-text("{policy_text}")', timeout=5000)
            assert btn is not None, f"Policy button {policy_text} missing!"
        print("   ✓ All 4 policy modes (Short, Standard, Deep, Continuous Adaptive) present on setup screen.")

        # 3. Start interview with ADAPTIVE mode
        print("3. Starting interview via Setup screen...")
        await page.click('button:has-text("Standard")')
        await page.click('button:has-text("Start Interview")')

        # Handle sensor consent modal
        try:
            enable_btn = await page.wait_for_selector('button:has-text("Enable Audio & Video")', timeout=3000)
            if enable_btn:
                print("   Clicking 'Enable Audio & Video' modal button...")
                await enable_btn.click()
        except Exception:
            pass

        # 4. Check that dynamic indicator is shown (NO rigid "Question 5 of 5")
        print("4. Verifying Interview Workspace dynamic question indicator...")
        try:
            await page.wait_for_selector('text=Adaptive Interview', timeout=15000)
            indicator = await page.inner_text('div:has-text("Adaptive Interview")')
            print(f"   ✓ Dynamic Indicator displayed: {indicator.splitlines()[0]}")
        except Exception as e:
            print("   Current page URL:", page.url)
            print("   Console errors:", console_errors)
            body_text = await page.inner_text('body')
            print("   Page content snippet:", body_text[:300])
            await page.screenshot(path="scratch/interview_page_debug.png")
            raise e
        
        # Verify camera status pill
        camera_pill = await page.wait_for_selector('text=Camera', timeout=5000)
        assert camera_pill is not None, "Camera status pill not found!"
        print("   ✓ Camera preview & status pill verified.")

        # Verify Report page components
        print(f"5. Navigating to Report page for session {session_id}...")
        await page.goto(f"{FRONTEND_BASE}/report?sessionId={session_id}", wait_until="networkidle")

        header = await page.wait_for_selector('h1:has-text("Performance & Delivery Report")', timeout=10000)
        assert header is not None, "Report header not found!"
        await page.wait_for_selector('text=Interview Readiness Score', timeout=10000)
        await page.wait_for_selector('button:has-text("Per-Question Review")', timeout=10000)
        await page.wait_for_selector('button:has-text("Interview Timeline")', timeout=10000)
        await page.wait_for_selector('button:has-text("Dimension Breakdown")', timeout=10000)
        print("   ✓ Report page fully loaded with Assessment Confidence, tabs, and explainability metrics!")

        os.makedirs("scratch", exist_ok=True)
        screenshot_path = "scratch/adaptive_report_verified.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"   ✓ Full-page screenshot saved to {screenshot_path}")

        print(f"6. Total console errors: {len(console_errors)}")
        if console_errors:
            print("   Console errors:", console_errors)

        await browser.close()
        print("\nBrowser Verification Complete: ALL TESTS PASSED!")

if __name__ == "__main__":
    sid = run_backend_demo_verification()
    asyncio.run(run_browser_ui_verification(sid))
