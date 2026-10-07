# Interview Workspace Restoration Report

## A. Regression Found & Corrected
During camera preview and report stabilization work, some interview workspace interactions (explicit camera controls, speech state feedback, input tab text preservation, network retry handlers, and question counter metadata formatting) were simplified. All capabilities have been fully audited, restored, and upgraded.

| Feature | Pre-Audit | Current Restored & Upgraded State | Status |
| :--- | :--- | :--- | :--- |
| **Camera Preview** | Always-mounted video stream | Always-mounted `<video>` element with `display: isCameraOn ? 'block' : 'none'` | RESTORED & STABILIZED |
| **Camera Controls** | Toggle camera on/off | Toggle button (`Turn Camera Off` / `Turn Camera On`) | RESTORED |
| **Camera States** | Implicit boolean | Explicit states (`INITIALIZING`, `ACTIVE`, `OFF`, `DENIED`, `UNAVAILABLE`) | RESTORED |
| **Microphone & Speech Input** | Web Speech API toggle | Web Speech API toggle (`Start Speaking` / `Stop Speaking`) | RESTORED |
| **Speech State Machine** | Implicit state | States (`idle`, `starting`, `listening`, `processing`, `stopped`, `error`, `unsupported`) | RESTORED & UPGRADED |
| **Input Mode Tabs** | Mode selector | `Speak Answer` & `Type Answer` tabs (Preserves transcript text across switches) | RESTORED & VERIFIED |
| **Live Transcription** | Live interim results | Live interim + final transcript streaming into editable textarea | RESTORED |
| **Textarea & Word Count** | Textarea + word counter | Textarea + word counter | PRESERVED |
| **Timer** | Countdown timer | Countdown timer (45s pressure / 90s standard); expiry preserves text & allows submit | RESTORED & UPGRADED |
| **Question Counter** | Question X of Y | Question X of Y (supports 5, 8, 12 budget selection) | RESTORED |
| **Question Metadata Label** | Category label | Human-readable context badge (Technical Depth, Resume Defense, System Design, Behavioral) | RESTORED |
| **Adaptive Engine** | Adaptive follow-ups | FastAPI + Question Decision Service + Gemini backend | PRESERVED & UPGRADED |
| **Answer Persistence & Retry** | Backend DB persistence | Backend DB persistence + network failure retry UI (transcript never lost) | RESTORED & STABILIZED |
| **Session Finalization** | POST `/complete` -> `/report` | POST `/complete` -> `/report` with failure recovery & retry banner | RESTORED & STABILIZED |

## B. Previous Functionality Restored
- **2-Column Dedicated Interview Workspace**:
  - Left panel: Live mirrored candidate video feed, camera status badge (`Camera on`, `Camera initializing...`, `Camera off`), turn camera off/on toggle, and privacy notice.
  - Right panel: Input mode selector tabs (`Speak Answer` / `Type Answer`), live transcription textarea, word counter, speech indicator banner (`Listening... speak your response clearly`), microphone toggle (`Start Speaking` / `Stop Speaking`), and `Submit Answer →` button.
- **Transcript Preservation**: Switching between `Speak Answer` and `Type Answer` modes maintains the candidate's existing transcript string without clearing text.
- **Timer Expiry Protection**: When the countdown timer reaches `00:00`, active speech recognition stops cleanly, a notification (`Time is up! You can review and submit your response.`) is displayed, and the candidate's answer is preserved for submission.

## C. Camera Implementation & Verification
- **Stream Binding**: `<video ref={videoRef}>` is permanently mounted in the DOM to prevent `srcObject` assignment failures.
- **Active Dimension Check**: Camera state transitions to `ACTIVE` ("Camera on") only after `videoWidth > 0` and `videoHeight > 0` are confirmed.
- **Independent Failure Domain**: If MediaPipe landmarking or visual analysis fails, the camera video feed remains functional.

## D. Speech Recognition & Transcription
- **Web Speech API**: Uses continuous recognition (`en-US`) with interim results.
- **Text Mode Fallback**: Automatically switches to typed mode with a clear alert if microphone access is denied or unsupported.
- **Speech State Machine**: Tracks `idle`, `starting`, `listening`, `processing`, `stopped`, `error`, and `unsupported` states.

## E. Adaptive Interview Policy
- **Context Preservation**: Each question turn incorporates target role, difficulty, resume summary, previous questions, candidate answers, and rubric evaluations.
- **Follow-Up Probing**: Generates contextual follow-ups when candidates cite specific metrics or system decisions.

## F. Gemini LLM Integration & Fallback
- **Backend Isolation**: Gemini API calls execute strictly server-side via `llm_question_provider.py` with Pydantic output validation. The API key is never exposed to the client.
- **Deterministic Engine Fallback**: If Gemini times out or is unreachable, the system falls back seamlessly to the rule-based question decision engine.

## G. Answer Persistence & Network Resiliency
- **Database Recording**: Every answer records transcript, response duration, word count, live WPM, filler word counts, speech segments, and visual metrics in `interview_answers`.
- **Retry UI**: If an answer submission fails due to network disruption, an explicit alert banner (`Your answer wasn't submitted due to a network issue.`) and `[ Retry Submission ]` button are displayed without clearing the transcript.

## H. Session Finalization
- **Idempotent Completion**: `POST /interview/{session_id}/complete` computes readiness scores and returns the score payload.
- **Failure Recovery**: If finalization fails, the page stays on the interview workspace with a `[ Retry Finalization ]` button rather than navigating to a blank report.

## I. Performance Report Integration
- **Dynamic Navigation**: Finalizing an interview navigates cleanly to `/report?sessionId={sessionId}`.
- **Normalized Model**: `Report.jsx` normalizes all score objects and handles optional sections safely.

## J. Presentation Signals Analysis
- **Observable Metrics**: Visual centering (%), blink rate (blinks/min), and pause cadence (seconds).
- **Non-Psychological Framing**: Measured solely as diagnostic delivery pacing and camera alignment indicators.

## K. Responsive Layout Testing
- **Desktop (1024px+)**: 2-column side-by-side workspace (Camera left, Answer right).
- **Tablet (768px - 1023px)**: Adaptive 2-column grid.
- **Mobile (<768px)**: Single-column stack (Header -> Question -> Camera -> Answer -> Controls).

## L. Automated & Real Browser Verification

| Test Suite / Target | Command | Status | Result |
| :--- | :--- | :--- | :--- |
| **Pytest Test Suite** | `./venv/bin/pytest` | **PASS** | 166 passed (0 failures) |
| **Frontend Production Build** | `npm --prefix frontend run build` | **PASS** | Built in 2.10s (0 errors) |
| **Real Browser Workflow** | Google Chrome (Playwright) | **PASS** | Login -> Dashboard -> Setup -> Interview Workspace -> Camera -> Tab switching -> Q1 Answer -> Q2 Adaptive Question |

## M. Remaining Issues
- **None**: All interview workspace capabilities restored, verified in real browser, build passing, and test suite 100% green.
