# AI Interview Intelligence System — Project Architecture & Technical Guide

---

## 1. Executive Summary

The **AI Interview Intelligence System** is an enterprise-grade, web-based platform designed to simulate realistic technical and behavioral interviews. It moves beyond generic questionnaire apps by offering:

1. **Resume-Aware Question Generation**: Parses candidate resumes (PDF or text), extracts technical competencies, and tailors interview questions specifically to the candidate's declared stack and background.
2. **Multimodal Performance Assessment**:
   - **Computer Vision**: Utilizes MediaPipe FaceMesh for visual centering, eye contact stability, and blink frequency tracking.
   - **Speech Diagnostics**: Employs the Web Speech API for real-time speech-to-text, calculating speech pacing (WPM) and detecting verbal filler words (*um, uh, like, basically*).
3. **Structured Rubric Scoring Engine**: Evaluates answers objectively across 5 core dimensions:
   - Structure & Narrative Flow
   - Technical Depth
   - Engineering Reasoning & Tradeoffs
   - STAR Framework Adherence (Situation, Task, Action, Result)
   - Resume Skill Consistency
4. **Weighted Interview Readiness Formula**:
   $$\text{Final Readiness Score} = 0.30 \times \text{Communication} + 0.30 \times \text{Technical} + 0.20 \times \text{Behavioral} + 0.20 \times \text{Resume Consistency}$$
5. **Fix My Answer (AI Coach)**: Refactors weak or passive responses into authoritative STAR-structured answers while strictly preserving the candidate's authentic experience without fabricating achievements.
6. **Progress & Longitudinal Analytics**: Tracks candidate readiness trajectories and competency evolution across multiple interview sessions.
7. **Offline Deterministic Fallbacks**: Operates 100% reliably in local and air-gapped demo environments without hard dependencies on paid third-party AI APIs.

---

## 2. System Architecture

```
                                  +---------------------------------------+
                                  |         React 19 / Vite Client        |
                                  |         (Port 5173 / Vanilla CSS)     |
                                  +-------------------+-------------------+
                                                      |
                         HTTP REST API (JSON / FormData) & WebSocket Ready
                                                      |
                                                      v
                                  +---------------------------------------+
                                  |          FastAPI Application          |
                                  |            (Port 8000)                |
                                  +-------------------+-------------------+
                                                      |
        +---------------------------------------------+---------------------------------------------+
        |                                             |                                             |
        v                                             v                                             v
+------------------+                          +------------------+                          +------------------+
|  API Route Layer |                          |  Service Layer   |                          |  Data & ORM      |
|  - /resume       |                          |  - resume_service|                          |  - SQLAlchemy 2  |
|  - /interview    |                          |  - scoring_engine|                          |  - SQLite        |
|  - /report       |                          |  - question_sel  |                          |  - interview.db  |
|  - /answer       |                          |  - answer_improv |                          |  - Auto Migrate  |
|  - /progress     |                          |  - evaluation    |                          |                  |
+------------------+                          +------------------+                          +------------------+
```

---

## 3. Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.12+ / 3.14 compatible)
- **ASGI Server**: Uvicorn
- **ORM & Database**: SQLAlchemy 2.0+ with SQLite (`interview.db`)
- **Validation**: Pydantic v2
- **Document Processing**: Poppler `pdftotext` with pure-stream fallback parser

### Frontend
- **Framework**: React 19 with Vite 7
- **Routing**: React Router DOM v7
- **Analytics & Data Visualization**: Recharts 3.x
- **Computer Vision**: MediaPipe FaceMesh & Camera Utils (`@mediapipe/face_mesh`, `@mediapipe/camera_utils`)
- **Speech Recognition**: Browser Native Web Speech API (`webkitSpeechRecognition` / `SpeechRecognition`)
- **Styling**: Minimalist, clean HR/SaaS typography (Inter / Slate / Navy palette)

---

## 4. End-to-End User Workflow

