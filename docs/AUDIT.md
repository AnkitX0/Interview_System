# System Audit & Spec Alignment Report (Phase 0)

**Date**: 2026-10-06  
**Auditor**: Lead Full-Stack & Applied-ML Engineer  
**Status**: Completed — Ready for User Review  

---

## 1. Executive Summary & Repository Map

The codebase represents a working college-grade prototype for an AI Interview Intelligence system. Core end-to-end flows exist and execute without crashing, but significant architectural, reliability, privacy, and ML-rigor gaps remain when measured against the **Master Product Specification**.

### Repository Structure & Entry Points

```
Interview_System/
├── backend/
│   ├── main.py                  # FastAPI entry point, CORS, router registrations
│   ├── database.py              # SQLite engine, SessionLocal, ad-hoc ALTER TABLE migration
│   ├── crud.py                  # Legacy behavioral scoring formula
│   ├── interview.db             # Active SQLite database (7 tables)
│   ├── requirements.txt         # Backend Python dependencies
│   ├── models/
│   │   ├── __init__.py          # Model exports
│   │   └── models.py            # SQLAlchemy ORM definitions (7 tables)
│   ├── routes/
│   │   ├── resume.py            # /resume/upload, /resume/analyze, /resume/{id}
│   │   ├── interview.py         # /interview/start, /answer, /followup, /complete, etc.
│   │   └── analytics.py         # /report/{session_id}, /progress, /answer/improve
│   ├── schemas/
│   │   └── schemas.py           # Pydantic request/response schemas
│   └── services/
│       ├── resume_service.py    # PDF extraction, keyword detection, audit score
│       ├── scoring_engine.py    # Deterministic rubric scoring & session readiness formula
│       ├── question_selector.py # Question Bank query with resume skill matching
│       ├── followup_generator.py# Rule-based follow-up question generator
│       ├── answer_improvement_service.py # STAR answer refactoring & vocabulary upgrades
│       ├── evaluation_engine.py # Evaluation abstraction layer
│       └── seed_questions.py    # 80-question database seeder
├── frontend/
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json             # React 19, Recharts, MediaPipe FaceMesh
│   ├── src/
│   │   ├── main.jsx             # Entry point with ReportProvider
│   │   ├── App.jsx              # Routes: /, /resume, /setup, /interview, /dashboard, /fix-answer, /progress
│   │   ├── components/
│   │   │   ├── Navbar.jsx       # Header navigation
│   │   │   └── Layout.jsx       # Global wrapper
│   │   ├── context/
│   │   │   └── ReportContext.jsx# SessionStorage-backed React Context
│   │   └── pages/
│   │       ├── Landing.jsx      # Marketing/onboarding page
│   │       ├── ResumeUpload.jsx # Resume upload, skill parsing, audit display
│   │       ├── InterviewSetup.jsx # Round configuration & hardware check
│   │       ├── Interview.jsx    # Webcam, FaceMesh, Web Speech STT, rubric feedback
│   │       ├── Dashboard.jsx    # Report page with subscores & question reviews
│   │       ├── FixAnswer.jsx    # STAR refactoring tool
│   │       └── Progress.jsx     # Longitudinal session trend chart & audit log
├── docs/
│   └── AUDIT.md                 # This document
├── README.md                    # Root project documentation
└── claud.md                     # Project Architecture & Technical Guide
```

---

## 2. Runtime Verification Results

| Target | Command | Result | Notes |
|---|---|---|---|
| **Backend Startup** | `uvicorn backend.main:app --port 8000` | **PASS (200 OK)** | Boots cleanly, connects to `interview.db`, auto-migrates missing columns, serves root endpoint. |
| **Frontend Production Build** | `npm run build` | **PASS** | Vite compiles in 1.9s. Single bundle warning (`>500kB` due to Recharts & MediaPipe chunks). |
| **Frontend Dev Server** | `npm run dev` | **PASS** | Serves on `http://localhost:5173`. |
| **End-to-End API Flow** | Custom integration runner | **PASS** | Full flow (Resume → Start → Answer → Followup → Complete → Report → Fix → Progress) returns 200 OK. |
| **Automated Test Suite** | `pytest` | **FAIL / MISSING** | `pytest` is not installed; no test directory or test files exist in the repo. |

---

## 3. Verification of Specific Suspected Issues

