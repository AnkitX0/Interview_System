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
  - `README.md` and `docs/ARCHITECTURE.md` previously contained hardcoded absolute user environment paths.
  - Frontend pages (`Interview.jsx`, `Dashboard.jsx`, `ResumeUpload.jsx`, `InterviewSetup.jsx`, `FixAnswer.jsx`, `Progress.jsx`) hardcoded `http://127.0.0.1:8000/`.
  - Backend code (`backend/database.py`) uses `os.path.dirname(__file__)`, which is path-agnostic.
- **Resolution Plan (FIXED in Commit 2e24a68)**:
  - Replaced absolute documentation paths with relative repo-root commands (`cd frontend`, `uvicorn backend.main:app`).
  - Introduced `frontend/src/config.js` with `import.meta.env.VITE_API_URL` and `http://127.0.0.1:8000` fallback, replacing all hardcoded URLs across all frontend pages. Add `frontend/.env.example`.

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
| **Explainable Evidence per Dimension** | **FIXED** (`ac99099`) | Strictly typed `{score, evidence, explanation, recommended_action}` returned for each dimension |
| **Deterministic Offline Path** | **IMPLEMENTED** | 100% functional without external network access |
| **Production LLM Path (Gemini/OpenAI)** | **FIXED** (`86727ad`) | Guarded Gemini/OpenAI caller with timeout, retries, grounding check, SHA-256 cache, and deterministic fallback |
| **Session Readiness Formula** | **FIXED** (`81c52b6`) | Dynamically re-normalizes weights proportionally when visual sensors are unmeasured (0.375, 0.375, 0.25, 0.0); records weights_used |
| **Ambiguous Behavioral Definition** | **FIXED** (`81c52b6`) | Renamed to "Delivery & Visual Stability" (proxy for centering/pacing). STAR moved strictly under Communication/Structure |
| **Web Speech API Speech-to-Text** | **FIXED** (`2e24a68`) | Inline non-blocking status/error banners replacing alerts; clear `🎙️ Speak Answer` / `⌨️ Type Answer` toggle |
| **Per-Answer Voice Metrics Table** | **MISSING** | WPM and fillers are stored flat on `InterviewAnswer`; no pause/silence/TTR metrics (Phase 2) |
| **MediaPipe FaceMesh Diagnostics** | **FIXED** (`81c52b6`) | Nullable sensor columns (`eye_contact_percent`, `blink_rate`); camera-off sends `null`, never fake/imputed data |
| **Executive Performance Report** | **FIXED** (`ac99099`, `81c52b6`) | Displays observable evidence per dimension; shows "Not measured: camera was off" with re-normalized weights note |
| **Segmented Interview Timeline** | **MISSING** | Report has aggregate and per-answer reviews, but no time-sliced performance timeline |
| **Fix My Answer (STAR Coach)** | **IMPLEMENTED** | `backend/services/answer_improvement_service.py`, `frontend/src/pages/FixAnswer.jsx` |
| **Persist `answer_improvements`** | **MISSING** | Fix My Answer results are ephemeral and not saved in database (Phase 4) |
| **Technical Concept→Tradeoff Pattern** | **MISSING** | Fix My Answer only uses STAR; lacks technical architectural pattern (Phase 4) |
| **Progress History Dashboard** | **IMPLEMENTED** | `frontend/src/pages/Progress.jsx` (Recharts trend + audit log table) |
| **Improvement Velocity & Prediction** | **MISSING** | No velocity points/session; no probabilistic readiness prediction for 4+ sessions |
| **Authentication & Multi-User Scoping**| **MISSING** | No user table, passwords, or JWT auth; all sessions are unauthenticated and public (Phase 2) |
| **Consent & Data Deletion** | **MISSING** | No explicit camera/mic consent modal; no "Delete My Session / Account" buttons (Phase 2) |
| **Centralized Config & Constants** | **FIXED** (`03c861f`) | `backend/config.py` declaring weights, delivery thresholds, word count bands, filler words, and LLM configuration |
| **Versioned Migrations (Alembic)** | **FIXED** (`03c861f`, `05f987c`) | Alembic migration recreating 7-table schema with nullable sensors & `weights_used`; auto-applies on startup |
| **Automated Test Suite** | **FIXED** (`2393d4c`, `86727ad`) | 30 tests in `tests/` covering API, rubric determinism, ranking, null sensors, and guarded LLM evaluation |
| **Validation, Error Shape & Guards** | **FIXED** (`fb78d68`) | Strict Pydantic validation, uniform `{error: {code, message, details}}` shape, division-by-zero guards, structured logging |
| **Path-Agnostic Config & URLs** | **FIXED** (`2e24a68`) | `frontend/src/config.js` with `import.meta.env.VITE_API_URL`, `frontend/.env.example`, all hardcoded URLs eliminated |

