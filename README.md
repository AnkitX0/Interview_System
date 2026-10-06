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
- **Progress & Session History Tracking**:
  - Historical session audit log with date, mode, difficulty, readiness scores, and deep-link report views.
  - Multi-line trend chart tracking Readiness, Technical Depth, Communication, and Behavioral signals across consecutive mock interviews.
  - Clean empty state with zero fabricated user data.

### 🟡 Partially Implemented
- **Speech Audio Archival**: Audio chunks recorded via browser `MediaRecorder` are buffered client-side; transcripts are parsed and scored server-side.
- **Contextual Follow-ups**: Follow-up prompt generator evaluates response length, metrics, and tradeoff keywords to probe deeper on weak responses.

### 🔮 Future Work (P2)
- Server-side Whisper transcription pipeline for offline voice recordings.
- Emotion & micro-expression detection (roadmap explicitly cautions against overclaiming emotion AI in HR contexts).
- Company-specific question sets (e.g., Google, Amazon, Meta behavioral loops).

---

## 3. Tech Stack

- **Backend**: Python 3.12+ / 3.14, FastAPI, SQLAlchemy, SQLite, Pydantic, Poppler `pdftotext`, Uvicorn.
- **Frontend**: React 19, Vite, React Router 7, Recharts, MediaPipe FaceMesh & Camera Utils, Web Speech API.
- **Architecture**: Modular Service Layer (`resume_service`, `scoring_engine`, `question_selector`, `answer_improvement_service`, `evaluation_engine`, `followup_generator`).

---

## 4. Architecture Overview

```
Frontend (React 19 / Vite)
  ├── Landing (/)
  ├── Resume Intelligence (/resume)
  ├── Interview Setup (/setup)
  ├── Live Mock Interview (/interview)
  │     ├── FaceMesh Computer Vision
  │     └── Web Speech Recognition
  ├── Performance Report (/dashboard & /report)
  ├── Fix My Answer (/fix-answer)
  └── Progress History (/progress)
         │
         │ REST API (JSON / FormData)
         ▼
FastAPI Backend (Port 8000)
  ├── Routes:
  │     ├── /resume     (Upload, parse, audit, score)
  │     ├── /interview  (Start, answer, evaluate, followup, complete)
  │     ├── /report     (Detailed session analytics & review)
  │     ├── /answer     (STAR refactoring & vocabulary upgrade)
  │     └── /progress   (Cross-session metrics & trajectory)
  ├── Services:
  │     ├── resume_service.py
  │     ├── scoring_engine.py (Rubric formulas)
  │     ├── question_selector.py (Resume skill matching)
  │     └── answer_improvement_service.py (STAR engine)
  └── Database:
        └── SQLite (interview.db)
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
3. Start the FastAPI server on port 8000:
   ```bash
   uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   *The backend will automatically initialize `interview.db`, apply Alembic migrations to head, and load the pre-seeded question bank.*

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

Run the backend test suite:
```bash
pytest tests/
```
Or directly using the virtual environment:
```bash
./venv/bin/pytest tests/
```
All 30 unit, scoring rubric, API, and guarded LLM evaluation tests run completely offline with zero API keys in < 0.3s.

Run the frontend production build check:
```bash
cd frontend && npm run build
```

---

## 8. Environment Variables

All core functionality operates **100% deterministically and offline without requiring external API keys**.

Optional external AI enhancements can be supplied in a `.env` file or environment:
```env
# Optional external LLM providers (graceful fallback active if omitted)
GEMINI_API_KEY=""
OPENAI_API_KEY=""
```

---

## 9. API Overview

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/resume/upload` | Upload PDF or raw text, parse skills, audit, and save resume profile |
| `POST` | `/resume/analyze` | Analyze provided resume text or retrieve stored candidate profile |
| `POST` | `/interview/start` | Initialize session with resume-aware question selection |
| `POST` | `/interview/{session_id}/answer` | Submit answer transcript for structured rubric evaluation |
| `POST` | `/interview/followup` | Generate contextual follow-up question based on answer |
| `POST` | `/interview/{session_id}/complete`| Finalize interview, compute weighted scores, save metrics |
| `GET`  | `/report/{session_id}` | Retrieve comprehensive performance report and answer reviews |
| `POST` | `/answer/improve` | Refactor weak answer into STAR framework with vocabulary upgrades |
| `GET`  | `/progress` | Fetch aggregated session counts, averages, and score trend data |

---

## 10. Demo Workflow

1. **Landing Page (`/`)**: Overview of the platform with direct calls to action.
2. **Resume Analysis (`/resume`)**: Upload a resume PDF or paste text. Review extracted competencies, audit score, strengths, and weak areas. Click **"Proceed to Interview Setup with this Profile"**.
3. **Interview Setup (`/setup`)**: See your attached resume profile. Configure mode, difficulty, target role, and question count. Test or skip the camera check. Click **"Begin Mock Interview"**.
4. **Live Interview Screen (`/interview`)**: View timer, question, and webcam feed. Click **"Start Speech-to-Text"** or type an answer. Submit for immediate rubric feedback. Progress through questions and complete the interview.
5. **Performance Report (`/dashboard`)**: Inspect your overall Readiness Score, subscore breakdown bars, computer vision behavioral indicators, insights, and question reviews.
6. **Fix My Answer (`/fix-answer`)**: Click **"Fix This Answer"** on any response in the report to see an AI-refactored STAR version, weaknesses audit, and vocabulary upgrades.
7. **Progress History (`/progress`)**: View your historical mock interview sessions, multi-session score trajectory, and performance growth over time.