### Issue 1: Ambiguous "Behavioral" Dimension
- **Finding**: **CONFIRMED & INCONSISTENT**.
- **Evidence**:
  - In `backend/services/scoring_engine.py` (lines 65–78), individual answers are scored for `"star_score"` based on STAR markers (*Situation, Task, Action, Result*). For behavioral questions, `overall_score` gives 35% weight to `star_score`.
  - In `backend/routes/interview.py` (lines 208–214) and `backend/crud.py` (lines 1–13), the session-level `behavioral_score` is computed purely from physical signals:
    $$\text{behavioral\_score} = 0.40 \times \text{eye\_contact\_score} + 0.30 \times \text{blink\_score} + 0.30 \times \text{pause\_score}$$
  - In `backend/services/scoring_engine.py` (lines 147–152), the session readiness formula:
    $$\text{Final Readiness} = 0.30 \times \text{Comm} + 0.30 \times \text{Tech} + 0.20 \times \text{Behavioral} + 0.20 \times \text{Resume Consistency}$$
    uses the computer-vision/pause metric as the 20% "Behavioral" term, while calling it "Behavioral Signals" or "Behavioral Presence" in the UI.
- **Resolution Plan**:
  1. Clearly separate **Verbal/STAR Quality** from **Physical Presence/Delivery**.
  2. Rename the 20% session dimension to **Delivery & Visual Stability** (or **Behavioral Delivery**), derived purely from observable physical and cadence signals (centering, blink rate, pause rate, head stability).
  3. Keep the **STAR Score** strictly as part of the Communication/Structure evaluation for behavioral prompts, with its own dedicated named sub-score in the breakdown.

---

### Issue 2: Real LLM Path in `evaluation_engine.py`
- **Finding**: **CONFIRMED STUB / DEAD CODE**.
- **Evidence**:
  - In `backend/services/evaluation_engine.py` (lines 20–31):
    ```python
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")

    # In production/offline environments without keys, use the deterministic rubric engine
    evaluation = evaluate_rubric_for_answer(...)
    return evaluation
    ```
  - The function reads `api_key` and does nothing with it. There is no HTTP client call, no SDK invocation, no prompt, and no Pydantic schema validation for LLM responses.
- **Resolution Plan**:
  - Implement a real provider client with strict Pydantic JSON output validation, a timeout guard (e.g. 5 seconds), and automatic fallback to `evaluate_rubric_for_answer` upon failure, timeout, or missing keys.
  - Never prompt the LLM to "rate 1–10"; prompt it to extract concrete rubric evidence and observations.

---

### Issue 3: Hardcoded Paths and Configuration
- **Finding**: **CONFIRMED IN DOCS & FRONTEND**.
- **Evidence**:
  - `README.md` (lines 124, 140) and `claud.md` (lines 250, 258) hardcode `/home/ankit/Documents/Interview_System`.
  - Frontend pages (`Interview.jsx`, `Dashboard.jsx`, `ResumeUpload.jsx`, `InterviewSetup.jsx`, `FixAnswer.jsx`, `Progress.jsx`) hardcode `http://127.0.0.1:8000/`.
  - Backend code (`backend/database.py`) uses `os.path.dirname(__file__)`, which is path-agnostic.
- **Resolution Plan**:
  - Replace absolute documentation paths with relative repo-root commands (`cd frontend`, `uvicorn backend.main:app`).
  - Introduce `frontend/src/config.js` or `import.meta.env.VITE_API_URL` with a sensible fallback (`http://127.0.0.1:8000`).

---

### Issue 4: Test Coverage
- **Finding**: **CONFIRMED ZERO TEST COVERAGE**.
- **Evidence**:
  - No `tests/` directory exists.
  - No `pytest`, `unittest`, or Vitest test suites exist.
  - The previous claims of test coverage were based on ad-hoc shell commands (`python -c "import urllib..."`).
- **Resolution Plan**:
  - Install `pytest` and create `tests/` with unit tests for:
    1. Scoring engine rubric determinism (identical input produces identical score).
    2. Golden answer fixtures (Weak / Average / Strong answers ranking strictly in ascending score bands).
    3. Resume parsing (with and without `pdftotext`).
    4. Readiness formula calculations and boundary conditions.
    5. API endpoint tests using FastAPI `TestClient`.

---