---

## 5. Phase-by-Phase Implementation Status

### Phase 1: Reliability, Testing & Data Correctness (STATUS: COMPLETED ✅)
1. **Housekeeping & Branching** (`cfadf4d`):
   - Created git branch `phase-1-reliability`.
   - Renamed `claud.md` $\rightarrow$ `docs/ARCHITECTURE.md`.
   - Created `docs/AUDIT.md`.
2. **Pytest Test Suite Baseline** (`2393d4c`):
   - Created `requirements-dev.txt`, `pytest.ini`, and unit test suite (`tests/conftest.py`, `test_scoring.py`, `test_resume.py`, `test_questions_and_followup.py`, `test_api.py`).
   - Verified rubric determinism, golden answer ranking order, and resume parser robustness.
3. **Versioned Database Migrations & Centralized Config** (`03c861f`, `05f987c`):
   - Replaced ad-hoc `ALTER TABLE` in `database.py` with Alembic migration `0001_initial_schema.py`.
   - Added `backend/config.py` defining initial weights, delivery thresholds, word count bands, filler words, and LLM configuration.
   - Cleaned up untracked pycache binaries and configured `.gitignore`.
4. **Structured Evidence Contract** (`ac99099`):
   - Implemented `DimensionEvaluation` and `AnswerEvaluationResponse` in `backend/schemas/schemas.py`.
   - Refactored `backend/services/scoring_engine.py` to return observable signals per dimension (`score`, `evidence`, `explanation`, `recommended_action`) with backward-compatible legacy fields.
   - Updated `Interview.jsx` and `Dashboard.jsx` to render observable evidence.
5. **Delivery Renaming, Null Handling & Re-normalized Readiness** (`81c52b6`):
   - Renamed session term to **"Delivery & Visual Stability"** (mapped internally to `behavioral_score`).
   - Relabeled UI to **"Head alignment (visual centering proxy)"** with centering tooltip.
   - Sensor columns made nullable; camera-off sends `null` (never imputed data).
   - Dynamically re-normalizes weights when unmeasured: Comm: 0.375, Tech: 0.375, Resume: 0.25, Delivery: 0.0.
   - Stored `weights_used` JSON in `session_scores`.
   - Updated `Dashboard.jsx` to render "Not measured: camera was off" and explain re-normalized weights.
6. **Validation, Uniform Error Shape, Structured Logging & Division Guards** (`fb78d68`):
   - Centralized exception handlers in `backend/main.py` producing uniform error shape: `{"error": {"code": "...", "message": "...", "details": [...]}}`.
   - Added `logging.getLogger("interview_system")` with structured log output.
   - Added zero-division guards for WPM, elapsed durations, and rate computations.
7. **Guarded LLM Evaluation Path** (`86727ad`):
   - Updated `backend/services/evaluation_engine.py` using `httpx` (Gemini $\rightarrow$ OpenAI $\rightarrow$ deterministic fallback).
   - Enforced 5.0s timeout, max 1 retry, temperature 0.0, transcript grounding check, and SHA-256 caching.
   - Added `tests/test_evaluation_llm.py` (30/30 tests passing).
8. **Frontend Config, API URL Abstraction & Non-blocking Speech Banner** (`2e24a68`):
   - Added `frontend/src/config.js` (`VITE_API_URL` with `http://127.0.0.1:8000` fallback) and `frontend/.env.example`.
   - Replaced all hardcoded URLs across all frontend pages (`InterviewSetup`, `ResumeUpload`, `Progress`, `FixAnswer`, `Interview`, `Dashboard`).
   - Replaced `alert()` in `FixAnswer` and `Interview` with inline dismissable status/warning banners and a segmented `🎙️ Speak Answer` / `⌨️ Type Answer` toggle.
