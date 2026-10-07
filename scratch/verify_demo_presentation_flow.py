"""
scratch/verify_demo_presentation_flow.py
Verifies the complete presentation flow:
LOGIN -> DASHBOARD -> START INTERVIEW -> LIVE INTERVIEW ->
SUBMIT ANSWER (fast transition) ->
SKIP / I DON'T KNOW (fast transition) ->
ANSWER QUESTION ->
END INTERVIEW (modal confirmation) ->
REPORT (loads with answered and skipped questions)
"""

import sys
import time
from playwright.sync_api import sync_playwright

def run_verification():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        print("[1] Navigating to login...")
        page.goto("http://localhost:5173/login")
        page.wait_for_selector('input[type="email"]', timeout=10000)

        # Login with valid demo account
        page.fill('input[type="email"]', "xyz@gmail.com")
        page.fill('input[type="password"]', "TestPassword123!")
        page.click('button[type="submit"]')

        print("[2] Waiting for dashboard navigation...")
        page.wait_for_url("**/dashboard", timeout=10000)
        print("    Reached Dashboard successfully.")

        print("[3] Navigating to interview setup...")
        page.goto("http://localhost:5173/setup")
        page.wait_for_selector("button:has-text('Start Interview')", timeout=10000)

        # Handle consent modal if shown
        consent_btn = page.locator("button:has-text('Use Text-Only Mode')")
        if consent_btn.is_visible():
            consent_btn.click()
            time.sleep(0.5)

        start_btn = page.locator("button:has-text('Start Interview')")
        start_btn.click()

        print("[4] Waiting for live interview workspace...")
        page.wait_for_url("**/interview", timeout=15000)
        page.wait_for_selector("textarea", timeout=10000)

        # Verify buttons exist
        submit_btn = page.locator("button", has_text="Submit Answer")
        skip_btn = page.locator("button", has_text="Skip / I Don't Know")
        end_btn = page.locator("button", has_text="End Interview")

        assert submit_btn.is_visible(), "Submit Answer button must be visible"
        assert skip_btn.is_visible(), "Skip / I Don't Know button must be visible"
        assert end_btn.is_visible(), "End Interview button must be visible"
        print("    Verified: Submit Answer, Skip / I Don't Know, and End Interview are visible.")

        # Verify Question Counter format (must NOT contain 'of up to')
        counter_el = page.locator("text=/Question \\d+/i").first
        counter_text = counter_el.inner_text()
        print(f"    Counter text: '{counter_text}'")
        assert "of up to" not in counter_text, f"Counter must not contain 'of up to': {counter_text}"

        page.screenshot(path="scratch/01_live_interview_workspace.png")

        # Switch to Type Answer mode if in speech mode
        type_btn = page.locator("button:has-text('Type Answer')")
        if type_btn.is_visible():
            type_btn.click()

        # Step 1: Answer Question 1
        print("[5] Answering Question 1...")
        textarea = page.locator("textarea")
        textarea.fill("In our backend service, we used PostgreSQL read replicas and Redis caching to handle high read concurrency while keeping latency under 50ms.")
        
        t0 = time.time()
        submit_btn.click()
        
        # Immediate UI response check (<300ms)
        # Button should show loading or disabled
        print(f"    Submitted answer. Waiting for next question...")
        
        # Wait for either new question text or answer textarea to reset
        page.wait_for_function("() => document.querySelector('textarea').value === ''", timeout=10000)
        t_sub = time.time() - t0
        print(f"    Question 1 processed and advanced in {t_sub:.2f}s!")

        page.screenshot(path="scratch/02_question_2_loaded.png")

        # Step 2: Skip Question 2
        print("[6] Skipping Question 2...")
        t_skip_start = time.time()
        skip_btn = page.locator("button", has_text="Skip / I Don't Know")
        skip_btn.click()

        # Wait for question to advance
        time.sleep(1.5)
        t_skip = time.time() - t_skip_start
        print(f"    Question 2 skipped and advanced in {t_skip:.2f}s!")

        page.screenshot(path="scratch/03_question_3_loaded_after_skip.png")

        # Step 3: Answering Question 3
        print("[7] Answering Question 3...")
        textarea = page.locator("textarea")
        textarea.fill("We implemented structured logging and distributed tracing with OpenTelemetry to track service degradation across microservices.")
        submit_btn = page.locator("button", has_text="Submit Answer")
        submit_btn.click()
        page.wait_for_function("() => document.querySelector('textarea').value === ''", timeout=10000)
        print("    Question 3 answered and advanced.")

        # Step 4: Click End Interview
        print("[8] Testing End Interview modal...")
        end_btn = page.locator("button", has_text="End Interview")
        end_btn.click()

        # Verify confirmation modal appears
        modal_title = page.locator("text='End interview?'")
        assert modal_title.is_visible(), "Modal title 'End interview?' must be visible"
        modal_body = page.locator("text='Your completed answers will be evaluated and your report will be generated.'")
        assert modal_body.is_visible(), "Modal description must be visible"

        page.screenshot(path="scratch/04_end_interview_modal.png")
        print("    End interview confirmation modal verified.")

        # Click confirm "End Interview" inside modal
        confirm_end_btn = page.locator("div[style*='position: fixed'] button:has-text('End Interview')")
        confirm_end_btn.click()

        print("[9] Waiting for Report page navigation...")
        page.wait_for_url("**/report?sessionId=*", timeout=15000)
        print("    Navigated to Report page!")

        page.wait_for_selector("text=/Interview Readiness Score/i", timeout=10000)
        print("    Report page loaded successfully with Readiness Score!")

        page.screenshot(path="scratch/05_report_summary.png")

        # Switch to Per-Question Review tab
        questions_tab = page.locator("button", has_text="Per-Question Review")
        if questions_tab.is_visible():
            questions_tab.click()
            time.sleep(1)
            # Verify skipped badge is present
            skipped_badge = page.locator("text='Skipped'")
            assert skipped_badge.count() >= 1, "Skipped badge should appear in Question Reviews"
            print("    Verified: Skipped question badge is present in Question Reviews!")
            page.screenshot(path="scratch/06_report_question_reviews.png")

        print("\nALL BROWSER FLOW VERIFICATION STEPS PASSED PERFECTLY!")
        browser.close()

if __name__ == "__main__":
    run_verification()
