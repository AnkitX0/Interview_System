# AI Interview Intelligence System

An end-to-end web-based platform for automated, multimodal candidate technical and behavioral mock interview assessments with rubric-based scoring, real-time computer vision cues, speech diagnostics, and actionable feedback loops.

---

## 1. Project Overview

The **AI Interview Intelligence System** bridges the gap between passive interview preparation and realistic, high-pressure interview evaluation. Candidates upload their resumes to extract technical proficiencies, engage in dynamic mock interviews with questions tailored to their background, receive multi-dimensional rubric scoring, analyze diagnostic behavioral indicators, and polish weak answers using the structured STAR framework.

---

## 2. Implemented Features (MVP)

### ✅ Fully Implemented (P0 / P1)
- **Resume Parsing & Intelligence Pipeline**:
  - Extracts text from uploaded PDF documents (using system `pdftotext` with pure-stream fallback) or raw text input.
  - Automatically identifies candidate name, education, experience, and categorized skills (Languages, Frameworks, Databases, Cloud & DevOps, Core Concepts).
  - Detects passive, weak, or vague statements and calculates a transparent resume score (0–100).
  - Outlines key candidate strengths, weak areas, and actionable recommendations.
  - Persists parsed profile directly to the database.
- **Resume-Aware Dynamic Interview Engine**:
  - Configurable interview rounds: Practice Mode, Technical Round, HR & Behavioral Round, and Pressure Incident Round.
  - Difficulty selection: Easy, Medium, Hard.
  - Target role customization (e.g. Software Engineer, Backend Specialist).
  - Prioritizes questions matching candidate resume competencies from an 80+ question database.
- **Multimodal Live Mock Interview**:
  - Interactive timer countdown per prompt.
  - Computer vision via MediaPipe FaceMesh to approximate eye contact stability and blink frequency.
  - Real-time speech-to-text transcription via Web Speech API with live speech cadence metrics (Words, WPM, and filler word detection: *um, uh, like, basically*).
  - Non-blocking camera pre-check with full text-mode fallback for environments without webcam or microphone access.
  - Live answer submission and immediate rubric evaluation cards.
- **Structured Rubric Scoring Engine**:
  - Rubric dimensions evaluated on each response (0–100):
    1. Structure & Flow
    2. Technical Depth
    3. Engineering Reasoning & Tradeoffs
    4. STAR Quality (Situation, Task, Action, Result)
    5. Resume Consistency
  - Normalized multi-dimensional session weights:
    $$\text{Final Readiness} = 0.30 \times \text{Communication} + 0.30 \times \text{Technical} + 0.20 \times \text{Behavioral} + 0.20 \times \text{Resume Consistency}$$
  - Transparent classification: Strongest Competency, Primary Growth Area, and Top 3 Actionable Insights.
- **Executive Performance Report Dashboard**:
  - Readiness Score gauge with readiness classification (Job-Ready, Near Interview-Ready, Needs Practice).
  - Recharts horizontal bar breakdowns and computer vision diagnostics summary.
  - Question-by-question review with individual transcripts, rubric scores, strengths, weaknesses, and direct **Fix This Answer** links.
- **Fix My Answer (AI Response Coach)**:
  - Takes candidate answers and diagnoses flaws (passive verbs, missing metrics, lack of STAR structure).
  - Generates a polished, senior-level STAR response that strictly preserves the candidate's authentic experience without fabricating fictional achievements.
  - Provides a 4-part STAR breakdown and before/after vocabulary upgrade recommendations.
- **User Authentication & Multi-Tenancy (Phase 2)**:
  - Argon2 password hashing (minimum 10 characters, rejects trivially weak passwords).
  - Secure httpOnly, SameSite=Lax JWT cookie transport (`interview_auth`).
  - Strict resource ownership isolation across all routes (cross-user access returns uniform `404 Not Found`).
  - Account profile pre-filling target role and experience level.
  - Legacy data claiming utility script: `python scripts/claim_legacy_data.py --email <user@example.com>`.
- **Per-Answer Voice Metrics & Cadence Tracking (Phase 2)**:
  - Web Speech event timing approximates speech segment intervals without word-level audio leakage.
  - Computes Words Per Minute (WPM), verbal filler word counts, pause count, average pause duration, longest pause, and silence ratio.
  - Length-guarded Moving-Average Type-Token Ratio (MATTR) for vocabulary diversity (guarded against short responses < 20 words).
  - Transparent display-only contract (`USE_VOICE_METRICS_IN_SCORE = False` ensures readiness scores remain 100% stable).
  - All metrics labeled: *"approximate, based on speech-recognition timing"*.
  - For typed responses, audio cadence metrics are reported as `null` ("Not measured"), never zeroed or fabricated.