9. **Documentation Path Cleanup & Phase 1 Audit Finalization**:
   - Removed absolute paths from `README.md` and `docs/ARCHITECTURE.md`.
   - Added Running Tests section to `README.md`.
   - Updated `docs/AUDIT.md` reflecting completed Phase 1 status and commit hashes.

### Phase 2: Complete Implementation — Auth, User Scoping, Voice Metrics & Privacy (FIXED)

All Phase 2 requirements have been fully implemented, tested, and verified on branch `phase-2-auth-privacy`:

1. **Phase 1 Closeout** (`30b3199`):
   - Provided endpoint coverage matrix, legacy migration proof (`tests/test_migration.py`), camera-off test path, LLM metadata persistence, and dependency justifications.
   - Removed emojis from Speak/Type UI toggles.
   - Logged deferred bundle-size audit note.

2. **Alembic Database Migration 0002** (`6d9d765`):
   - Created `alembic/versions/0002_auth_and_user_scoping.py`.
   - Added tables: `users`, `user_profile`, `voice_metrics`, `consent_records`.
   - Added `user_id` foreign keys to `resumes` and `interview_sessions`.
   - Verified automated upgrade test against pre-Alembic fixture database.

3. **Authentication Backend & Rate Limiting** (`42c19aa`):
   - Added `backend/services/auth_service.py` with Argon2 password hashing (minimum 10 chars, reject weak passwords).
   - Configured secure httpOnly, SameSite=Lax JWT cookie transport (`AUTH_COOKIE_NAME="interview_auth"`, 60-minute duration).
   - Added sliding expiration and memory-bounded IP rate limiter (register: 10/min, login: 10/min).
   - Implemented `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/me`, and `GET/PUT /profile`.
   - Added `tests/test_auth.py` (8 passing tests).

4. **User Ownership Scoping & Isolation Matrix** (`2e8cf34`):
   - Scoped all resume, interview, analytics, and report routes with `get_current_user`.
   - Enforced 404 Not Found on cross-user resource access (never 403 or enumerable errors).
   - Created `scripts/claim_legacy_data.py --email <user@example.com>` to safely claim unassigned pre-Alembic rows.
   - Added programmatic inspection in `tests/test_user_isolation.py` scanning all FastAPI routes to prove unauthenticated 401s and cross-tenant 404s.

5. **Authentication Frontend Integration** (`499bc53`):
   - Implemented `frontend/src/utils/api.js` with `credentials: "include"` and global 401 dispatch to `/login`.
   - Added `AuthContext.jsx` with active session tracking, pre-filling target role and difficulty from user profile in `InterviewSetup.jsx`.
   - Added `ProtectedRoute.jsx` guarding `/resume`, `/setup`, `/interview`, `/dashboard`, `/report`, `/fix-answer`, `/progress`, and `/history`.
   - Added minimal, professional `Login.jsx` and `Register.jsx` pages.
   - Implemented clear session state on logout (clears `ReportContext` and `sessionStorage`).

6. **Per-Answer Voice Metrics & Vocabulary Diversity** (`7ac63f0`):
   - Added `backend/services/voice_service.py` computing WPM, filler word count, pause metrics (count, avg pause, longest pause, silence ratio), and length-guarded MATTR vocabulary diversity (minimum 20 words).
   - Client captures speech segment intervals relative to question start in `Interview.jsx`.
   - Typed responses return `null` / `"Not measured"` for audio cadence, never defaulted or imputed values.
   - Rendered Voice & Cadence Metrics card in `Dashboard.jsx` with UI tooltip: `"approximate, based on speech-recognition timing"`.
   - Maintained `USE_VOICE_METRICS_IN_SCORE = False` in `config.py` ensuring readiness scores remain identical and display-only.
   - Added `tests/test_voice_metrics.py` (7 passing tests).

7. **Interview Session History & Report Reopening** (`51ba8df`):
   - Verified paginated `GET /interview/history?page=1&limit=10` returning newest-first session items scoped to user.
   - Added `frontend/src/pages/History.jsx` listing past sessions, dates, roles, modes, scores, view report links, and session deletion with confirmation dialog.
   - Added `/history` route to `App.jsx` and link to `Navbar.jsx`.
   - Added session deletion button to `Progress.jsx`.

