# Interview Intelligence — Preparation System
## Production Architecture, System Deep Dive & Faculty Defense Guide

---

## 1. Project Overview

### What the System Does
The **Interview Intelligence Preparation System** is an evidence-based, multimodal interview preparation and analytics platform. It guides candidates through the end-to-end interview lifecycle: extracting verified technical claims and projects from their resumes, conducting adaptive, conversational technical and behavioral mock interviews with computer vision and live voice capture, evaluating answers against structured engineering rubrics, and synthesizing longitudinal study reports paired with targeted practice drills.

### Why It Exists & The Problem It Solves
Traditional technical interview preparation relies either on static question-and-answer flashcards (e.g., LeetCode, static question lists) or unstructured conversational chatbots (e.g., generic ChatGPT prompts). Both approaches suffer from fundamental educational weaknesses:
1. **Lack of Conversational Continuity**: Chatbots lack session memory, fail to challenge candidate diversions, and do not press candidates to explain architectural tradeoffs or justify specific technologies.
2. **Hallucination & Lack of Resume Grounding**: General AI chatbots often invent technologies or ask generic trivia unrelated to what the candidate actually built.
3. **Uncalibrated Scoring & Fake Precision**: Many tools output arbitrary scores (e.g., "Confidence: 94%") based on unscientific sentiment analysis or facial emotion recognition.
4. **Disjointed Practice Loop**: Candidates receive scores without diagnostic study materials (e.g., missing metrics, model answers, and targeted drills).

### Who Uses It
- **University Students & Job Seekers**: Preparing for technical, behavioral, and high-urgency system design rounds.
- **Career Mentors & Faculty**: Evaluating student readiness using verifiable answer transcripts rather than opaque scores.

### What Makes It Different
- **Evidence-Gated Assessment**: Incomplete or skipped answers are marked as missing evidence rather than penalized with an artificial zero score.
- **Separation of Authoritative Application Logic from LLM Reasoning**: Deterministic code manages session state, exposure tracking, turn counters, and grading rubrics; Gemini is reserved for semantic understanding, claim extraction, and explanatory synthesis.
- **Honest Computer Vision**: Uses MediaPipe to measure observable geometric signals (face alignment, blink frequency, single-person framing) without claiming pseudoscientific "emotion detection" or "lie detection."
- **Resilient Real-Time Voice-to-Text**: Continuous Web Speech state machine with transcript deduplication, mixed typing support, and automated server-side fallback.

---

## 2. Complete Architecture

The platform follows a layered, modular client-server architecture:

```
+----------------------------------------------------------------------------------------------------+
|                                    CANDIDATE CLIENT (BROWSER)                                      |
|                                                                                                    |
|  [ React 18 SPA + Vite ]   • Theme System (Vintage Editorial Paper / Dark Workstation)             |
|  [ MediaPipe FaceMesh ]    • Local Single-Person Geometry (1 Face Valid / 2+ Faces Red Warning)     |
|  [ Web Speech API ]        • Continuous State Machine Hook (Deduplication + Mixed Typing Sync)     |
+-------------------------------------------------+--------------------------------------------------+
                                                  | HTTP / HTTPS (REST API)
                                                  v
+----------------------------------------------------------------------------------------------------+
|                                  FASTAPI APPLICATION GATEWAY (PORT 8001)                           |
|                                                                                                    |
|  [ CORS & Security ]       • Origin Validation, CSRF Defense, HttpOnly Cookie Authentication      |
|  [ Routes ]                • /auth, /resume, /interview, /practice, /readiness, /analytics, /health |
|  [ Health Checks ]         • Liveness & Readiness endpoints for container orchestration           |
+-------------------------------------------------+--------------------------------------------------+
                                                  |
         +----------------------------------------+----------------------------------------+
         |                                        |                                        |
         v                                        v                                        v
+-----------------------+              +-----------------------+              +------------------------+
|   BUSINESS SERVICES   |              |  EVALUATION ENGINES   |              |  DATABASE PERSISTENCE  |
|                       |              |                       |              |                        |
| • Resume Parser       |              | • Deterministic Rubric|              | • SQLAlchemy ORM       |
| • Claim Extractor     |              | • Verification Risk   |              | • SQLite (Dev/Docker)  |
| • Adaptive Engine     |              | • Voice & Vision Gate |              | • PostgreSQL (Prod)    |
| • Question Exposure   |              | • Gemini LLM Fallback |              | • 12 Relational Tables |
| • Practice Recommender|              | • Report Synthesizer  |              |                        |
+-----------------------+              +-----------------------+              +------------------------+
```

