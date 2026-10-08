# Interview Intelligence

### Evidence-based interview preparation and adaptive mock interviews

Interview Intelligence is a full-stack interview preparation platform that analyzes a candidate's resume, conducts adaptive technical interviews, evaluates answers using structured evidence, and provides targeted feedback for improvement.

It combines resume-grounded questioning, answer evaluation, speech transcription, local visual presentation analysis, interview history, and targeted practice into one unified preparation loop.

---

## Architecture

```text
                    ┌─────────────────────────┐
                    │      React + Vite       │
                    │        Frontend         │
                    └────────────┬────────────┘
                                 │ HTTPS (API Calls)
                                 ▼
                    ┌─────────────────────────┐
                    │      FastAPI Backend    │
                    │           API           │
                    └──────┬────────────┬─────┘
                           │            │
              ┌────────────┘            └────────────┐
              ▼                                      ▼
     ┌─────────────────┐                    ┌─────────────────┐
     │  PostgreSQL DB  │                    │ Object Storage  │
     │ Users/Sessions  │                    │ Resumes/Docs    │
     │ Reports/History │                    │ Local / S3 / R2 │
     └─────────────────┘                    └─────────────────┘
              │
              ├─────────────────────────────► Google Gemini AI (Server-Side Only)
              │
              └─────────────────────────────► Email Provider (SMTP / Resend / Dev)
```

---

## Features

### Resume Intelligence
- **Document Support**: Parses PDF documents and pasted text with structured validation.
- **Structure Extraction**: Automatically extracts education, career experience, and categorized skill inventories.
- **Claim & Project Identification**: Analyzes resume claims, technical depth, and flags potential buzzwords or vague ownership statements.
- **Role Fit Profiling**: Evaluates alignment against role profiles (Backend, Frontend, Full-Stack, ML, DevOps, etc.).
- **Honest Score Gating**: Prevents fabricated scoring when resume text extraction is low-confidence or truncated.

### Adaptive Interviews
- **Resume-Grounded Questioning**: Prioritizes questions matching candidate experience and claimed project architectures.
- **Dynamic Follow-Ups**: Probes weak answers with clarifying questions; challenges strong answers with deeper architectural tradeoffs.
- **Curriculum & Question Exposure**: Tracks exposure history to avoid duplicate questions and maintain variety across practice sessions.
- **Evidence-Based Completion**: Synthesizes response metrics only after questions have been answered or explicitly skipped.

### Answer Evaluation
- **Rubric Dimensions**: Assesses structure, technical depth, reasoning, behavioral clarity (STAR methodology), and resume consistency.
- **Evidence Extraction**: Identifies concrete signals from answer text rather than generic praise.
- **Human-Readable Recommendations**: Actionable coaching points and vocabulary improvements.
- **AI Response Coaching ("Fix This Answer")**: Provides a concrete rewrite demonstrating how to structure the same authentic experience using measurable results.

### Speech Transcription
- **Live Speech Input**: Captures candidate audio in real time during live mock interviews.
- **Editable Transcript**: Candidates can review and edit transcribed responses before submission.
- **Mixed Input Support**: Supports typing, dictation, or combining both seamlessly.
- **Cadence Diagnostics**: Measures approximate speech timing (Words Per Minute, filler word frequencies, pause cadence).

### Visual Presentation Analysis
- **Local Browser-Side Processing**: MediaPipe FaceMesh runs entirely within the candidate's browser.
- **Presentation Stability Indicators**: Tracks camera alignment, centering, approximate blink frequency, and head motion stability.
- **Zero Emotion Claims**: Measures physical delivery cues without claiming to recognize psychological emotions or predict hiring success.

---

## Privacy

- **Local Visual Analysis**: Camera frames are processed strictly in the candidate's local browser window using client-side JavaScript. Raw camera frames are not uploaded to or stored on backend servers.
- **Audio Processing**: Answer audio is transcribed through the configured speech service and only the resulting transcript and derived cadence metrics are saved.
- **Resume Document Privacy**: Uploaded resume contents are scoped strictly to the authenticated user account.
- **Data Portability & Right to Be Forgotten**: Users can export their complete interview records (`GET /auth/export`) or permanently delete their account and associated sessions (`DELETE /auth/account`).

---

## Tech Stack