8. **Privacy Consent Tracking, Data Export & Cascading Deletion** (`4637a58`):
   - Added `GET /consent` and `POST /consent` recording timestamped grants/withdrawals in `consent_records`.
   - Added `DELETE /interview/{session_id}` cascading all child rows (answers, evaluations, voice metrics, behavioral metrics, scores).
   - Verified `DELETE /resume/{resume_id}`.
   - Added `DELETE /auth/account` requiring password re-confirmation via `PasswordConfirmRequest`, permanently deleting all user data and clearing auth cookies.
   - Added `GET /auth/export` returning full user JSON data for portability.
   - Added frontend Sensor Processing & Privacy Consent Modal before camera/mic activation, offering Text-Only Mode with zero sensor access.
   - Added Data Retention Statement across UI and README: *"Your data is kept until you delete it."*
   - Added `tests/test_consent_and_deletion.py` (3 passing tests).

9. **Documentation & Phase 2 Audit Log** (`fccc79c`):
   - Updated `README.md`, `docs/ARCHITECTURE.md`, and `docs/AUDIT.md`.

---

## 6. Phase 2 Verification & Sign-Off Gate

1. **Phase 2 Deliverables Summary**:
   - All Phase 2 authentication, scoping, voice metrics, privacy, and deletion requirements implemented and verified.
   - **57 automated tests** in `tests/` pass in < 5s covering auth, user isolation, voice metrics, consent, deletion, migrations, scoring determinism, and LLM evaluation.
   - Vite production build succeeds with 0 errors.
   - All 8 sub-step commits recorded to `phase-2-auth-privacy` git branch.
2. **Phase 3 Gate**:
   - Stop and wait for user review and approval before proceeding to Phase 3 (Intelligence Layer: Claim-Probe Ladder, Verification Risk, Safe Pressure Mode).

---

### Phase 3: Complete Implementation — Intelligence Layer, Claim-Probe Ladder, Verification Risk, Safe Pressure Mode (FIXED)

All Phase 3 requirements have been fully implemented, tested, and verified on branch `phase-3-intelligence`:

1. **Phase 2 Closeout** (`686d8d7`):
   - Addressed all security and disclosure items: explicit CSRF double-submit token protection, rate limiting tests, startup guard requiring `SECRET_KEY` in production, explicit CORS origins with credentials, cookie flags (`httpOnly`, `SameSite=Lax`, `Secure` in production), `scripts/claim_legacy_data.py`, and log-hygiene policy.
   - Privacy copy honesty: Rewrote consent modal, README, and ARCHITECTURE to explicitly disclose that Web Speech API audio processing is delegated to the browser vendor's cloud service and does not stay solely on device; local video frames never leave the browser; server receives only derived text and metrics; text-only mode completely disables both. Bumped `policy_version` to "2.0".
   - MediaPipe FaceMesh assets: Bundled locally under `frontend/public/mediapipe/face_mesh/` (`face_mesh.binarypb`, `face_mesh_solution_packed_assets_loader.js`, `face_mesh_solution_simd_wasm_bin.js`, `face_mesh_solution_simd_wasm_bin.wasm`, `face_mesh_solution_wasm_bin.js`, `face_mesh_solution_wasm_bin.wasm`), removing third-party CDN fetch during runtime for air-gapped operation.
   - Route ordering verification: Confirmed static routes (`/interview/history`, `/interview/latest`, `/report/latest`) are declared before parameterized route `/{session_id}` in FastAPI router, preventing shadowing.
   - Missing evidence tests: Added tests for pause computation fixtures, zero-duration guards, MATTR vocabulary length guards, legacy DB fixture upgrade, and zero-orphan row checks on cascading deletion.
   - Documented unverifiable manual hardware items (real camera, real mic, cross-browser Safari/Firefox, live LLM keys).

2. **Alembic Database Migration 0003** (`5da4343`):
   - Created `alembic/versions/0003_intelligence_layer.py`.
   - Added tables: `resume_skills`, `resume_projects`, `resume_claims`, `resume_flags`, `interview_questions`, `interview_decisions`, `claim_consistency`, `answer_visual_metrics`.
   - Added columns to `resumes`: `role_fit_scores` (JSON), `seniority_signal` (String).
   - Added columns to `answer_evaluations`: `verification_risk` (JSON), `probe_ladder_step` (String), `probe_intent` (String).
   - Fully backward-compatible upgrade with non-destructive downgrade.