---

## 3. Technology Stack

| Technology | Role | Justification |
| :--- | :--- | :--- |
| **React 18** | Frontend Library | Component lifecycle control, hooks for camera streams, speech events, and reactive UI state. |
| **Vite** | Frontend Tooling | Instant HMR, clean ES module production bundling, and fast compilation. |
| **FastAPI** | Backend Framework | High-performance Python async framework with native Pydantic validation, OpenAPI docs, and clean dependency injection. |
| **Python 3.12+** | Backend Language | Rich ecosystem for document extraction, data science, and LLM orchestration. |
| **SQLAlchemy 2.0** | ORM Layer | Robust relational mapping, explicit transaction control, and database portability (SQLite to PostgreSQL). |
| **MediaPipe** | Computer Vision | Runs 100% locally in candidate's browser via WebAssembly, guaranteeing zero video transmission to servers and candidate privacy. |
| **Web Speech API** | Voice Input | Zero-latency, browser-native speech recognition without expensive third-party streaming fees. |
| **Google Gemini API** | Contextual LLM | High-speed contextual reasoning for claim extraction, follow-up probe formulation, and study answer generation. |
| **Docker & Compose** | Containerization | Standardized single-command build (`docker compose up --build`) ensuring identical behavior across student and faculty machines. |
| **Pytest** | Testing | 196+ automated tests verifying scoring math, state persistence, question exposure, and API contracts. |

---

## 4. Frontend Architecture

### Directory Structure & Responsibilities
- `src/pages/`: Page-level components corresponding to application routes:
  - `Dashboard.jsx`: Overall readiness trajectory, active recommendations, and recent completed sessions.
  - `Interview.jsx`: Core conversational interview loop, camera stream with bounding box, live speech transcription, and authoritative turns stream.
  - `Report.jsx`: "Your Interview Review" study cards, what went well, missing concepts, model answers, and resume claim verifications.
  - `Profile.jsx`: Comprehensive candidate biodata, professional links with URL validation, and resume synchronization.
  - `Practice.jsx`: Dedicated practice hub with 7 specialized drill modules.
  - `ResumeUpload.jsx`: PDF upload, text extraction, validation, and claim preview.
  - `History.jsx`: Paginated table of sessions distinguishing completed, incomplete, and unassessed sessions.
- `src/utils/`:
  - `useSpeechRecognition.js`: Continuous speech-to-text hook with state machine, microphone permission checking, live interim/final merging, deduplication, and mixed typing sync.
  - `cameraTrackingLogic.js`: Single-person classification (`NO_FACE`, `ONE_FACE`, `MULTIPLE_FACES`), bounding box computation, and visual coverage calculation.
  - `profileCompletenessLogic.js`: Deterministic 100-point profile completeness score.
  - `api.js`: Wrapper around `fetch` injecting authorization headers and credentials.
- `src/styles/`:
  - `tokens.css`: Design tokens defining the **Vintage Editorial + Modern Study Platform** aesthetic (warm ivory `#F5F1E8`, soft parchment `#FBF9F4`, espresso `#2A211C`, terracotta `#9A6048`, olive `#69705A`, and dark workstation palette).
  - `global.css`: Typography, layout, and responsive grid utilities.

---

## 5. Backend Architecture

### Modular Organization
- `backend/main.py`: Application entrypoint, CORS configuration, CSRF middleware, centralized error handlers, and route registration.
- `backend/routes/`:
  - `auth.py`: Candidate registration, password hashing (bcrypt), JWT issuance, and cookie management.
  - `resume.py`: PDF upload, text extraction (pdfplumber/pdftotext), deterministic skills extraction, and Gemini claim extraction.
  - `interview.py`: Session initialization, authoritative persisted turns retrieval (`GET /interview/{id}/turns`), answer submission, skip handling, next question adaptation, and session finalization.
  - `practice.py`: Practice drill launcher and category-specific question pools.
  - `readiness.py`: Longitudinal readiness score calculation and historical trend lines.
  - `analytics.py`: Cross-session weakness tracking, radar chart metrics, and progress summaries.
- `backend/services/`:
  - `adaptive_engine.py`: Dynamic question selection based on candidate weaknesses, follow-up ladder, and interview policy.
  - `question_bank.py`: Curated question taxonomy across 7 distinct categories with deterministic ID exposure tracking.
  - `evaluation_service.py`: Rubric-based answer evaluation with deterministic baseline scoring and Gemini qualitative synthesis.
  - `gemini_service.py`: Resilient Gemini API integration with timeout guards, structured schemas, and fallback defaults.
  - `scoring_service.py`: Multi-dimensional readiness aggregation with camera weighting normalization.