- **Frontend**: React 18, Vite, React Router 6, Recharts, CSS
- **Backend API**: FastAPI (Python 3.11+ / 3.14), Uvicorn, SQLAlchemy 2.0, Alembic
- **Database**: SQLite (local development and tests) / PostgreSQL (production)
- **Authentication**: Argon2-cffi password hashing, cryptographically random single-use tokens, HttpOnly SameSite=Lax JWT session cookies
- **Email Infrastructure**: Multi-provider abstraction supporting Development Sandbox, standard SMTP (Mailpit, Gmail App Passwords, SendGrid), and Resend API
- **AI Integration**: Google Gemini API (`gemini-2.5-flash`), server-side only

---

## Project Structure

```text
Interview_System/
├── backend/
│   ├── config.py                 # Central configuration and environment variables
│   ├── database.py               # Database engine, connection pooling, and auto-migrations
│   ├── main.py                   # FastAPI application, CORS middleware, and health endpoints
│   ├── models/                   # SQLAlchemy relational data models
│   │   └── models.py             # User, UserProfile, Resume, Session, Answer models
│   ├── routes/                   # API endpoint routers
│   │   ├── auth.py               # Register, verify-email, forgot-password, reset-password, login
│   │   ├── resume.py             # Resume upload and analysis
│   │   ├── interview.py          # Session turn execution and answer submissions
│   │   ├── analytics.py          # Dashboard performance analytics
│   │   ├── practice.py           # Targeted drills and practice questions
│   │   └── readiness.py          # Longitudinal readiness tracking
│   ├── schemas/                  # Pydantic request and response schemas
│   │   └── schemas.py
│   ├── services/                 # Core domain logic
│   │   ├── auth_service.py       # Password validation, Argon2 hashing, token generation
│   │   ├── email_service.py      # Email provider abstraction (Development, SMTP, Resend)
│   │   ├── storage_service.py    # Document storage abstraction (Local, S3)
│   │   ├── scoring_engine.py     # Multimodal rubric evaluation
│   │   ├── question_selector.py  # Adaptive question matching
│   │   └── ...
│   └── requirements.txt          # Python dependencies
├── frontend/
│   ├── public/                   # Static assets
│   ├── src/
│   │   ├── components/           # UI components (Layout, Navbar, ProtectedRoute, Modals)
│   │   ├── context/              # React Context (AuthContext, ThemeContext, ReportContext)
│   │   ├── pages/                # Page views
│   │   │   ├── Landing.jsx
│   │   │   ├── Login.jsx         # Sign in with "Forgot password?" link
│   │   │   ├── Register.jsx      # Sign up with honest delivery verification state
│   │   │   ├── VerifyEmail.jsx   # Single-use email verification link confirmation
│   │   │   ├── ForgotPassword.jsx # Enumeration-safe reset link request
│   │   │   ├── ResetPassword.jsx # Secure password update with requirements checklist
│   │   │   ├── ResumeUpload.jsx  # Resume parsing and claim verification
│   │   │   ├── InterviewSetup.jsx# Interview configuration
│   │   │   ├── Interview.jsx     # Live mock interview environment
│   │   │   ├── Dashboard.jsx     # Readiness overview
│   │   │   ├── Report.jsx        # Detailed evaluation report
│   │   │   ├── FixAnswer.jsx     # STAR answer rewriting coach
│   │   │   ├── Practice.jsx      # Targeted practice drills
│   │   │   ├── History.jsx       # Historical interview sessions
│   │   │   ├── Progress.jsx      # Skill readiness trends
│   │   │   └── Profile.jsx       # Candidate target role profile
│   │   ├── utils/                # API helpers and life-cycle utilities
│   │   ├── App.jsx               # Application routing table
│   │   └── main.jsx              # React DOM entrypoint
│   ├── package.json
│   └── vite.config.js
├── alembic/
│   ├── versions/                 # Version-controlled schema migrations
│   └── env.py
├── alembic.ini                   # Alembic migration configuration
├── tests/                        # Automated backend test suite (215 tests)
├── .env.example                  # Environment variable reference template
├── docker-compose.yml            # Docker deployment orchestration
└── README.md
```

---

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- (Optional) Mailpit for local SMTP inspection: `mailpit`

### 1. Backend Setup
```bash
# Navigate to backend directory
cd /path/to/Interview_System

# Create and activate a virtual environment
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate

# Install backend dependencies
pip install -r backend/requirements.txt

# Copy environment template
cp .env.example .env

# Run database migrations
alembic upgrade head

# Start FastAPI development server on port 8001
uvicorn backend.main:app --reload --port 8001
```