```
[ Landing Page (/) ]
        │
        ▼
[ Resume Upload (/resume) ]
  • Upload PDF or paste text
  • System parses skills, education, experience, and detects vague phrasing
  • Calculates Resume Audit Score (0–100)
        │
        ▼ (One-Click Hand-off)
[ Interview Setup (/setup) ]
  • Displays attached candidate profile
  • Select Mode: Practice, Technical, HR/Behavioral, Pressure
  • Select Difficulty: Easy, Medium, Hard
  • Select Target Role & Question Count (1 to 5)
  • Optional hardware test (with immediate skip/text-mode fallback)
        │
        ▼
[ Live Mock Interview (/interview) ]
  • Dynamic question presented based on candidate stack
  • Live countdown timer per prompt
  • Real-time webcam feed with eye-contact and blink overlay
  • Voice speech-to-text recording with live WPM and filler word counter
  • Submit answer → Immediate Rubric Feedback Card (Scores, Strengths, Weaknesses)
  • Follow-up probe if response is overly brief or lacks metrics
        │
        ▼
[ Executive Performance Report (/dashboard & /report) ]
  • Main Interview Readiness Score & Readiness Classification
  • Dimension Subscores (Communication, Technical, Behavioral, Resume Consistency)
  • Radar/Bar visualization and computer vision sensor summary
  • Detailed Question-by-Question review with qualitative critique
        │
        ├──► [ Fix My Answer (/fix-answer) ]
        │     • AI Coach refactors weak answers into STAR framework
        │     • Diagnoses weaknesses and provides vocabulary upgrade table
        │
        └──► [ Progress History (/progress) ]
              • Longitudinal multi-session score trajectory chart
              • Historical audit log table with deep-links to past reports
```

---

## 5. Detailed Component & Service Breakdown

### 5.1 Backend Services (`backend/services/`)

#### 1. `resume_service.py`
- **Text Extraction**: Uses Linux system utility `pdftotext` to extract pristine text from PDF byte buffers. If running in environments where `pdftotext` is absent, invokes a regex-based stream fallback parser.
- **Competency Detection**: Categorizes skills across 5 domains:
  - *Languages*: Python, Java, C++, TypeScript, Go, Rust, SQL, etc.
  - *Frameworks*: React, FastAPI, Django, Spring Boot, Vue, Next.js, etc.
  - *Databases*: PostgreSQL, MySQL, Redis, MongoDB, Cassandra, SQLite.
  - *Cloud & DevOps*: AWS, Docker, Kubernetes, CI/CD, Git, Terraform.
  - *Core Concepts*: REST API, Microservices, System Design, OOP, Data Structures.
- **Audit & Clarity Scorer**: Flags passive or vague expressions (e.g., *"worked on various"*, *"responsible for bug fixing"*), rewards quantified impact (percentages, latencies, user scale), and generates a 0–100 Resume Audit Score.

#### 2. `scoring_engine.py`
- Implements transparent, deterministic rubric scoring without black-box rating guesses:
  - **Structure Score**: Measures length appropriateness (60–250 words), logical progression, paragraph transitions (*furthermore, because, specifically, finally*).
  - **Technical Depth Score**: Measures domain-specific technical terminology, architectural mechanisms (*caching, indexing, concurrency, latency, microservices*).
  - **Reasoning Score**: Evaluates architectural tradeoffs and explanations of *"why"* choices were made.
  - **STAR Score**: Named sub-score under Communication/Structure detecting Situation, Task, Action, and Result markers with action-oriented personal ownership verbs.
  - **Resume Consistency Score**: Cross-references technologies cited in the candidate's response against their parsed resume profile.
- **Evidence Contract**:
  Every answer dimension returns a strictly typed structure:
  ```json
  {
    "score": 0.0-100.0,
    "evidence": ["0 quantified results found", "14 filler words in 212 words"],
    "explanation": "Narrative explanation...",
    "recommended_action": "Targeted next steps..."
  }
  ```
- **Dimension Naming & Mapping**:
  - The 20% session term is named **"Delivery & Visual Stability"** (mapped internally to the `behavioral_score` database column). Psychological terms like "Behavioral Confidence" are strictly avoided.
  - Visual signals in UI/reports are labeled **"Head alignment (visual centering proxy)"** (mapped internally to `eye_contact_percent`), with tooltip: *"Share of the session your head was positioned near the centre of the frame. It does not measure gaze, confidence, or nervousness."*