---

## 6. Database Architecture

The system utilizes 12 relational models mapped via SQLAlchemy:

```
+-------------------+        1:1        +-------------------+
|       User        | ----------------> |    UserProfile    |
+-------------------+                   +-------------------+
          | 1:N
          v
+-------------------+        1:N        +-------------------+
|      Resume       | ----------------> |    ResumeClaim    |
+-------------------+                   +-------------------+
          | 1:N
          v
+-------------------+        1:N        +-------------------+
| InterviewSession  | ----------------> |  InterviewAnswer  |
+-------------------+                   +-------------------+
     |           |                                | 1:1
     | 1:1       | 1:N                            v
     v           v                      +-------------------+
+-----------+ +-------------------+     | AnswerEvaluation  |
|SessionScore| | InterviewDecision |     +-------------------+
+-----------+ +-------------------+               | 1:1
                                                  v
                                        +-------------------+
                                        |   VoiceMetrics    |
                                        +-------------------+
                                                  | 1:1
                                                  v
                                        +-------------------+
                                        |   VisualMetrics   |
                                        +-------------------+
```

### Key Models & Fields
1. **`User`**: Account identity (`email`, `password_hash`, `full_name`, `created_at`).
2. **`UserProfile`**: Structured candidate biodata (`target_role`, `experience_level`, `bio`, `education_degree`, `education_university`, `graduation_year`, `skills_languages`, `skills_frameworks`, `skills_databases`, `skills_tools`, `linkedin_url`, `github_url`, `leetcode_url`, `portfolio_url`).
3. **`Resume`**: Candidate resume document (`raw_text`, `skills`, `projects`, `experience`, `parsed_claims`, `resume_score`).
4. **`ResumeClaim`**: Extracted claims with verification status (`claim_text`, `claim_type`, `technology`, `metric`, `probe_priority`, `verification_status`).
5. **`InterviewSession`**: Interview state (`user_id`, `resume_id`, `mode`, `difficulty`, `status`, `current_question_index`, `question_mode`, `session_policy`).
6. **`InterviewAnswer`**: Persisted turns (`session_id`, `question_id`, `question_text`, `transcript`, `response_time`, `duration_seconds`, `wpm`, `answer_status`, `evaluation_status`, `score`).
7. **`AnswerEvaluation`**: Multi-dimensional grading (`structure_score`, `technical_score`, `reasoning_score`, `consistency_score`, `overall_score`, `strengths`, `weaknesses`, `missing_concepts`, `suggestions`, `improved_answer`).
8. **`SessionScore`**: Final synthesized session outcome (`readiness_score`, `technical_score`, `communication_score`, `behavioral_score`, `delivery_measured`).
9. **`QuestionExposure`**: Cross-session memory preventing question repetition (`user_id`, `question_id`, `category`, `last_exposed_at`).

---

## 7. Resume Intelligence Pipeline

```
PDF File Upload
      ↓
PDF Sanitization & Validation (Size <= 5MB, Valid MIME type)
      ↓
Text Extraction (pdfplumber primary -> pdftotext fallback)
      ↓
Deterministic Parsing:
  • Contact info regex
  • Standard technology taxonomy matching (Python, React, PostgreSQL, Docker, etc.)
  • Structural section extraction (Skills, Experience, Projects, Education)
      ↓
LLM Claim & Metric Extraction (Gemini Structured Output):
  • Specific technical claims (e.g., "Reduced latency by 40%")
  • Architecture claims (e.g., "Migrated monolith to microservices")
  • Probe priority assignment (High priority on quantitative claims)
      ↓
Interview Probe Seed Generation:
  • Candidate claim: "Optimized database queries by 35%"
  • Generated probe: "How did you measure the 35% latency drop, and what indexing strategy did you use?"
```

---

## 8. Question Generation & Taxonomy

### The 7 Curated Question Pools
1. **Technical Deep Dive**: Core architecture, internals, memory, and database concurrency.
2. **Trade-off Reasoning**: Comparative engineering decisions (SQL vs. NoSQL, Sync vs. Async).
3. **Follow-up & Probe Defense**: Handling architectural edge cases and concurrent request failures.
4. **Project & Claim Defense**: Grounded verification of candidate's stated resume accomplishments.
5. **Structured Communication**: Explaining technical systems clearly to non-technical stakeholders.
6. **Behavioral Scenarios**: STAR-framework situational questions (conflicts, outages, failures).
7. **High-Urgency Pressure**: 45-second incident response and triage scenarios.