3. **Resume Intelligence & Claim Extraction** (`57513fa`):
   - Upgraded `backend/services/resume_service.py` with deterministic regex/NER extraction of skills (categorized by languages, frameworks, databases, cloud/devops, core), projects, and concrete claims (action, metric, impact, technology).
   - Rule-based risk flags: generic claims, metricless claims, missing tenure dates, technology soup.
   - Deterministic role-fit scoring against 4 standard profiles: Frontend, Backend, Fullstack, ML / Applied AI (matching skills, project relevance, and seniority signal).
   - Probe priorities calculation identifying top claims and risk areas to prioritize during interview question generation.
   - Added `POST /resume/{resume_id}/reanalyze` endpoint.
   - Added `tests/test_resume.py` coverage.

4. **Deterministic Claim-Probe Ladder & Adaptive Question Engine** (`e4693ef`):
   - Created `backend/services/adaptive_engine.py` implementing the 4-stage probe ladder:
     - `T1_FOUNDATION`: Concept and role in resume claim.
     - `T2_TRADE_OFFS`: Alternatives considered and design decisions.
     - `T3_INCIDENT`: Production failure, debugging, or bottleneck scenario.
     - `T4_EDGE_CASE`: Scale stress-test, failure mode, or resource constraint.
   - Implemented rolling difficulty adjustment: 2 consecutive high scores ($\ge 80$) increase difficulty; 2 consecutive low scores ($< 50$) decrease difficulty.
   - Dynamic question bank and resume-anchored fallback probe templates.
   - Decision logging in `interview_decisions` table recording target claim, probe ladder step, difficulty adjustment, and human-readable rationale.
   - Added `POST /interview/{session_id}/next` endpoint.

5. **Adaptive Next-Question UI Integration & Decision Log Rationale** (`25830fb`):
   - Refactored `frontend/src/pages/Interview.jsx` to fetch subsequent questions adaptively via `POST /interview/{session_id}/next` on answer submission.
   - Synchronized question timers, reset speech recognition, and handled seamless interview completion.
   - Updated `frontend/src/pages/Dashboard.jsx` to display probe ladder step badge (`T1`–`T4`) and adaptive decision rationale accordion for interviewer transparency.

6. **Per-Answer Verification Risk Scoring with Observable Evidence Contract** (`1869f28`):
   - Created `backend/services/verification_risk.py` evaluating 5 observable answer indicators:
     - Generic filler phrases ("industry best practices", "leveraged scalable solutions").
     - Buzzword-to-content density ratio.
     - Absence of concrete specifics (quantifiable numbers, technical parameters, explicit tooling).
     - Repetition across answer sentences.
     - Ownership vagueness ("we worked on", "it was done" vs "I built", "I designed").
   - Output structured contract: `level` (`low`, `moderate`, `elevated`), `risk_score` (0–100), `signals`, and `observable_evidence` list.
   - Strictly enforced non-accusatory language: no banned terms ("bluff", "lie", "fake").
   - Added comprehensive tests in `tests/test_verification_risk.py` (12 passing tests).

7. **Claim Consistency Tracking & Dynamic Session Consistency Scoring** (`04930e8`):
   - Implemented `backend/services/claim_consistency_service.py` linking answer transcripts to targeted resume claims.
   - Status classifications: `consistent` (matches claim details and metrics), `weak_support` (claim mentioned but missing details), `low_consistency` (contradictory metrics or conflicting stack), `insufficient_evidence` (unanswered or non-responsive).
   - Dynamic session consistency calculation: replaces static score when $\ge 1$ claim-probed answer exists, setting `consistency_source = "claim_level"`.
   - Included non-accusatory disclaimer across all consistency reports.
   - Added `tests/test_claim_consistency.py` (4 passing tests).

8. **Safe Pressure Mode with Time Limits & Challenge Triggers** (`7771b84`):
   - Implemented Safe Pressure Mode with 45-second timer constraints per question.
   - Dynamic follow-up challenge triggers: metric justification ("You mentioned 10k RPS, what was the bottleneck?"), counterexample/failure probing ("What if that database failed?"), and vague assertion challenges.
   - Safe de-escalation: added `POST /interview/{session_id}/switch-mode` allowing candidate to transition to Standard mode at any point (extending timer to 90s).
   - Ethical safeguards: Pre-interview pressure mode notice and mandatory acknowledgment checkbox in `InterviewSetup.jsx`.
   - Added `tests/test_pressure_mode.py` (6 passing tests).