### 2. Frontend Setup
```bash
# Open a new terminal and navigate to frontend directory
cd frontend

# Install node dependencies
npm install

# Start Vite development server (default port: 5173)
npm run dev
```

Visit `http://localhost:5173` in your browser.

---

## Environment Configuration

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Key environment variables:
| Variable | Description | Default (Local Dev) |
| :--- | :--- | :--- |
| `APP_ENV` | Application environment (`development` \| `production`) | `development` |
| `APP_BASE_URL` | Base URL of frontend application for email links | `http://localhost:5173` |
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite:///./interview.db` |
| `SECRET_KEY` | Secret key for JWT session cookies (min 32 chars) | Dev fallback in non-prod |
| `ACCESS_TOKEN_EXPIRE_MINUTES`| Session cookie lifespan in minutes | `1440` (24 hours) |
| `VERIFICATION_TOKEN_EXPIRE_MINUTES`| Verification token lifespan | `30` |
| `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES`| Password reset token lifespan | `30` |
| `EMAIL_PROVIDER` | Email provider (`development` \| `smtp` \| `resend`) | `development` |
| `EMAIL_FROM` | Sender email address for outgoing messages | `noreply@interviewintelligence.com` |
| `SMTP_HOST` | Hostname of SMTP server (if `EMAIL_PROVIDER=smtp`)| `""` |
| `SMTP_PORT` | Port of SMTP server | `587` |
| `SMTP_USERNAME` | SMTP authentication username | `""` |
| `SMTP_PASSWORD` | SMTP authentication password or App Password | `""` |
| `RESEND_API_KEY` | Resend API key (if `EMAIL_PROVIDER=resend`) | `""` |
| `GEMINI_API_KEY` | Google Gemini API key (server-side only) | `""` |
| `STORAGE_PROVIDER` | Resume storage provider (`local` \| `s3`) | `local` |
| `CORS_ORIGINS` | Comma-separated list of allowed origins | `http://localhost:5173,http://localhost:3000` |

---

## Email Setup

The application features a clean email provider abstraction. The UI never claims an email was sent unless the provider confirms successful submission.

### Option A: Local Development (`EMAIL_PROVIDER=development`)
- Safe default for testing and local development.
- Captures outgoing verification and reset emails in-memory and appends them to `backend/data/dev_emails.log`.
- No external email account or internet connection required.

