# Production Deployment Guide: Interview Intelligence Preparation System

This guide provides end-to-end instructions for deploying the **Interview Intelligence** system to production with:
- **Database**: [Neon PostgreSQL](https://neon.tech) (Serverless PostgreSQL)
- **Backend**: [Render](https://render.com) (FastAPI Web Service)
- **Frontend**: [Vercel](https://vercel.com) (React 19 + Vite SPA)
- **AI Engine**: Google Gemini API (`gemini-2.5-flash`)
- **Browser ML**: Client-side MediaPipe landmark detection and Web Speech API

---

## Architecture Overview

```
                      +-----------------------------+
                      |       User / Candidate      |
                      +--------------+--------------+
                                     |
               +---------------------+---------------------+
               |                                           |
               v (HTTPS)                                   v (MediaPipe / Speech)
    +----------------------+                       +----------------------+
    |    Vercel (React)    |                       |    Browser Web ML    |
    |  SPA on *.vercel.app |                       |  FaceMesh & Speech   |
    +----------+-----------+                       +----------------------+
               |
               | (CORS with credentials, SameSite=None, Secure)
               v
    +----------------------+
    |    Render (FastAPI)  | <==== GEMINI_API_KEY ====> [ Google Gemini API ]
    | *.onrender.com:PORT  |
    +----------+-----------+
               |
               | (Connection pooling: pool_pre_ping, SSL require)
               v
    +----------------------+
    |    Neon PostgreSQL   |
    | ep-*.neon.tech/neondb|
    +----------------------+
```

---

## Step 1: Set Up Neon PostgreSQL

1. **Create Account & Project**:
   - Go to [neon.tech](https://neon.tech) and sign up / log in.
   - Click **Create Project**.
   - Project Name: `interview-intelligence-db` (or your choice).
   - Region: Choose the AWS region nearest your target users (e.g., `US East (Ohio)` or `US East (N. Virginia)`).
   - Postgres version: `16` or `15`.
   - Click **Create Project**.

2. **Retrieve Connection String**:
   - On the Neon Project Dashboard, locate the **Connection Details** box.
   - Ensure the dropdown is set to **Postgres** (or **SQLAlchemy**).
   - The connection string will look like:
     ```text
     postgresql://alex:AbCdEf123456@ep-cool-fog-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
     ```
   - **Important**: If the copied URL starts with `postgres://`, the backend automatically normalizes it to `postgresql://`. Ensure `?sslmode=require` is present at the end.

3. **Run Migrations on Neon Database**:
   - On your local development workstation, run Alembic migrations against the Neon connection string to initialize all database tables:
     ```bash
     DATABASE_URL="postgresql://user:password@ep-cool-fog-123456.us-east-2.aws.neon.tech/neondb?sslmode=require" venv/bin/alembic upgrade head
     ```
   - *Alternative*: When the Render backend starts up for the first time, `backend/database.py`'s `init_db()` automatically runs `alembic upgrade head` and creates missing tables. Running it beforehand is recommended to verify connectivity.

---

## Step 2: Deploy the FastAPI Backend to Render

1. **Connect Repository on Render**:
   - Log into [render.com](https://render.com).
   - Click **New +** -> **Web Service**.
   - Select **Build and deploy from a Git repository** and connect your `Interview_System` repository.

2. **Configure Service Settings**:
   - **Name**: `interview-intelligence-backend` (creates `https://interview-intelligence-backend.onrender.com`)
   - **Region**: Same region as your Neon database (e.g., `Ohio (US East)`)
   - **Branch**: `phase-5-productization` (or `main`)
   - **Root Directory**: Leave blank (repository root)
   - **Runtime**: `Python 3`
   - **Build Command**:
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     uvicorn backend.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Plan**: `Free`

3. **Configure Health Check**:
   - Click **Advanced**.
   - Set **Health Check Path** to:
     ```text
     /health
     ```

4. **Add Backend Environment Variables**:
   Add the following variables in the **Environment** tab:

   | Variable Key | Recommended Value / Description | Required? |
   |---|---|---|
   | `ENVIRONMENT` | `production` | **Yes** |
   | `DATABASE_URL` | Your Neon connection string (`postgresql://...`) | **Yes** |
   | `SECRET_KEY` | Generate a 32+ char random string (e.g. `openssl rand -hex 32`) | **Yes** |
   | `GEMINI_API_KEY` | Your Google AI Studio API key (`AIzaSy...`) | **Yes** |
   | `GEMINI_MODEL` | `gemini-2.5-flash` | **Yes** |
   | `REQUIRE_EMAIL_VERIFICATION` | `false` (allows instant candidate demo login) | **Yes** |
   | `FRONTEND_URL` | Temporarily leave blank or set after Step 3 | **Yes** (set after Vercel URL known) |
   | `CORS_ORIGINS` | Temporarily leave blank or set after Step 3 | **Yes** (set after Vercel URL known) |
   | `AUTH_COOKIE_SAMESITE` | `none` (required for cross-domain cookies) | **Yes** |
   | `AUTH_COOKIE_SECURE` | `true` (required for cross-domain cookies) | **Yes** |

5. **Deploy**:
   - Click **Create Web Service**.
   - Monitor the deploy logs. Once build succeeds and health check passes, Render will display a green **Live** badge.
   - Note your public backend URL: `https://<YOUR-RENDER-APP>.onrender.com`.
   - Test in browser or curl:
     ```bash
     curl https://<YOUR-RENDER-APP>.onrender.com/health
     # Returns: {"status":"ok"}

     curl https://<YOUR-RENDER-APP>.onrender.com/health/ready
     # Returns: {"status":"ready","database":"ok",...}
     ```

---

## Step 3: Deploy the React/Vite Frontend to Vercel

1. **Import Project on Vercel**:
   - Log into [vercel.com](https://vercel.com).
   - Click **Add New...** -> **Project**.
   - Import your `Interview_System` repository.

2. **Configure Build & Output Settings**:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click **Edit** and choose `frontend`
   - **Build Command**: `npm run build` (default)
   - **Output Directory**: `dist` (default)
   - **Install Command**: `npm install` (default)

3. **Configure Frontend Environment Variables**:
   In the **Environment Variables** section, add:

   | Variable Key | Value | Description |
   |---|---|---|
   | `VITE_API_URL` | `https://<YOUR-RENDER-APP>.onrender.com` | Your live Render backend base URL without trailing slash |

4. **Deploy**:
   - Click **Deploy**.
   - Vercel will build the frontend assets using `frontend/vercel.json` (which provides SPA client-side route fallback to `/index.html`).
   - Once completed, Vercel provides your live domain: `https://<YOUR-APP>.vercel.app`.

---

## Step 4: Cross-Service Wiring (Final Handshake)

Because the frontend and backend are hosted on separate domains (`*.vercel.app` and `*.onrender.com`):

1. **Update Render Environment with Vercel Domain**:
   - Return to the [Render Dashboard](https://dashboard.render.com).
   - Go to your backend service -> **Environment**.
   - Set:
     ```text
     FRONTEND_URL=https://<YOUR-APP>.vercel.app
     CORS_ORIGINS=https://<YOUR-APP>.vercel.app
     ```
   - Render will automatically trigger a rolling redeploy to apply the updated CORS origins.

2. **Verify Cross-Origin Cookie Support**:
   - `AUTH_COOKIE_SAMESITE=none` and `AUTH_COOKIE_SECURE=true` ensure that Safari, Chrome, and Firefox permit the `HttpOnly` JWT cookie across the Vercel-to-Render boundary during API requests.

---

## Complete Environment Variable Reference

### Backend (Render)

| Variable | Type | Default | Description |
|---|---|---|---|
| `ENVIRONMENT` | String | `production` | Triggers production security safeguards. |
| `DATABASE_URL` | Secret | *None* | Full Neon PostgreSQL connection string. |
| `SECRET_KEY` | Secret | *None* | Cryptographic signing key for JWT tokens. |
| `GEMINI_API_KEY` | Secret | *None* | Google GenAI API key for evaluations and question generation. |
| `GEMINI_MODEL` | String | `gemini-2.5-flash` | Gemini model name for LLM queries. |
| `REQUIRE_EMAIL_VERIFICATION` | Boolean | `false` | When `false`, users can register and log in immediately without OTP/email links. |
| `FRONTEND_URL` | Public URL | *None* | Origin of the deployed Vercel frontend. |
| `CORS_ORIGINS` | CSV | *None* | Comma-separated list of allowed origins. |
| `AUTH_COOKIE_SAMESITE` | String | `none` | SameSite cookie attribute (`none` for cross-domain HTTPS). |
| `AUTH_COOKIE_SECURE` | Boolean | `true` | Secure cookie flag (required when SameSite is None). |
| `ACCESS_TOKEN_EXPIRE_MINUTES`| Integer | `1440` | JWT expiration duration in minutes (24h). |

### Frontend (Vercel)

| Variable | Type | Example | Description |
|---|---|---|---|
| `VITE_API_URL` | Public URL | `https://interview-backend.onrender.com` | Base URL of deployed backend. Never put secrets here. |

---

## Verification & Smoke Test Checklist

After deployment, perform these manual verification steps:

- [ ] **Liveness**: Open `https://<YOUR-RENDER-APP>.onrender.com/health` in a browser. It should return `{"status":"ok"}`.
- [ ] **Readiness**: Open `https://<YOUR-RENDER-APP>.onrender.com/health/ready`. It should return `{"status":"ready","database":"ok",...}`.
- [ ] **Frontend Landing Page**: Open `https://<YOUR-APP>.vercel.app`. Verify that the page loads with rich styles, typography, and functional navigation buttons.
- [ ] **User Registration**: Click **Create Account** / Sign Up. Register a new user with `@gmail.com` address. Verify that registration succeeds and immediately transitions to the dashboard without blocking on email delivery.
- [ ] **User Login & Logout**: Click **Log Out**, then navigate to `/login`. Sign in with the registered credentials. Verify that the session is restored.
- [ ] **Incorrect Credentials**: Attempt to sign in with an incorrect password. Verify that a professional error message ("Invalid email or password") is displayed without leaking database details.
- [ ] **Direct URL Refresh**: Navigate to `/dashboard` or `/setup` and refresh the browser. Verify that `vercel.json` SPA routing prevents 404 errors.
- [ ] **Resume Parsing**: Upload a sample PDF or DOCX resume. Verify that text extraction, claim detection, and role fit scores compute successfully.
- [ ] **Camera & Mic**: Enter an interview session. Verify that MediaPipe loads landmarks locally and microphone capture functions with graceful permission handling.