- **Privacy Consent, Right to be Forgotten & Data Export (Phase 2)**:
  - Sensor Processing & Privacy Choice modal before camera/mic activation.
  - One-click Text-Only Mode fallback that completely avoids camera/mic permission requests.
  - Data retention guarantee: *"Your data is kept until you delete it."*
  - Cascading session and resume deletion (`DELETE /interview/{session_id}`, `DELETE /resume/{resume_id}`).
  - Account deletion with password confirmation (`DELETE /auth/account`) permanently removing all user data and child rows.
  - Complete data portability export (`GET /auth/export`) per GDPR/CCPA principles.
- **Intelligence Layer: Claim-Probe Ladder, Verification Risk & Safe Pressure Mode (Phase 3)**:
  - **Resume Intelligence Upgrade**:
    - Normalized entity tables (`resume_skills`, `resume_projects`, `resume_claims`, `resume_flags`).
    - Evaluates role fit against 4 engineering profiles (`Backend`, `Frontend`, `Fullstack`, `DevOps`).
    - Computes claim probe priorities (0.0 to 1.0) and highlights interview risk areas.
    - Explicit re-analysis endpoint: `POST /resume/{id}/reanalyze`.
  - **Deterministic Claim-Probe Ladder & Adaptive Engine**:
    - 4-stage technical verification ladder: `T1_FOUNDATION` → `T2_TRADE_OFFS` → `T3_INCIDENT` → `T4_EDGE_CASE`.
    - `POST /interview/{session_id}/next` dynamically selects next question based on performance and claim priorities.
    - Rolling difficulty adjustments (`easy`, `medium`, `hard`) based on 3-turn moving average score.
    - Full decision transparency logged in `interview_decisions` and shown on the dashboard.
  - **Per-Answer Verification Risk Engine**:
    - Computes verification risk level (`low`, `moderate`, `elevated`, `not_computed` for answers < 20 words).
    - Observable indicators: buzzword-to-specifics ratio, lack of technical mechanisms, excessive repetition across answers, and ownership vagueness.
    - Strict non-accusatory language contract without banned terms.
  - **Claim Consistency & Dynamic Session Consistency Scoring**:
    - Evaluates candidate answers against declared resume claims (`consistent`, `weak_support`, `low_consistency`, `insufficient_evidence`).
    - Sets `session_scores.consistency_source = "claim_level"` when claim evidence is available.
  - **Safe Pressure Mode**:
    - Shorter response countdown (default 45s vs 90s) with fast-cadence technical incident challenges.
    - Setup notice with mandatory candidate acknowledgement.
    - Always-visible "Switch to practice mode" button (`POST /interview/{session_id}/switch-mode`) relaxing timer to 90s without penalty.
    - Strict rubric invariance: identical answers receive identical grading across all modes.
  - **Extended Visual Metrics & Quality Gating**:
    - Captures per-answer client-side FaceMesh aggregates (`head_alignment_percent`, `blink_rate`, `head_movement_variance`, `face_visibility_ratio`, `head_shift_count`, `frames_sampled`).
    - Persisted in `answer_visual_metrics`.
    - Quality gate: `face_visibility_ratio < 0.60` or `frames_sampled < 30` marks metrics as low confidence / unmeasured.
    - Display-only contract (`USE_EXTENDED_VISUAL_METRICS_IN_SCORE = False`).
  - **Optional LLM Probe Phrasing**:
    - LLM used strictly for phrasing probe questions more naturally, never for decision flow or policy.
    - Strict claim grounding, timeout guards, and deterministic template fallback.
- **Progress & Session History Tracking**:
  - Historical session audit log (`/history` and `/progress`) with date, mode, difficulty, readiness scores, deep-link report views, and session deletion.
  - Multi-line trend chart tracking Readiness, Technical Depth, Communication, and Behavioral signals across consecutive mock interviews.
  - Clean empty state with zero fabricated user data.

---

## 3. Tech Stack