- **Readiness Formula & Sensor Nullability**:
  - When Delivery sensors are measured (camera active):
    $$\text{Readiness} = 0.30 \times \text{Communication} + 0.30 \times \text{Technical} + 0.20 \times \text{Delivery} + 0.20 \times \text{Resume Consistency}$$
  - When Delivery sensors are unmeasured (camera off or denied, `eye_contact_percent` and `blink_rate` are `null`):
    Weights are proportionally re-normalized:
    $$\text{weights} = (\text{Communication: } 0.375, \text{Technical: } 0.375, \text{Resume Consistency: } 0.25, \text{Delivery: } 0.0)$$
    The exact weights applied are persisted in `session_scores.weights_used` so every score is reproducible.

#### 3. `question_selector.py`
- Queries `models.QuestionBank` (pre-seeded with 80+ questions).
- Filters by requested mode (*Technical, HR, Behavioral, Pressure*) and difficulty level (*Easy, Medium, Hard*).
- Prioritizes questions matching the candidate's parsed skills (e.g., if candidate knows Docker and SQL, queries select questions focusing on those domains).

#### 4. `followup_generator.py`
- Analyzes candidate answers for gaps:
  - If answer is < 25 words: probes for step-by-step implementation specifics.
  - If answer lacks quantifiable metrics: asks the candidate to quantify system or business impact.
  - If answer discusses technology without tradeoffs: asks for architectural alternatives evaluated.
  - If answer mentions team conflicts: asks about stakeholder communication.

#### 5. `answer_improvement_service.py`
- Powers the **Fix My Answer** module.
- Identifies passive phrasing, lack of metrics, and missing STAR structure.
- Restructures the response into a high-impact engineering statement:
  - **Situation**: Contextual background of the problem.
  - **Task**: Explicit SLA or engineering objective.
  - **Action**: Concrete architectural steps taken with personal ownership.
  - **Result**: Quantifiable performance, latency, or business impact.
- Generates a vocabulary upgrade table comparing weak phrases (*"helped make it faster"*) with senior terminology (*"optimized query latency by 65%"*).

#### 6. `evaluation_engine.py`
- Clean abstraction layer for rubric evaluation with guarded provider cascade (Gemini $\rightarrow$ OpenAI $\rightarrow$ deterministic fallback).
- Enforces strict 5-second timeout, max 1 retry, temperature 0.0, grounding verification against the transcript, and SHA-256 caching.
- If API keys are omitted or external calls fail/timeout, cleanly falls back to the deterministic rubric in `scoring_engine.py`.

---

### 5.2 Database Schema (`backend/models/models.py`)

Managed via Alembic migrations (`alembic/versions/`):
1. **`resumes`**:
   - `id` (PK), `filename`, `candidate_name`, `raw_text`, `skills` (JSON), `experience`, `education`, `resume_score`, `strengths` (JSON), `weak_areas` (JSON), `suggested_improvements` (JSON), `summary`, `created_at`.
2. **`interview_sessions`**:
### 5.2 Database Schema & Alembic Migrations

The database (`interview.db`) is managed via Alembic migrations (with automated upgrade to `head` on application startup):
- `0001_initial_schema.py`: Baseline 7 tables.
- `0002_auth_and_user_scoping.py`: Multi-tenancy, voice metrics, and privacy tables.
- `0003_intelligence_layer.py`: 8 tables for claim-probe ladder, resume intelligence, decisions, claim consistency, and extended visual metrics.

#### Table Definitions:
1. **`users`**:
   - `id` (PK), `email` (unique index), `password_hash` (Argon2), `full_name`, `is_active`, `created_at`.
2. **`user_profile`**:
   - `id` (PK), `user_id` (FK → users.id, CASCADE), `target_role`, `domain`, `experience_level`, `university`, `graduation_year`, `current_status`, `target_companies` (JSON), `interview_goal`, `weekly_practice_goal`, `created_at`, `updated_at`.
3. **`consent_records`**:
   - `id` (PK), `user_id` (FK → users.id, CASCADE), `consent_type` (`camera`, `microphone`, `transcript_storage`), `policy_version`, `granted` (Boolean), `created_at`.
4. **`resumes`**:
   - `id` (PK), `user_id` (FK → users.id, CASCADE), `filename`, `candidate_name`, `raw_text`, `skills` (JSON), `experience`, `education`, `resume_score`, `strengths` (JSON), `weak_areas` (JSON), `suggested_improvements` (JSON), `role_fit_scores` (JSON), `risk_areas` (JSON), `summary`, `created_at`.