9. **Client-Side Extended Visual Metrics with Quality Gating** (`4f9a817`):
   - Added `backend/services/visual_metrics_service.py` and updated client FaceMesh pipeline.
   - Client measures: `head_alignment_percent`, `blink_rate`, `head_movement_variance`, `face_visibility_ratio`, `head_shift_count`, and `frames_sampled`.
   - Quality gating: if `face_visibility_ratio < 0.60` or `frames_sampled < 30`, visual metrics are marked `quality_gate_passed = False` with `confidence_level = "low"` or `"unmeasured"`.
   - Ethical score invariance: `USE_EXTENDED_VISUAL_METRICS_IN_SCORE = False` ensures visual metrics are purely diagnostic and NEVER alter readiness scores.
   - Observable language contract: banned pseudo-scientific labels ("nervousness", "stress spike", "posture check").
   - Added `tests/test_visual_metrics.py` (8 passing tests).

10. **Optional LLM Probe Phrasing with Strict Claim Grounding** (`b4ac1d6`):
    - Added `backend/services/probe_rephraser.py` using Gemini/OpenAI to generate natural, conversational probe phrasing grounded in candidate claims.
    - Safety guards:
      - 2.5s strict timeout with immediate deterministic fallback.
      - SHA-256 in-memory caching to eliminate duplicate LLM calls.
      - Banned word filter rejecting adversarial or hostile phrasing.
      - Strict domain token grounding (`verify_probe_grounding`) verifying that claim keywords exist in the probe output.
      - 100% offline fallback when API keys are absent.
    - Added `tests/test_probe_rephraser.py` (7 passing tests).

11. **Intelligence Report UI, Full Data Export & Cascading Deletion** (`7558b24`):
    - Frontend UI upgrades:
      - `ResumeUpload.jsx`: Role Fit card (scores across 4 profiles), Seniority Signal badge, Top Risk Areas, Extraction Flags.
      - `Dashboard.jsx`: Verification Risk signal badge with observable evidence breakdown; Resume Claim Verification table displaying claim text, probe status, consistency rating, and non-accusatory disclaimer.
    - Data portability: `GET /auth/export` includes all 8 intelligence tables (`resume_skills`, `resume_projects`, `resume_claims`, `resume_flags`, `interview_questions`, `interview_decisions`, `claim_consistency`, `answer_visual_metrics`).
    - Cascading deletion: `DELETE /auth/account` and `DELETE /interview/{session_id}` cascade across all 8 intelligence tables with zero orphan rows left in SQLite.
    - Added `tests/test_intelligence_export_and_cascade.py`.

12. **Documentation & Phase 3 Audit Log** (`5a39741`):
    - Updated `README.md`, `docs/ARCHITECTURE.md`, and `docs/AUDIT.md` reflecting all Phase 3 capabilities, API schemas, testing metrics, and privacy contracts.

---

## 7. Phase 3 Verification & Sign-Off Gate

1. **Phase 3 Deliverables Summary**:
   - All Phase 3 intelligence layer, claim-probe ladder, verification risk, safe pressure mode, and visual gating requirements implemented and verified.
   - **107 automated tests** in `tests/` pass with zero failures:
     - `test_api.py` (13 tests)
     - `test_auth.py` (11 tests)
     - `test_claim_consistency.py` (4 tests)
     - `test_consent_and_deletion.py` (3 tests)
     - `test_evaluation_llm.py` (6 tests)
     - `test_intelligence_export_and_cascade.py` (1 test)
     - `test_migration.py` (1 test)
     - `test_pressure_mode.py` (6 tests)
     - `test_probe_rephraser.py` (7 tests)
     - `test_questions_and_followup.py` (5 tests)
     - `test_resume.py` (9 tests)
     - `test_scoring.py` (11 tests)
     - `test_user_isolation.py` (3 tests)
     - `test_verification_risk.py` (12 tests)
     - `test_visual_metrics.py` (8 tests)
     - `test_voice_metrics.py` (7 tests)
   - Vite production build succeeds with 0 errors.
   - Clean, reproducible git history on `phase-3-intelligence` branch with one commit per sub-step.
   - Full air-gapped / offline capability preserved with zero external network dependencies.
2. **Phase 4 Gate**:
   - Approved to proceed to Phase 4 (Performance Intelligence, Learning Loop & Readiness Engine).