- **Backend**: Python 3.12+ / 3.14, FastAPI, SQLAlchemy 2, Alembic, SQLite (`interview.db`), Pydantic v2, Argon2-cffi, PyJWT, Poppler `pdftotext`, Uvicorn.
- **Frontend**: React 19, Vite 7, React Router 7, Recharts, MediaPipe FaceMesh & Camera Utils, Web Speech API.
- **Architecture**: Modular Monolith Service Layer (`auth_service`, `voice_service`, `resume_service`, `adaptive_engine`, `verification_risk`, `claim_consistency_service`, `visual_metrics_service`, `probe_rephraser`, `scoring_engine`, `question_selector`, `answer_improvement_service`, `evaluation_engine`, `followup_generator`).

---

## 4. Architecture Overview

```
Frontend (React 19 / Vite)
  ├── Public Routes: Landing (/), Login (/login), Register (/register)
  ├── Protected Routes (ProtectedRoute):
  │     ├── Resume Intelligence (/resume) [Role Fit & Risk Areas]
  │     ├── Interview Setup (/setup) [Consent Modal & Safe Pressure Notice]
  │     ├── Live Mock Interview (/interview) [FaceMesh, Web Speech / Text-Only Mode, Adaptive /next]
  │     ├── Performance Report (/dashboard & /report) [Rubric Evidence, Verification Risk & Claim Audit]
  │     ├── Fix My Answer (/fix-answer)
  │     ├── Session History (/history)
  │     └── Progress Growth (/progress)
         │
         │ REST API (Credentials Included / httpOnly JWT Cookie)
         ▼
FastAPI Backend (Port 8000)
  ├── Authentication & Scoping: Argon2 Hashing, JWT httpOnly Cookie, Rate Limiter
  ├── Routes:
  │     ├── /auth       (Register, login, logout, me, export, delete account)
  │     ├── /profile    (Get, update candidate profile)
  │     ├── /consent    (Get, record privacy consent logs)
  │     ├── /resume     (Upload, parse, audit, score, reanalyze, delete)
  │     ├── /interview  (Start, next, switch-mode, answer, followup, complete, delete)
  │     ├── /report     (Detailed session analytics, voice metrics, rubric evidence, claim verification)
  │     ├── /answer     (STAR refactoring & vocabulary upgrade)
  │     └── /progress   (Cross-session metrics & trajectory)
  ├── Services:
  │     ├── auth_service.py (Argon2, JWT, rate limiting)
  │     ├── adaptive_engine.py (4-stage probe ladder & rolling difficulty)
  │     ├── verification_risk.py (Observable evidence signals & risk scoring)
  │     ├── claim_consistency_service.py (Claim consistency & derived scoring)
  │     ├── visual_metrics_service.py (Quality gating & per-answer storage)
  │     ├── probe_rephraser.py (Optional grounded LLM probe phrasing)
  │     ├── voice_service.py (Cadence, pauses, MATTR diversity)
  │     ├── resume_service.py (Role profiles, claim & flag extraction)
  │     ├── scoring_engine.py (Rubric formulas & re-normalization)
  │     ├── question_selector.py (Question bank selection)
  │     └── answer_improvement_service.py (STAR engine)
  └── Database & Migrations:
        ├── Alembic Migrations (0001 initial, 0002 auth, 0003 intelligence layer)
        └── SQLite (interview.db / PostgreSQL-ready SQLAlchemy models with cascading deletion)
```

---

## 5. Setup & Installation

### Prerequisites
- Python 3.10+ (tested with Python 3.12 and 3.14)
- Node.js 18+ and npm
- `pdftotext` (available on Linux via `sudo apt install poppler-utils`)

---

## 6. How to Run

### Backend Startup

1. Open a terminal in the project root:
   ```bash
   cd Interview_System
   ```
2. Activate your virtual environment:
   ```bash
   source venv/bin/activate
   ```
3. Run migrations and start the FastAPI server on port 8000:
   ```bash
   uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   *The backend will automatically initialize `interview.db`, run Alembic migrations to head, and load the pre-seeded question bank.*

4. *(Optional)* Claim unassigned legacy pre-Alembic data for an account:
   ```bash
   python scripts/claim_legacy_data.py --email your_email@example.com
   ```

### Frontend Startup

1. Open a second terminal:
   ```bash
   cd frontend
   ```
2. Start the Vite development server:
   ```bash
   npm run dev
   ```
3. Open your browser at:
   ```
   http://localhost:5173
   ```

---

## 7. Running Tests

Run the complete backend test suite:
```bash
./venv/bin/pytest tests/
```
All **107 automated unit, scoring, auth, user isolation, voice metrics, consent, migration, probe ladder, verification risk, safe pressure, and visual metrics tests** execute completely offline with zero API keys.

Run the frontend production build check:
```bash
cd frontend && npm run build
```

---

## 8. Environment Variables

All core functionality operates **100% deterministically and offline without requiring external API keys**.

Configuration parameters in `backend/config.py` (overridable via environment):
```env
# Security & Auth
SECRET_KEY="your-random-secret-key"
AUTH_COOKIE_NAME="interview_auth"
ACCESS_TOKEN_EXPIRE_MINUTES="60"
ENVIRONMENT="development"  # set to 'production' for Secure cookies