### Issue 5: Camera/Mic Failure Handling & Web Speech API
- **Finding**: **CONFIRMED PARTIAL & FAKES DATA ON CAMERA OFF**.
- **Evidence**:
  - **Graceful UI Fallback**: In `InterviewSetup.jsx` and `Interview.jsx`, camera permission denial shows a warning and displays a "Webcam Inactive" placeholder instead of crashing.
  - **Browser Fragility**: Web Speech API (`window.webkitSpeechRecognition`) is Chrome/Chromium/Edge-specific. On Firefox or unsupported browsers, clicking speech-to-text triggers an intrusive `alert()`.
  - **Data Integrity Violation (Fake Data)**: In `frontend/src/pages/Interview.jsx` (lines 16, 269–283), when the camera is never enabled, `eyeContactPercent` defaults to `75.0` and `blinkCount` to `0`. On interview completion, it posts:
    `{ eye_contact_percent: 75.0, blink_rate: 18.0, pause_rate: 2.0 }`
    The backend then scores this as real behavioral data! This violates the Hard Rule: *"No fake AI. Honest language."*
- **Resolution Plan**:
  - When the camera is off or permission is denied, pass `eye_contact_percent: null`, `blink_rate: null`.
  - The backend scoring formula must adapt gracefully when physical signals are unmeasured (re-normalizing weights across Communication, Technical, and Resume Consistency, or displaying "Not Measured").
  - Replace `alert()` with an inline banner explaining that Web Speech API is browser-dependent and providing a clean microphone/text toggle.

---

### Issue 6: Eye-Contact Heuristic
- **Finding**: **CONFIRMED OVERCLAIMED / COARSE PROXY**.
- **Evidence**:
  - In `frontend/src/pages/Interview.jsx` (lines 132–143):
    ```javascript
    const nose = landmarks[1];
    const noseX = nose.x * canvas.width;
    const centerX = canvas.width / 2;
    if (Math.abs(noseX - centerX) < 65) {
      setEyeContact(true);
    }
    ```
  - This checks only whether the **nose tip X-coordinate** is within 65 pixels of the video horizontal center. It does not measure gaze, pupil orientation, or vertical head tilt.
  - In `Dashboard.jsx`, this was presented as *"Visual Center / Eye Contact: 78%"*.
- **Resolution Plan**:
  - Relabel all UI references from "Eye Contact" to **"Visual Centering Proxy"** or **"Head Alignment Stability"**.
  - Add explicit observable language: *"Head positioned within central visual frame for X% of session; not an assessment of confidence or eye gaze."*

---

### Issue 7: Pressure Mode Reality Check
- **Finding**: **CONFIRMED LABEL ONLY / NO BEHAVIORAL DIFFERENCE**.
- **Evidence**:
  - In `backend/services/question_selector.py` (lines 35–36), selecting "Pressure Mode" filters `QuestionBank` for questions categorized as `"Pressure"` (e.g. *"Your project failed in production. What do you do?"*).
  - In `frontend/src/pages/Interview.jsx`, the timer is still 90 seconds (identical to practice), the follow-up logic is identical, and the scoring rubric is identical.
  - There are no shorter time limits, no challenge interjections, no incident escalations, and no psychological explanation.
- **Resolution Plan**:
  - Implement real, safe pressure behavior:
    1. Reduced response countdown (e.g., 45s instead of 90s).
    2. Challenge follow-ups (e.g., *"How did you validate that SLA?", "What would you do if the rollback failed?"*).
    3. Clear pre-session disclaimer explaining that pressure mode simulates high-urgency incident response, not personal evaluation.

---

## 4. Master Product Specification Alignment Matrix