### Cross-Session Exposure Tracking
Questions are never selected purely at random. The `QuestionExposure` table tracks every question previously presented to the candidate. When selecting the next question:
1. Questions exposed within the last 5 sessions are deprioritized.
2. If a candidate previously demonstrated a weakness in a topic (e.g., Database Transactions), the system does **not** repeat the identical question. Instead, it selects a **different question assessing the same competency** at a matching or higher difficulty.

---

## 9. Adaptive Interview Engine

During live sessions, the interviewer does not follow a blind static script. At each turn, `decide_next_question` evaluates:
- **Candidate Diversion**: Did the candidate answer the question or evade it? If evaded, the system re-anchors to the unresolved topic.
- **Evidence Sufficiency**: Was the answer strong and thorough? If yes, advance to higher complexity or architectural tradeoffs. If weak, probe foundational understanding.
- **Resume Verification**: Seamlessly interleave probes verifying candidate resume claims.
- **Session Policy**: Adheres to the target budget (e.g., 5 questions) before gracefully concluding.

---

## 10. Answer Evaluation & Grading Rubric

Evaluation combines deterministic rubric grading with qualitative LLM feedback:

| Dimension | Weight | Evaluation Criteria |
| :--- | :---: | :--- |
| **Technical Accuracy** | 35% | Correctness of technical concepts, protocols, data structures, and algorithms. |
| **Architectural Reasoning** | 25% | Articulation of tradeoffs, boundary conditions, edge cases, and failure modes. |
| **Communication Structure** | 25% | Clarity, concise pacing (target 110–160 WPM), absence of filler loops. |
| **Resume Consistency** | 15% | Alignment between submitted answer and claimed experience levels. |

### Empty & Skipped Answer Policy
- **Empty or Partial Answers (< 3 words)**: Marked as `EMPTY` / `PARTIAL`, assigned `score = None`, `evaluation_status = "NOT_APPLICABLE"`.
- **Skipped Answers**: Marked as `SKIPPED`, assigned `score = None`, `evaluation_status = "NOT_APPLICABLE"`.
- **Readiness Score Exclusion**: Unanswered turns are **never** averaged in as a zero score; they are treated as an evidence gap.

---

## 11. Speech-to-Text Pipeline

```
[Candidate clicks Start Speaking]
               ↓
navigator.mediaDevices.getUserMedia({ audio: true })
               ↓
Web Speech API (webkitSpeechRecognition) Initialized:
  • continuous: true
  • interimResults: true
               ↓
Candidate speaks:
  • onresult fires with event.resultIndex
  • Interim speech rendered live into the answer textarea
  • Final results appended to authoritative transcript
               ↓
Candidate pauses / continues / types:
  • Manual keystrokes immediately update base text without overwriting
               ↓
Unexpected audio silence / onend:
  • State machine detects state === LISTENING and safely restarts recognition
               ↓
[Candidate submits]:
  • Recognition cleanly stopped
  • Final transcript persisted to backend
```

---

## 12. Camera & Computer Vision Pipeline

```
Local Video Stream (640x480)
            ↓
MediaPipe FaceMesh (Runs locally via WebAssembly, maxNumFaces: 4)
            ↓
Frame Classification:
  • 0 faces: NO_FACE → Yellow banner "Face not detected"
  • 1 face: ONE_FACE → Valid outline + Telemetry active
  • 2+ faces: MULTIPLE_FACES → PROMINENT RED BOUNDING BOXES + Warning banner
            ↓
Telemetry Gating:
  • Multi-person frames and no-face frames are strictly excluded from visual metrics
  • Visual Analysis Coverage % = (Valid Frames / Total Sampled Frames) * 100
```

### What the System Measures
- **Face Framing Centering**: Percentage of valid frames candidate remained positioned in frame.
- **Blink Rate & Eye Openness**: Frequency of blinks per minute calculated from upper/lower eyelid landmark distance.
- **Visual Analysis Coverage**: Percentage of time candidate was properly framed and alone.

### What the System DOES NOT Claim to Measure
- The system **does not** claim to detect lies, deceit, psychological stress, emotional states, or candidate integrity. Signals are strictly reported as video framing stability and presentation pacing.

---

## 13. Scoring System & Longitudinal Readiness