# Optional external LLM providers (graceful fallback active if omitted)
GEMINI_API_KEY=""
OPENAI_API_KEY=""
```

Frontend environment configuration (`frontend/.env.example`):
```env
VITE_API_URL=http://127.0.0.1:8000
```

---

## 9. API Overview

| Method | Endpoint | Description | Scoped |
|---|---|---|:---:|
| `POST` | `/auth/register` | Register account with Argon2 hashing & set JWT cookie | No |
| `POST` | `/auth/login` | Authenticate credentials & set JWT cookie | No |
| `POST` | `/auth/logout` | Clear authentication cookie | No |
| `GET`  | `/auth/me` | Current authenticated user and profile | Yes |
| `GET/PUT` | `/profile` | Get or update user profile preferences | Yes |
| `GET/POST`| `/consent` | Retrieve or record privacy consent logs | Yes |
| `GET`  | `/auth/export` | Complete GDPR/CCPA data export including all intelligence tables (JSON) | Yes |
| `DELETE`| `/auth/account` | Permanently delete account with password re-check | Yes |
| `POST` | `/resume/upload` | Upload PDF/text, extract claims & projects, audit resume | Yes |
| `POST` | `/resume/analyze` | Analyze provided resume text or fetch profile | Yes |
| `POST` | `/resume/{id}/reanalyze` | Re-run full entity, role fit, and probe priority extraction | Yes |
| `DELETE`| `/resume/{id}` | Permanently delete stored resume and intelligence rows | Yes |
| `POST` | `/interview/start` | Initialize session with resume-aware questions & timer | Yes |
| `POST` | `/interview/{session_id}/next` | Deterministic adaptive next-question policy & ladder advancement | Yes |
| `POST` | `/interview/{session_id}/switch-mode` | Switch from Safe Pressure Mode to Practice Mode (relaxes to 90s) | Yes |
| `GET`  | `/interview/history`| Paginated list of past interviews (newest first) | Yes |
| `POST` | `/interview/{session_id}/answer` | Submit answer with voice and extended visual metrics | Yes |
| `POST` | `/interview/followup` | Generate contextual follow-up question | Yes |
| `POST` | `/interview/{session_id}/complete`| Finalize interview & compute normalized scores | Yes |
| `DELETE`| `/interview/{session_id}`| Delete interview and cascade child rows | Yes |
| `GET`  | `/report/{session_id}` | Retrieve report with observable rubric evidence & claim verification | Yes |
| `POST` | `/answer/improve` | Refactor weak answer into STAR framework | Yes |
| `GET`  | `/progress` | Fetch cross-session score trajectories | Yes |

---

## 10. Privacy Guarantees & Sensor Disclosure

- **Video Processing**: Video frames are analysed locally and never leave the browser. Head alignment and visual stability proxies are computed on-device via MediaPipe FaceMesh. Raw video is never recorded or uploaded to our server.
- **Speech Recognition**: Speech recognition is performed by the browser's own speech service (Web Speech API), which may process audio on the vendor's servers under its own privacy policy.
- **Server Data Processing**: Our server receives only transcript text, timing intervals, and derived numbers. Raw video and raw audio files are never stored or uploaded to our server.
- **Text-Only Fallback**: Text-only mode avoids both video and speech processing entirely.
- **Data Retention**: *Your data is kept until you delete it.* You can delete any session, resume, or your entire account at any time via the UI or `/auth/account` deletion endpoints.
- **Honest Metrics**: Physical indicators are reported as observable proxies:
  - Head alignment is a *visual centering proxy*, not a measure of confidence, eye contact, or nervousness.
  - Voice pacing and pause intervals are *approximations based on speech-recognition event timing*.
  - Verification risks are *observable consistency indicators*, never accusations of dishonesty.