| Spec Feature | Status | Evidence / Affected Files |
|---|---|---|
| **Resume PDF & Text Extraction** | **IMPLEMENTED** | `backend/services/resume_service.py:34-88` (`pdftotext` + regex fallback) |
| **Categorized Skill Extraction** | **IMPLEMENTED** | `backend/services/resume_service.py:91-118` (5 competency buckets) |
| **Weak Phrasing & Audit Scorer** | **IMPLEMENTED** | `backend/services/resume_service.py:145-175` (vague regex patterns) |
| **Project & Bullet Decomposition** | **PLANNED** | Currently extracts raw experience lines; does not parse projects into claim ladders |
| **`resume_skills` & `resume_flags` Tables** | **MISSING** | `backend/models/models.py` has flat JSON fields on `Resume` table |
| **Role Fit Score & Risk Areas** | **MISSING** | No role fit calculation against target job title |
| **Claim-Probe Ladder** | **MISSING** | Questions are chosen by category, not by traversing specific resume claims |
| **Bluff / Verification Risk Indicator** | **MISSING** | No dedicated verification-risk score or buzzword density detector |
| **Resume-Aware Question Bank (80+)** | **IMPLEMENTED** | `backend/services/seed_questions.py`, `backend/services/question_selector.py` |
| **Adaptive Follow-up Generator** | **PARTIALLY IMPLEMENTED** | `backend/services/followup_generator.py` (has 4 static rules, not dynamic ladder) |
| **Safe Pressure Mode** | **BROKEN / LABEL ONLY** | `frontend/src/pages/Interview.jsx` has no behavioral difference for pressure mode |
| **Rubric Scoring (5 Dimensions)** | **IMPLEMENTED** | `backend/services/scoring_engine.py` (Structure, Tech, Reasoning, STAR, Consistency) |
| **Explainable Evidence per Dimension** | **PARTIALLY IMPLEMENTED** | Returns strengths/weaknesses strings, not structured `{score, evidence, explanation, action}` |
| **Deterministic Offline Path** | **IMPLEMENTED** | 100% functional without external network access |
| **Production LLM Path (Gemini/OpenAI)** | **BROKEN / STUBBED** | `backend/services/evaluation_engine.py:20` reads env vars but never calls LLM |
| **Session Readiness Formula** | **IMPLEMENTED** | 0.30 Comm + 0.30 Tech + 0.20 Behavioral + 0.20 Resume Consistency |
| **Ambiguous Behavioral Definition** | **BROKEN** | Conflates webcam centering with STAR verbal scores |
| **Web Speech API Speech-to-Text** | **IMPLEMENTED** | `frontend/src/pages/Interview.jsx:62-106` |
| **Per-Answer Voice Metrics Table** | **MISSING** | WPM and fillers are stored flat on `InterviewAnswer`; no pause/silence/TTR metrics |
| **MediaPipe FaceMesh Diagnostics** | **PARTIALLY IMPLEMENTED** | Nose X-centering proxy; EAR blink counter; imputes fake data when camera is off |
| **Executive Performance Report** | **IMPLEMENTED** | `frontend/src/pages/Dashboard.jsx`, `backend/routes/analytics.py` |
| **Segmented Interview Timeline** | **MISSING** | Report has aggregate and per-answer reviews, but no time-sliced performance timeline |
| **Fix My Answer (STAR Coach)** | **IMPLEMENTED** | `backend/services/answer_improvement_service.py`, `frontend/src/pages/FixAnswer.jsx` |
| **Persist `answer_improvements`** | **MISSING** | Fix My Answer results are ephemeral and not saved in database |
| **Technical Concept→Tradeoff Pattern** | **MISSING** | Fix My Answer only uses STAR; lacks technical architectural pattern |
| **Progress History Dashboard** | **IMPLEMENTED** | `frontend/src/pages/Progress.jsx` (Recharts trend + audit log table) |
| **Improvement Velocity & Prediction** | **MISSING** | No velocity points/session; no probabilistic readiness prediction for 4+ sessions |
| **Authentication & Multi-User Scoping**| **MISSING** | No user table, passwords, or JWT auth; all sessions are unauthenticated and public |
| **Consent & Data Deletion** | **MISSING** | No explicit camera/mic consent modal; no "Delete My Session / Account" buttons |
| **Centralized Config & Constants** | **MISSING** | Scoring weights, filler words, and thresholds are hardcoded magic numbers |
| **Versioned Migrations (Alembic)** | **MISSING** | Relies on ad-hoc SQLite `ALTER TABLE` script in `database.py` |
| **Automated Test Suite** | **MISSING** | Zero test files exist |

---

## 5. Proposed Phase-by-Phase Implementation Plan

### Phase 1: Reliability, Testing & Data Correctness (Immediate Next Step)
1. **Pytest Test Suite**:
   - Install `pytest` in `venv`.
   - Create `tests/test_scoring.py`: unit tests for rubric formulas, golden answer fixtures (weak/average/strong scoring in strictly ascending bands), and determinism verification.
   - Create `tests/test_resume.py`: tests for resume parser with PDF and plain text, checking skill extraction and clarity audit.
   - Create `tests/test_api.py`: FastAPI endpoint tests for every route using `TestClient`.