5. **`resume_skills`**:
   - `id` (PK), `resume_id` (FK → resumes.id, CASCADE), `name`, `category`, `confidence`, `evidenced`, `created_at`.
6. **`resume_projects`**:
   - `id` (PK), `resume_id` (FK → resumes.id, CASCADE), `title`, `description`, `technologies` (JSON), `bullets` (JSON), `created_at`.
7. **`resume_claims`**:
   - `id` (PK), `resume_id` (FK → resumes.id, CASCADE), `project_id` (FK → resume_projects.id, SET NULL), `claim_text`, `claim_type`, `technologies` (JSON), `has_metric`, `probe_priority` (Float), `reasons` (JSON), `created_at`.
8. **`resume_flags`**:
   - `id` (PK), `resume_id` (FK → resumes.id, CASCADE), `claim_id` (FK → resume_claims.id, CASCADE), `flag_type`, `description`, `severity`, `created_at`.
9. **`interview_sessions`**:
   - `id` (PK), `user_id` (FK → users.id, CASCADE), `resume_id` (FK), `mode`, `difficulty`, `target_role`, `total_questions`, `current_question_index`, `followup_count`, `status`, `created_at`.
10. **`interview_questions`**:
    - `id` (PK), `session_id` (FK → interview_sessions.id, CASCADE), `sequence_order`, `question_text`, `question_type` (`bank`, `probe`, `challenge`), `source` (`bank`, `resume_claim`, `pressure`), `claim_id` (FK → resume_claims.id, SET NULL), `ladder_stage`, `difficulty`, `time_limit_seconds`, `generated_reason`, `created_at`.
11. **`interview_decisions`**:
    - `id` (PK), `session_id` (FK → interview_sessions.id, CASCADE), `turn`, `decision`, `reason`, `inputs` (JSON), `created_at`.
12. **`claim_consistency`**:
    - `id` (PK), `session_id` (FK → interview_sessions.id, CASCADE), `claim_id` (FK → resume_claims.id, CASCADE), `label` (`consistent`, `weak_support`, `low_consistency`, `insufficient_evidence`), `evidence` (JSON), `answers_considered`, `created_at`.
13. **`question_bank`**:
    - `id` (PK), `question_text`, `category`, `difficulty`, `role`.
14. **`interview_answers`**:
    - `id` (PK), `session_id` (FK → interview_sessions.id, CASCADE), `question_id`, `question_text`, `transcript`, `response_time`, `duration_seconds`, `wpm`, `filler_count`, `created_at`.
15. **`answer_evaluations`**:
    - `id` (PK), `answer_id` (FK → interview_answers.id, CASCADE), `structure_score`, `clarity_score`, `depth_score`, `technical_score`, `reasoning_score`, `star_score`, `consistency_score`, `overall_score`, `strengths` (JSON), `weaknesses` (JSON), `missing_concepts` (JSON), `suggestions` (JSON), `engine_used`, `prompt_version`, `verification_risk_score`, `verification_risk_level`, `verification_risk_evidence` (JSON), `verification_risk_explanation`.
16. **`voice_metrics`**:
    - `id` (PK), `answer_id` (FK → interview_answers.id, CASCADE, unique), `words_per_minute` (nullable), `filler_word_count`, `avg_pause_duration` (nullable), `longest_pause` (nullable), `pause_count` (nullable), `silence_ratio` (nullable), `vocabulary_diversity_score` (nullable), `speech_source` (`speech` | `typed`), `created_at`.
17. **`answer_visual_metrics`**:
    - `id` (PK), `answer_id` (FK → interview_answers.id, CASCADE, unique), `head_alignment_percent`, `blink_rate`, `head_movement_variance`, `face_visibility_ratio`, `head_shift_count`, `frames_sampled`, `created_at`.
18. **`behavioral_metrics`**:
    - `id` (PK), `session_id` (FK → interview_sessions.id, CASCADE), `eye_contact_percent` (nullable Float), `blink_rate` (nullable Float), `pause_rate` (Float).
19. **`session_scores`**:
    - `id` (PK), `session_id` (FK → interview_sessions.id, CASCADE), `behavioral_score` (nullable Float), `communication_score`, `technical_score`, `resume_consistency_score`, `consistency_source` (`claim_level` | `heuristic` | `legacy`), `readiness_score`, `strongest_category`, `weakest_category`, `insights` (JSON), `weights_used` (JSON), `created_at`.