### Calculation Formula
```
Readiness Score (with camera) =
  (0.30 * Technical) + (0.30 * Communication) + (0.20 * Delivery) + (0.20 * Resume Consistency)

Readiness Score (camera inactive) =
  (0.375 * Technical) + (0.375 * Communication) + (0.25 * Resume Consistency)
```

### Assessment Confidence
- **High**: >= 5 completed, evaluated turns.
- **Moderate**: 3–4 completed, evaluated turns.
- **Low / Insufficient Data**: < 3 completed turns (displayed as "Building Baseline" or "Not assessed").

---

## 14. Report Generation ("Your Interview Review")

The interview report functions as a structured study guide:
1. **Overall Readiness & Confidence**: Displays score (e.g., `78 / 100`) or `Not assessed` if insufficient evidence exists.
2. **Key Strengths & Growth Areas**: Highlights top performing competency and immediate growth opportunity.
3. **Per-Question Study Cards**:
   - Exact Question & Candidate's Verbatim Answer.
   - Pacing metrics (WPM, response time).
   - **What a Strong Answer Should Cover** (foundational concepts, mechanisms, trade-offs).
   - **What Was Missing** (concrete implementation gaps).
   - **How to Structure an Improved Answer** (model response).
   - **Resume Connection** (why this question matters for the candidate's portfolio).
   - Actionable "Practice This Topic" button launching targeted practice.

---

## 15. Profile & Biodata System

The profile includes:
- **Personal & Professional**: Full Name, Email, Target Role, Experience Level, Bio.
- **Education**: Degree, University, Graduation Year.
- **Technical Skills**: Programming Languages, Frameworks, Databases, Tools.
- **Developer Profiles**: LinkedIn, GitHub, LeetCode, Codeforces, HackerRank, Kaggle, Portfolio (with URL validation and `[Open ↗]` buttons).
- **Profile Completeness Score (0–100%)**: Deterministic weighting (Name 10, Role 10, Bio 10, Education 10, Skills 15, LinkedIn 10, GitHub 10, LeetCode 10, Portfolio 5, Experience 10).
- **Resume Synchronization**: Suggests details extracted from uploaded resumes with a 1-click `[Use Resume Details]` button that never silently overwrites existing fields.

---

## 16. Security & Privacy

1. **Compromised Key Mitigation**: Zero hardcoded API keys. All keys loaded via `GEMINI_API_KEY` server-side only.
2. **Zero Video Storage**: Video frames are processed in-browser via WebAssembly; no candidate video or audio is permanently stored on the server.
3. **Strict CSRF & CORS**: Authenticated cookie state changes validate Origin headers against allowed origins.
4. **Password Hashing**: Bcrypt with salted rounds.

---

## 17. Docker & Startup Instructions

### Single-Command Startup
To start the entire platform with frontend, backend, database, and healthchecks:
```bash
docker compose up --build
```

### Access URLs
- **Frontend SPA**: `http://localhost:5173`
- **Backend API**: `http://localhost:8001`
- **Interactive OpenAPI Docs**: `http://localhost:8001/docs`
- **Backend Health Check**: `http://localhost:8001/health`

### Manual Local Development
```bash
# Terminal 1: Backend
source venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2: Frontend
cd frontend
npm run dev
```

---

## 18. Testing & Verification Summary

- **Automated Backend Tests**: **196 passing tests** across 34 test suites.
- **Frontend Production Build**: Vite build succeeds in **~2.1 seconds** with zero lint or syntax errors.
- **Automated JavaScript Unit Tests**:
  - `test_speech.mjs`: 11 passing tests (state machine transitions, deduplication, auto-restart, mixed typing).
  - `test_camera.mjs`: 6 passing tests (0, 1, and 2+ person frame classification, normalized bounding boxes, coverage ratio).
  - `test_profile.mjs`: 4 passing tests (100-point completeness score, link validation).

---

## 19. Known Limitations

1. **Browser Speech API Compatibility**: Web Speech API is supported natively in Chromium-based browsers (Chrome, Edge, Brave). In unsupported browsers, the UI provides a clear notification and falls back to typed input or server-side transcription.
2. **Camera Lighting & Multi-Person Sensitivity**: MediaPipe FaceMesh depends on adequate facial illumination. If lighting is poor, frames are categorized as `NO_FACE` and excluded from scoring to protect candidate score fairness.
3. **Complex PDF Formatting**: Resumes designed with heavily nested graphical multi-column layouts may experience non-standard text flow during extraction; the system allows manual review and edits.

---

## 20. How to Explain This Project in 5 Minutes (Faculty Presentation)

### Minute 1: The Problem & The Vision
"Good morning, professors. Traditional interview preparation is broken. Static question banks like LeetCode don't prepare students for conversational communication, while generic chatbots like ChatGPT suffer from hallucinations, lack session memory, and don't challenge evasive answers. We built the **Interview Intelligence System**—an evidence-based preparation platform that conducts adaptive, resume-grounded mock interviews, tracks multi-person camera telemetry, and provides study-oriented diagnostic reviews."

### Minute 2: The Core Product Loop & Resume Grounding
"The loop begins with the student's resume. Our parser extracts verified technical skills and quantitative claims (for example, 'Reduced API latency by 40%'). Rather than accepting this claim blindly, our adaptive interview engine generates targeted probes to verify how the student measured that latency and what database indexing strategies they used."

### Minute 3: Real-Time Multimodal Interaction (Speech & Vision)
"During the live interview, the student experiences a real conversation. As they speak, our continuous speech state machine streams words live into the answer box with zero duplicate transcript errors. Concurrently, MediaPipe processes video frames locally in the browser. It enforces single-person compliance: if a second person appears, the system draws a red bounding box, alerts the candidate, and suppresses visual metrics so invalid frames never corrupt the evaluation."

### Minute 4: Honest, Evidence-Gated Evaluation
"We do not claim to detect emotions or lies. Instead, we measure observable signals like pacing (WPM) and camera alignment. If a candidate skips a question, our system does not falsely assign a zero score—it marks an evidence gap. The final report is a true study tool, showing the student what a strong answer should cover, what was missing, and providing an improved model answer with one-click access to targeted practice drills."

### Minute 5: Architectural Defensibility & Code Quality
"Architecturally, deterministic application logic is strictly separated from LLM reasoning. SQLAlchemy manages our 12 database models, FastAPI handles REST endpoints, and Docker enables one-command deployment. The platform is backed by 196 automated pytest tests and verified frontend unit tests. Everything demonstrated today is working code, running live on this machine."

---

## 21. Likely Faculty Questions & Defensible Answers

#### 1. Why use Gemini instead of an open-source local model like LLaMA?
"Gemini provides high-speed contextual reasoning and structured JSON output schema validation with minimal latency (sub-second responses), which is critical for live conversational interviews. However, our architecture cleanly decouples the LLM through a provider interface; local models like Ollama/LLaMA 3 can be swapped in without modifying business logic."

#### 2. Why FastAPI instead of Django or Flask?
"FastAPI provides asynchronous execution for high I/O concurrency, native Pydantic data validation with automatic OpenAPI schema generation, and dependency injection for clean database session management."

#### 3. Why React with Vite instead of Next.js?
"Because this is an interactive client-side application heavily reliant on local browser APIs (Web Speech API, MediaPipe WebAssembly, canvas rendering), a client-side React SPA with Vite provides fast Hot Module Replacement, zero SSR hydration overhead, and minimal bundle size."

#### 4. Why MediaPipe FaceMesh instead of OpenCV or deep learning models on the server?
"MediaPipe runs completely inside the client's browser using WebAssembly. This delivers two major advantages: first, absolute candidate privacy—zero camera frames are transmitted over the network or stored on our servers; second, zero server GPU infrastructure costs."

#### 5. Why Web Speech API?
"The Web Speech API provides zero-latency, local voice-to-text with zero transcription service fees. To handle edge cases where recognition stops, we engineered an auto-restarting state machine with transcript deduplication and fallback to typed input."

#### 6. How do you prevent Gemini from hallucinating candidate skills?
"We perform deterministic extraction of skills and technologies first using curated dictionary matching and strict section boundary parsing. Gemini is only supplied the candidate's actual extracted text as ground truth."

#### 7. How does the interview adapt dynamically?
"At each turn, `decide_next_question` checks whether the candidate diversion occurred, whether evidence was sufficient, and what weaknesses were diagnosed in prior turns. If the candidate was weak on database concurrency, the engine probes deeper into concurrency before advancing."

#### 8. How do you prevent repeating the same question across sessions?
"Our `QuestionExposure` database table logs every question presented to a user. During question selection, previously seen questions within the last 5 sessions are deprioritized."

#### 9. How is the readiness score calculated?
"Readiness is a weighted composite: 30% Technical Accuracy, 30% Communication Structure, 20% Delivery Stability, and 20% Resume Consistency. If the camera was off, the formula automatically re-normalizes without penalizing the student."

#### 10. Why isn't a skipped question scored as a zero?
"In educational assessment, absence of evidence is not proof of incompetence. Marking a skipped question as a zero score distorts longitudinal trend lines. We classify skipped turns as 'Evidence Not Obtained', excluding them from arithmetic scoring while highlighting them in the study report."

#### 11. Can your system detect candidate emotion or stress?
"No, and we explicitly do not claim to. Facial emotion recognition is scientifically unreliable and legally problematic in hiring. We measure observable physical signals: eye contact alignment, blink rate, and framing stability."

#### 12. What happens if two people appear in the camera frame?
"MediaPipe detects multiple face landmark sets (`faceCount > 1`). The system draws red bounding boxes around all detected faces, displays a warning banner, and pauses visual metric sampling so the candidate's delivery score is not corrupted."

#### 13. How is privacy preserved for resumes and biometric data?
"Biometric video streams never leave the candidate's local browser memory. Resumes are stored locally in the application database and can be purged upon request."

#### 14. What happens if the Gemini API experiences a timeout or 429 rate limit?
"Every Gemini call is wrapped in a timeout guard with deterministic fallback logic. The interview proceeds using curated question bank taxonomy and deterministic rubric scoring without freezing."

#### 15. What happens if speech recognition cuts out mid-sentence?
"Our `useSpeechRecognition` state machine detects the unexpected `onend` event while in `LISTENING` state and restarts the recognizer. Existing text is preserved, and incoming results are deduplicated via `resultIndex`."

#### 16. Where is session data stored?
"All session records, answers, and evaluations are persisted in the relational database (SQLite in development/Docker, PostgreSQL in production) via SQLAlchemy."

#### 17. Why Docker Compose for one-command startup?
"To ensure the application runs identically on any faculty or evaluation machine without requiring manual installation of Node.js, Python, or system dependencies like Poppler."

#### 18. What makes this different from prompting ChatGPT: 'Interview me for a software engineer role'?
"ChatGPT lacks persistent question exposure memory, cannot track single-person camera telemetry, does not ground questions in verified resume claims, and does not produce structured diagnostic study reports with targeted drills."

#### 19. What components of the system are deterministic vs. AI-generated?
"Session state, turn counters, question exposure history, scoring arithmetic, profile completeness, and camera geometry are 100% deterministic. LLM reasoning is used only for semantic text understanding, follow-up probe generation, and qualitative answer improvement."

#### 20. How is CSRF and cross-origin security handled?
"Our custom FastAPI middleware checks the `Origin` header on state-changing requests (POST, PUT, DELETE) when authenticated via cookies, blocking unauthorized cross-origin requests."

#### 21. How does the practice hub connect to interview performance?
"When an interview concludes, the report diagnoses the student's weakest competency (e.g., Trade-off Reasoning) and displays a 'Start Next Drill' button that launches a dedicated 5-question session in that specific category."

#### 22. How is profile completeness calculated?
"Deterministically across 10 categories totaling 100 points: Name (10), Target Role (10), Bio (10), Education (10), Skills (15), LinkedIn (10), GitHub (10), LeetCode (10), Portfolio (5), and Experience (10)."

#### 23. What database migrations tool is used?
"Alembic is configured (`alembic.ini` and `alembic/`), running alongside `init_db()` to ensure schema integrity across deployments."

#### 24. How is WPM (words per minute) calculated?
"From verbatim word count divided by response duration in minutes, with guards against zero or negative response times."

#### 25. What is the future scope of this research project?
"Integration with offline local LLMs (e.g., LLaMA 3 via Ollama) for zero-cloud air-gapped deployments, and expanding speech phoneme analysis to assist non-native English speakers with pronunciation clarity."

---

## 13. Subsystem Architecture Updates & Refinements

### 13.1 Resume Review & Confirmation Workflow
To eliminate opaque, silent resume ingestion, the resume analysis pipeline follows a strict two-stage process:
1. **Document Selection & Primary Action**:
   - The candidate selects or drags a PDF/TXT resume (`Ankit_Singh_Resume.pdf`).
   - A dedicated document summary card immediately confirms filename, size, format, and status with a prominent **Review Resume** primary CTA.
2. **Deterministic Extraction & Grounding**:
   - Text extraction (Poppler/PyPDF2), structural sanitization, entity segmentation, and skill cataloging run on the backend.
   - Grounded claims and metrics are extracted. No imaginary information is fabricated.
3. **Candidate Audit & Confirmation Screen**:
   - Candidate inspects extracted attributes: Candidate Name, Target Role, Education, Technical Skills (with add/remove chips), Extracted Projects (with Accept/Ignore toggles), and Audited Claims.
   - Every extracted attribute displays an evidence badge: `Found in resume` (or `Needs confirmation`).
   - The candidate commits the profile only upon clicking **Save Resume Analysis & Continue**, which updates stored records via `PUT /resume/{id}`.

### 13.2 Speech Recognition Pipeline & Mixed Typing Synchronization
- **Single Source of Truth**: The answer `textarea` value is authoritative. Competing state loops are eliminated.
- **Microphone Stream Isolation**: When browser-native Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`) is available, concurrent `MediaRecorder` audio locks are avoided so PulseAudio/ALSA hardware buffers are never starved.
- **Zero-Duplication Transcript Accumulation**: On each `onresult` event, the recognizer computes finalized segments and interim hypothesis across `event.results`, prepending the anchor text (`baseTextBeforeSpeechRef`).
- **Resilient Re-Instantiation**: If recognition ends unexpectedly while the candidate is still in `LISTENING` mode, a fresh `new SpeechRecognition()` instance is created to prevent Chromium `InvalidStateError` exceptions.
- **Typing + Speech Interoperability**: Manual textarea edits immediately synchronize `baseTextBeforeSpeechRef` so subsequent spoken words append seamlessly without clobbering typed text.

### 13.3 Fullscreen Interview State & Proctoring Focus Protection
- **Pre-Flight Environment Check**: Clicking "Start Interview" does NOT immediately begin asking questions. The candidate must pass the Environment Check:
  - Video Camera: `READY` / `BLOCKED`
  - Microphone: `READY` / `BLOCKED`
  - Fullscreen: `READY` / `NOT ACTIVE`
- **Enforced Fullscreen Activation**: The interview question loop begins only after `requestFullscreen()` succeeds.
- **Visibility & Focus Loss Telemetry**:
  - The system monitors `document.visibilitychange`, `fullscreenchange`, and `window.blur`.
  - If `document.hidden === true` or fullscreen is exited, an immediate blocking overlay appears:
    *"INTERVIEW PAUSED — Please return to the interview window and restore fullscreen to continue."*
  - Answer submissions and timers are halted while paused.
  - Interruption metrics (`focus_interruption_count`, `focus_loss_duration_seconds`) are recorded in session telemetry without false cheating accusations.
- **Navigation Lock & Leave Warning**:
  - While an interview is active (`sessionStorage.interviewActive === "true"`), top navigation links intercept route changes with an exit warning.
  - `beforeunload` provides native browser confirmation before accidental window closure.

### 13.4 Contextual Report Generation & Educational Study Review
- **Strictly Grounded Insights**: Reports do not rely on static predefined text. For each question and submitted answer, the evaluation engine synthesizes question-specific expectations:
  - *What a Strong Answer Should Cover*: Derived from the exact question subject and target role.
  - *What Was Missing*: Pinpoints specific gaps in the candidate's actual submission (mechanisms, metrics, trade-offs).
  - *Improved Model Answer*: Concise, high-scoring technical demonstration tailored specifically to the prompt.
- **Reliable Fallback**: The Gemini client uses an expanded timeout (12.0s) and Pydantic schema validation. If the external API times out or is unreachable, the system generates deterministic, question-grounded study points rather than generic placeholders.

---

## 14. Browser Security Constraints

A normal web browser runs inside an operating system sandbox designed to protect user agency. Consequently, **no standard web application can completely prevent**:
1. Operating system application switching (e.g., `Alt+Tab`, `Cmd+Tab`, Windows key).
2. Minimizing or closing the browser window via OS window controls.
3. Terminating the browser process via Task Manager or OS signals.
4. Opening second browser windows or monitors via OS shortcut combinations.

### The Technically Correct Implementation
Rather than claiming impossible OS-level lockdown, our application implements the strongest legitimate browser proctoring standards available:
- **Controlled Fullscreen**: Initiates via `document.documentElement.requestFullscreen()`.
- **Immediate Fullscreen Exit Detection**: Pauses the session and displays a full-window blocking overlay until fullscreen is restored.
- **Visibility Loss Detection**: Uses the Page Visibility API (`document.visibilitychange`) to detect tab switches and window blur events.
- **Accurate Telemetry Logging**: Quantifies focus interruption counts and cumulative duration in session analytics for faculty inspection.
- **Unload Warning**: Registers `beforeunload` handlers to warn users before accidental tab dismissal.
- **Session Persistence**: Authoritative turn state and telemetry are continually flushed to SQLite/PostgreSQL so active progress is never lost.