---

## 8. Phase 4 Baseline Audit

Conducted on branch `phase-4-performance-intelligence` from commit `5a39741`.

### Baseline Verification Status

1. **Test Suite**: 107/107 automated pytest tests passing in 6.81s across 16 test files.
2. **Frontend Build**: Vite production build succeeded with 0 errors (`dist/index.html` 0.46 kB, `dist/assets/index-BlmvpAY2.js` 790.08 kB).
3. **Database Migration State**: Alembic head at `0003_intelligence_layer` (all 15 tables present and verified).
4. **Offline / Air-Gapped Mode**: Functional with zero API keys required; bundled FaceMesh assets in `frontend/public/mediapipe/face_mesh/`.

### Baseline Matrix

- **IMPLEMENTED**:
  - Single-session adaptive interview loop (`/interview/start`, `/next`, `/answer`, `/complete`).
  - Resume intelligence & claim extraction with role fit and risk flags (`POST /resume/{id}/reanalyze`).
  - Deterministic 4-step probe ladder (`T1_FOUNDATION` -> `T2_TRADE_OFFS` -> `T3_INCIDENT` -> `T4_EDGE_CASE`) with difficulty stepping.
  - Interview decision logging (`interview_decisions` table).
  - Verification risk observable indicators (generic phrasing, buzzwords, specificity gap, repetition, ownership vagueness).
  - Claim consistency tracking (`consistent`, `weak_support`, `low_consistency`, `insufficient_evidence`) with dynamic session scoring.
  - Safe Pressure Mode with 45s timer, challenge triggers, de-escalation `/switch-mode` (90s).
  - Client-side extended visual metrics with quality gating (`face_visibility_ratio < 0.60` or `frames_sampled < 30`).
  - Diagnostic metric score invariance (`USE_VOICE_METRICS_IN_SCORE = False`, `USE_EXTENDED_VISUAL_METRICS_IN_SCORE = False`).
  - User authentication (Argon2, httpOnly JWT cookies, CSRF tokens, rate limiting).
  - Cascading deletion and data export covering all 15 DB models.
  - 107 automated tests across 16 test files.
  - Production frontend build.

- **PARTIALLY IMPLEMENTED**:
  - Longitudinal progress: `/interview/history` returns past sessions, and `Progress.jsx` charts past scores, but lacks comparability criteria, trend detection, or data-sufficiency gating.
  - Single-turn answer improvement: `FixAnswer.jsx` exists, but is not tied into recurring weaknesses or structured practice recommendations.

- **MISSING** (Phase 4 Objectives):
  - Session Timeline service deriving normalized chronological performance event stream from stored answers/metrics.
  - Performance Dimension Model contract formalizing value, measured state, evidence, explanation, and action for each dimension.
  - Weakness diagnosis engine with symptom -> pattern -> root weakness detection and configurable evidence thresholds.
  - Longitudinal recurring weakness tracking across comparable sessions (`MIN_SESSIONS_FOR_RECURRING`).
  - Deterministic weakness severity model (`low`, `moderate`, `high`, `critical`).
  - Longitudinal improvement velocity calculation with minimum-session guards and comparability criteria.
  - Session comparability engine (`is_comparable(session_a, session_b)` checking role, mode, difficulty, completed answers).
  - Practice recommendation engine (`select_next_practice(user_history)`) generating prioritized, explainable practice plans.
  - Targeted practice session mode leveraging existing interview infrastructure (question bank, claim ladder, rubrics).
  - Longitudinal readiness engine with data-sufficiency confidence (`insufficient_data`, `low`, `medium`, `high`) and smoothed trend (`improving`, `stable`, `declining`).
  - Target readiness gap analysis and bounded baseline score projection (non-ML, explicit heuristic).
  - Redesigned minimal Report UI with visual timeline, what went well, what held you back, and next practice.
  - Dashboard "Next Best Practice" banner with one-click practice launch.
  - Weakness history UI tracking first/last seen, occurrences, severity trend, and improvement confirmation.

- **BROKEN**:
  - None. Zero regressions, 107/107 tests passing.

- **UNVERIFIED**:
  - Physical browser camera capture.
  - Physical microphone audio and Web Speech recognition.
  - Non-Chromium speech recognition behavior (Firefox / Safari).
  - Live third-party LLM providers (Gemini / OpenAI API keys).