---

## 5.3 Claim-Probe Ladder & Adaptive Question Engine

The interview intelligence layer enforces a deterministic 4-stage probe ladder grounded strictly in candidate resume claims:

```
+-----------------------------------------------------------------------------------+
|                            4-STAGE CLAIM PROBE LADDER                             |
+-----------------------------------------------------------------------------------+

     [ T1: FOUNDATION ]   ──(Score >= 70)──>   [ T2: TRADE-OFFS ]
      Architectural setup,                       Alternatives evaluated,
      stack selection & core mechanics           why this design was chosen
              |                                            |
         (Score < 60)                                 (Score < 60)
              v                                            v
     [ Consolidate / Retest ]                     [ Consolidate / Retest ]
              |                                            |
              +────────────────────────────────────────────+
                                   |
                             (Score >= 70)
                                   v
                         [ T3: INCIDENT ]
                          Production failure scenario,
                          rollback, data recovery
                                   |
                             (Score >= 70)
                                   v
                         [ T4: EDGE CASE ]
                          Cascading partition, silent
                          corruption, extreme load
```

### Adaptive Policy Decision Table

| State Trigger | Decision | Action / Output |
|---|---|---|
| `total_answers >= total_questions` | `COMPLETE_SESSION` | Terminates interview, triggers final score calculation |
| `mode == "pressure"` & trigger conditions met | `TRIGGER_CHALLENGE` | 45s timer, numeric validation or counterexample challenge |
| Previous question was probe & `score >= 70` | `ADVANCE_LADDER` | Advances claim to next ladder stage (T1 → T2 → T3 → T4) |
| Previous question was probe & `score < 60` | `PROBE_CLAIM` | Re-probes current ladder stage with targeted mechanism inquiry |
| Unprobed high-priority claim (`priority >= 0.55`) | `PROBE_CLAIM` | Initiates T1 probe on candidate's top-ranked resume claim |
| No claims pending | `NEXT_BANK_QUESTION` | Selects from QuestionBank matching candidate skills & adjusted difficulty |

---

### 5.4 Frontend Pages (`frontend/src/pages/`)

| Page | Route | Access | Description |
|---|---|:---:|---|
| **Landing** | `/` | Public | Hero section, value propositions, and 4-step workflow walkthrough. |
| **Sign In** | `/login` | Public | Email and password login with error boundary and redirect. |
| **Register** | `/register` | Public | Account registration enforcing password strength guidelines. |
| **Resume Upload** | `/resume` | Protected | PDF/text uploader, competency badges, role fit breakdown, risk areas, and flags. |
| **Interview Setup** | `/setup` | Protected | Mode selector, difficulty, role input, Privacy Consent Modal, and Safe Pressure Notice. |
| **Live Interview** | `/interview` | Protected | FaceMesh feed, speech recognition, live stats, adaptive `/next` question flow, mode switch button. |
| **Dashboard / Report**| `/dashboard` & `/report` | Protected | Main readiness gauge, subscore bars, voice cadence card, resume verification table, and decision log. |
| **Fix My Answer** | `/fix-answer` | Protected | Interactive AI response coach with STAR breakdown and vocabulary upgrade table. |
| **Session History** | `/history` | Protected | Paginated historical sessions log with report reopening and session deletion. |
| **Progress History** | `/progress` | Protected | Multi-session score trajectory line chart, aggregate averages, and session deletion. |

---

## 6. Complete API Reference

### Authentication & Privacy
- `POST /auth/register`: Creates account, hashes password with Argon2, sets httpOnly JWT cookie.
- `POST /auth/login`: Validates credentials, sets httpOnly JWT cookie.
- `POST /auth/logout`: Clears authentication cookie.
- `GET /auth/me`: Returns current user identity and profile.
- `GET/PUT /profile`: Returns or updates user profile preferences.
- `GET/POST /consent`: Retrieves or records privacy consent logs.
- `GET /auth/export`: Full JSON export of user profile, consent records, resumes, sessions, and all 8 intelligence tables.
- `DELETE /auth/account`: Permanently cascades deletion of user and all personal data after password re-verification.