### Option B: Local Mailpit (`EMAIL_PROVIDER=smtp`)
- Run [Mailpit](https://github.com/axllent/mailpit) locally (`mailpit`).
- Set in `.env`:
  ```ini
  EMAIL_PROVIDER=smtp
  SMTP_HOST=localhost
  SMTP_PORT=1025
  SMTP_USERNAME=
  SMTP_PASSWORD=
  SMTP_USE_TLS=false
  ```
- Inspect delivered emails in the Mailpit web UI at `http://localhost:8025`.

### Option C: Google Gmail SMTP (`EMAIL_PROVIDER=smtp`)
- **Important**: Never use your personal Google account password.
- Requirements:
  1. Enable 2-Factor Authentication (2FA) on your Google account.
  2. Generate a dedicated 16-character **Google App Password** (under *Security* → *2-Step Verification* → *App passwords*).
  3. Configure in `.env`:
     ```ini
     EMAIL_PROVIDER=smtp
     SMTP_HOST=smtp.gmail.com
     SMTP_PORT=587
     SMTP_USERNAME=your_address@gmail.com
     SMTP_PASSWORD=your_16_character_app_password
     SMTP_USE_TLS=true
     ```

### Option D: Production Transactional Email (`EMAIL_PROVIDER=resend` or `smtp`)
- **Resend**:
  ```ini
  EMAIL_PROVIDER=resend
  RESEND_API_KEY=re_xxxxxxxxxxxxxx
  EMAIL_FROM=onboarding@resend.dev  # or your verified custom domain
  ```
- **Transactional SMTP** (SendGrid, Postmark, Amazon SES):
  ```ini
  EMAIL_PROVIDER=smtp
  SMTP_HOST=smtp.sendgrid.net
  SMTP_PORT=587
  SMTP_USERNAME=apikey
  SMTP_PASSWORD=your_sendgrid_api_key
  SMTP_USE_TLS=true
  ```

---

## Security

- **Server-Side Password Hashing**: Passwords are saved strictly using Argon2-cffi. Plaintext passwords are never stored or logged.
- **Single-Use Cryptographic Tokens**: Both email verification and password reset utilize 32-byte cryptographically random URL-safe tokens (`secrets.token_urlsafe(32)`). Tokens are stored as SHA-256 hashes in the database with strict 30-minute expirations.
- **Account Enumeration Protection**: The `/auth/forgot-password` endpoint always returns a uniform response (*"If an account exists for this email, we'll send a password reset link."*) to prevent attackers from discovering registered accounts.
- **Session Security**: Authentication utilizes `HttpOnly`, `SameSite=Lax` cookies. In production environments (`APP_ENV=production`), `Secure=True` is enforced.
- **Credential Isolation**: The Google Gemini API key is accessed exclusively server-side in FastAPI and is never exposed in client bundles or `VITE_*` environment variables.
- **Strict Rate Limiting**: In-memory token bucket rate limiting protects registration, login, resend verification (60-second cooldown), forgot password, and reset password endpoints.

---

## Production Deployment

### Production Architecture
1. **Frontend**: Static deploy on Cloudflare Pages, Vercel, or Netlify (`npm run build` → serve `dist/`).
2. **Backend**: Containerized FastAPI service on Render, Railway, Fly.io, or AWS ECS/Cloud Run.
3. **Database**: Managed PostgreSQL instance (AWS RDS, Supabase, Neon, or Railway PostgreSQL).
4. **Storage**: Object storage bucket (AWS S3 or Cloudflare R2) or managed persistent volume.
5. **Email Provider**: Resend or transactional SMTP with custom domain DKIM/SPF records.

### Deployment Checklist
1. Provision a PostgreSQL database instance.
2. Configure object storage bucket credentials.
3. Configure transactional email credentials (e.g., Resend or SendGrid).
4. Set production environment variables:
   - `APP_ENV=production`
   - `DATABASE_URL=postgresql://user:pass@host:5432/dbname`
   - `SECRET_KEY=<generate-random-32-char-key>`
   - `FRONTEND_URL=https://yourdomain.com`
   - `APP_BASE_URL=https://yourdomain.com`
   - `CORS_ORIGINS=https://yourdomain.com`
   - `EMAIL_PROVIDER=resend` (or `smtp`)
   - `GEMINI_API_KEY=<your-api-key>`
5. Run database migrations: `alembic upgrade head`.
6. Verify service health:
   - `GET /health` → `{"status": "ok"}`
   - `GET /health/ready` → `{"status": "ready", "database": "ok", "email": {...}}`
7. Perform an end-to-end smoke test (registration, email delivery, email verification, login, forgot password, reset password, mock interview, and report generation).

---

## Testing

Run the full automated test suite:
```bash
# Run all backend unit, integration, and security tests
./venv/bin/pytest tests/

# Run specific email and password reset tests
./venv/bin/pytest tests/test_password_reset_and_email_delivery.py -v

# Verify frontend production build
cd frontend && npm run build
```

---

## Project Status

| Component | Status | Notes |
| :--- | :--- | :--- |
| **User Authentication** | Implemented | Argon2 password hashing, HttpOnly session cookies |
| **Email Verification** | Implemented | Expiring single-use tokens, honest delivery feedback, 60s resend cooldown |
| **Password Reset** | Implemented | Enumeration-protected `/forgot-password`, `/reset-password` with requirement checklist |
| **Email Provider Abstraction** | Implemented | Supports Development capture, SMTP (Mailpit/Gmail App Password), and Resend API |
| **Resume Intelligence** | Implemented | Entity parsing, claim verification, role fit matching |
| **Adaptive Mock Interview** | Implemented | Dynamic question ladder, follow-up probes, difficulty adjustments |
| **Speech Transcription** | Implemented | Real-time dictation, editable transcripts, speech cadence metrics |
| **Visual Stability Analysis**| Implemented | Local browser-side FaceMesh (centering, blink frequency, head alignment) |
| **Answer Scoring & Coaching**| Implemented | 5-dimension rubric, STAR rewriting coach |
| **Production Deployment Architecture** | Implemented | PostgreSQL support with psycopg2, Alembic migrations, readiness health checks |

---

## Realistic Roadmap

- Multi-tenant team dashboards and recruiter review portals
- Webhook events for third-party ATS integrations (Greenhouse, Lever)
- Audio transcription provider failover (local Whisper fallback alongside cloud transcription)
- Expanded technical domain tracks (Distributed Systems, Security, Data Engineering)
- Native mobile responsive layout enhancements
