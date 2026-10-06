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
   - `id` (PK), `resume_id` (FK), `mode`, `difficulty`, `target_role`, `total_questions`, `current_question_index`, `followup_count`, `status`, `created_at`.
3. **`question_bank`**:
   - `id` (PK), `question_text`, `category`, `difficulty`, `role`.
4. **`interview_answers`**:
   - `id` (PK), `session_id` (FK), `question_id`, `question_text`, `transcript`, `response_time`, `duration_seconds`, `wpm`, `filler_count`, `created_at`.
5. **`answer_evaluations`**:
   - `id` (PK), `answer_id` (FK), `structure_score`, `clarity_score`, `depth_score`, `technical_score`, `reasoning_score`, `star_score`, `consistency_score`, `overall_score`, `strengths` (JSON), `weaknesses` (JSON), `missing_concepts` (JSON), `suggestions` (JSON), `dimensions` (JSON).
6. **`behavioral_metrics`**:
   - `id` (PK), `session_id` (FK), `eye_contact_percent` (nullable Float), `blink_rate` (nullable Float), `pause_rate` (Float).
7. **`session_scores`**:
   - `id` (PK), `session_id` (FK), `behavioral_score` (nullable Float), `communication_score`, `technical_score`, `resume_consistency_score`, `readiness_score`, `strongest_category`, `weakest_category`, `insights` (JSON), `weights_used` (JSON), `created_at`.

---

### 5.3 Frontend Pages (`frontend/src/pages/`)

| Page | Route | Description |
|---|---|---|
| **Landing** | `/` | Hero section, value propositions, and 4-step workflow walkthrough. |
| **Resume Upload** | `/resume` | PDF/text uploader, competency badges, clarity audit, and one-click interview launch. |
| **Interview Setup** | `/setup` | Mode selector, difficulty pills, target role input, question slider, and non-blocking camera check. |
| **Live Interview** | `/interview` | MediaPipe FaceMesh webcam feed, speech recognition, live WPM/filler stats, and instant rubric feedback. |
| **Dashboard / Report** | `/dashboard` & `/report` | Main readiness gauge, subscore bars, behavioral sensor stats, and question-by-question review. |
| **Fix My Answer** | `/fix-answer` | Interactive AI response coach with STAR breakdown and vocabulary upgrade table. |
| **Progress History** | `/progress` | Multi-session score trajectory line chart and historical sessions audit table. |

---

## 6. Complete API Reference

### Resume Endpoints
- `POST /resume/upload`: Accepts `multipart/form-data` with `file` (PDF/TXT) or `raw_text`. Returns parsed candidate profile JSON with score.
- `POST /resume/analyze`: Analyzes JSON payload containing `text` or existing `resume_id`.
- `GET /resume/{resume_id}`: Fetches stored resume profile by ID.

### Interview Session Endpoints
- `POST /interview/start`:
  - Request: `{ "mode": "technical", "difficulty": "medium", "number_of_questions": 3, "resume_id": 1, "target_role": "Backend Engineer" }`
  - Response: `{ "session_id": 1, "questions": [...] }`
- `GET /interview/{session_id}`: Returns status, question count, and progress of session.
- `POST /interview/{session_id}/answer`:
  - Request: `{ "session_id": 1, "question_id": 1, "question_text": "...", "transcript": "...", "response_time": 25.0, "wpm": 130.0, "filler_count": 1 }`
  - Response: `{ "score": 82.0, "technical_score": 85.0, "structure_score": 80.0, "strengths": [...], "weaknesses": [...], "suggestions": [...] }`
- `POST /interview/followup`:
  - Request: `{ "session_id": 1, "question_id": 1, "question": "...", "answer": "..." }`
  - Response: `{ "followup_question": "...", "followup_count": 1 }`
- `POST /interview/{session_id}/complete`:
  - Request: `{ "eye_contact_percent": 78.5, "blink_rate": 18.0, "pause_rate": 1.8 }`
  - Response: `{ "session_id": 1, "readiness_score": 76.5, "subscores": {...}, "insights": [...] }`

### Analytics & Reports
- `GET /report/{session_id}`: Returns full performance report payload including radar chart points and answer evaluations.
- `GET /progress`: Returns aggregated interview counts, averages, and multi-session trend history.

### Fix My Answer
- `POST /answer/improve`:
  - Request: `{ "question": "...", "answer": "...", "target_role": "Software Engineer" }`
  - Response: `{ "original_answer": "...", "weaknesses": [...], "improved_answer": "...", "explanation": "...", "star_breakdown": {...}, "vocabulary_suggestions": [...] }`

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

The system includes a 30-test automated test suite across unit, rubric scoring, LLM provider caching/fallback, and FastAPI route layers:
```bash
pytest tests/
# or directly with venv:
./venv/bin/pytest tests/
```
All 30 tests pass completely offline without external credentials in < 0.3 seconds.

To run a production frontend build check:
```bash
cd frontend
npm run build
```
*(Build compiles with zero errors).*