2. **Scoring Transparency & Evidence Contracts**:
   - Refactor `scoring_engine.py` to return `{score, evidence: [...], explanation, recommended_action}` for every dimension.
   - Ensure evidence cites observable facts (*"0 metrics detected"*, *"14 filler words"*, *"tradeoff keywords: 0"*).
   - Update `Dashboard.jsx` to render this evidence cleanly.
3. **Behavioral Dimension Disambiguation**:
   - Rename session dimension to **Delivery & Visual Stability** (CV + pause pacing).
   - Keep **STAR Quality** strictly under Communication/Structure, with its own dedicated breakdown badge.
   - **Fix Fake Data Bug**: When camera is disabled, pass `null` for visual metrics and adjust the session formula so unmeasured sensors do not fabricate data.
4. **Centralized Configuration Module**:
   - Create `backend/config.py` declaring `SCORING_WEIGHTS`, `FILLER_WORDS`, `TARGET_THRESHOLDS`, and note in docstrings that weights are initial assumptions.
5. **Real LLM Integration & Pydantic Validation**:
   - Implement actual Gemini/OpenAI caller in `evaluation_engine.py` with structured Pydantic response parsing, 5-second timeout, and clean fallback to deterministic rubric.

### Phase 2: MVP Gaps — Auth, User Scoping, Voice Metrics & Privacy
1. **Authentication & Multi-Tenancy**:
   - Add `User` and `UserProfile` tables with password hashing (`bcrypt` or `argon2`) and JWT authentication.
   - Scope all resumes, sessions, reports, and progress to `user_id`. Add authorization guards on all routes.
2. **Per-Answer Voice Metrics Table**:
   - Add `voice_metrics` table linked to `interview_answers`.
   - Calculate pause counts, longest pause, estimated vocabulary diversity (type-token ratio with length guard), WPM, and fillers.
3. **Privacy, Consent & Deletion**:
   - Add an explicit consent screen before camera/mic activation.
   - Add "Delete Session" and "Delete Account" endpoints and UI buttons.
   - Explicitly note in UI: *"Video is processed locally in your browser; raw video is never recorded or uploaded to the server."*

### Phase 3: Intelligence Layer — Claim-Probe Ladder, Verification Risk & Safe Pressure
1. **Resume Intelligence Upgrade**:
   - Extract projects, achievements, and quantified bullets into structured tables.
   - Add `resume_flags` table (vague, mismatch, missing metric).
   - Calculate Role Fit Score against target role.
2. **Claim-Probe Ladder & Adaptive Questioning**:
   - Associate resume claims with questions and traverse difficulty ladders based on previous answer evaluations.
   - Compute Bluff / Verification Risk score from observable signals (generic buzzwords, contradictions, evasion of specifics).
3. **Safe Pressure Mode**:
   - Implement shorter timers (45s), challenging follow-up probes, and a clear pre-session explanation.

### Phase 4: Report Timeline, Fix My Answer v2 & Longitudinal Growth
1. **Segmented Interview Timeline**:
   - Visualize metrics (WPM, fillers, structure, visual centering) chronologically across the interview.
2. **Fix My Answer v2**:
   - Add technical pattern (*Concept → Why → How → Example → Tradeoff*) alongside STAR.
   - Persist improved answers in `answer_improvements` table.
3. **Progress v2 & Velocity**:
   - Add Improvement Velocity metric and recurring weakness tracking across sessions.
   - Add probabilistic readiness estimate for candidates with 4+ sessions.

### Phase 5: UX & Product Polish
1. **Dashboard & Live Screen Refinements**:
   - Make mid-interview WPM/filler stats optional to avoid candidate distraction.
   - Ensure clean keyboard accessibility, contrast, and responsive layout.
2. **Copywriting Audit**:
   - Review all text to eliminate any overclaims or pseudo-scientific emotion labels.

---

## 6. Action Items & Approval Request

1. **Master Product Specification Document**:
   - The user prompt referenced the *Master Product Specification* as the target document. While key requirements, rules, and phases were quoted in the prompt, please provide the full text or file if additional unquoted sections exist.
2. **Approval Request**:
   - Please review this audit document ([`docs/AUDIT.md`](file:///home/ankit/Documents/Interview_System/docs/AUDIT.md)) and the proposed implementation plan.
   - Once you approve, I will immediately begin **Phase 1: Reliability, Testing & Data Correctness** (writing pytest tests, disambiguating behavioral metrics, fixing the camera-off fake data bug, implementing transparent evidence scoring, and wiring the real LLM path).