### Resume Endpoints (User-Scoped)
- `POST /resume/upload`: Accepts `multipart/form-data` with `file` (PDF/TXT) or `raw_text`. Parses claims, projects, flags, role fit.
- `POST /resume/analyze`: Analyzes JSON payload containing `text` or existing `resume_id`.
- `POST /resume/{resume_id}/reanalyze`: Re-evaluates claims, projects, flags, role fit, and probe priorities.
- `GET /resume/{resume_id}`: Fetches stored resume profile by ID with extracted intelligence entities.
- `DELETE /resume/{resume_id}`: Permanently deletes resume and cascades intelligence rows.

### Interview Session Endpoints (User-Scoped)
- `POST /interview/start`: Initializes session with resume-aware question selection and mode time limits.
- `POST /interview/{session_id}/next`: Evaluates adaptive policy and generates next probe, challenge, or bank question.
- `POST /interview/{session_id}/switch-mode`: Relaxes session from Safe Pressure Mode to Practice Mode (90s limit).
- `GET /interview/history`: Paginated list of user's past interviews (newest first).
- `GET /interview/{session_id}`: Returns status, question count, and progress of session.
- `POST /interview/{session_id}/answer`: Submits answer with voice and extended visual metrics; evaluates rubric and verification risk.
- `POST /interview/followup`: Generates contextual follow-up question.
- `POST /interview/{session_id}/complete`: Finalizes interview, computes normalized scores, evaluates claim consistency.
- `DELETE /interview/{session_id}`: Deletes interview session and cascades child answers, evaluations, and voice/visual metrics.

### Analytics & Reports (User-Scoped)
- `GET /report/{session_id}`: Returns full performance report payload including radar chart points, voice metrics, verification risk evidence, claim consistency table, and adaptive decision log.
- `GET /progress`: Returns aggregated interview counts, averages, and multi-session trend history.

### Fix My Answer
- `POST /answer/improve`: Refactors weak answer into STAR framework with vocabulary upgrade suggestions.

---

## 7. How to Run the System

### 1. Prerequisites
- Linux OS (Ubuntu / Debian / Arch / Fedora)
- Python 3.10+ (tested with Python 3.12 and 3.14)
- Node.js 18+ and npm
- `pdftotext` (`sudo apt install poppler-utils`)

### 2. Backend Startup
```bash
cd Interview_System
source venv/bin/activate
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
*Backend will start on `http://127.0.0.1:8000`, run Alembic migrations automatically, and load questions.*

### 3. Frontend Startup
```bash
cd frontend
npm run dev
```
*Frontend will start on `http://localhost:5173`.*

---

## 8. Verification & Test Suite

The system includes a **57-test automated test suite** across unit, rubric scoring, LLM provider caching/fallback, authentication, user isolation, voice metrics, consent, and cascading deletion:
```bash
./venv/bin/pytest tests/
```
All 57 tests pass completely offline without external credentials in < 5 seconds.

To run a production frontend build check:
```bash
cd frontend
npm run build
```
*(Build compiles with zero errors).*

---

## 9. Privacy Architecture & Sensor Disclosure

The platform enforces strict privacy principles and clear disclosures regarding client-side and cloud-assisted processing:

1. **Local-Only Video Analysis**: Video frames are analysed locally inside the candidate's browser using MediaPipe FaceMesh. Raw video frames never leave the browser and are never uploaded or stored on any server. FaceMesh assets are bundled locally under `frontend/public/mediapipe/face_mesh` for 100% air-gapped / offline operation without CDN requests.
2. **Speech Recognition Disclosure**: Speech recognition is performed by the browser's native Web Speech API, which may process microphone audio on the browser vendor's cloud servers (e.g. Google's speech recognition backend in Chrome) under the vendor's privacy policy. Our application server never receives or stores raw audio recordings.
3. **Server Data Reception**: The backend server receives only final transcript text, timestamp intervals, and derived numerical metrics (e.g., WPM, filler word count, pause duration).
4. **Text-Only Fallback**: Candidates who decline sensor consent can practice fully in Text-Only mode, bypassing both camera and microphone sensors entirely.
5. **Consent Re-Prompting**: The privacy policy version is tracked (`PRIVACY_POLICY_VERSION = "2.0"`). Any version change prompts users to re-review and re-acknowledge privacy terms prior to starting a session.
6. **Data Retention & Right to be Forgotten**: All user data is retained strictly until deleted by the user. Endpoints `GET /auth/export` and `DELETE /auth/account` provide full GDPR/CCPA data export and complete cascading deletion.


