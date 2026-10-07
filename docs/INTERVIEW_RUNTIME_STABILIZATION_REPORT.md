# Interview Runtime & Presentation Intelligence Report

## 1. Report Crash Investigation & Root Cause
- **Primary Root Cause**: In `frontend/src/pages/Report.jsx`, line 331 attempted to call `w.weakness_type.replace(/_/g, " ")` on items in `report.session_weaknesses`. The backend weakness diagnosis engine returns weakness objects with `"id": "tech_shallow_depth"` rather than `"weakness_type"`. Calling `.replace()` on `undefined` threw an uncaught JavaScript `TypeError`, crashing the React component tree and rendering a completely blank white page.
- **Query Parameter Resolution**: `Report.jsx` now safely resolves `targetSessionId` from `queryParams.get("sessionId") || location.state?.sessionId || currentSessionId || sessionStorage.getItem("currentSessionId")`.
- **Auth & Session Persistence**: `backend/config.py` was updated to use a persistent development secret key (`SECRET_KEY`) when no environment key is provided, preventing random token invalidation across dev server reloads.
- **Normalization Safeguard**: Implemented `normalizeReport(raw)` helper inside `Report.jsx` to guarantee fallback defaults for `subscores`, `session_weaknesses`, `timeline`, `next_practice`, `claim_consistency`, and `behavioral_metrics`.

## 2. Report API Contract
- **Endpoints**: `GET /report/{session_id}` and `GET /report/latest`.
- **Status Codes**: 
  - `200 OK`: Valid session owned by authenticated user.
  - `401 Unauthorized`: Missing or invalid session cookie.
  - `404 Not Found`: Session ID does not exist for the user.
- **Verified Response Schema**:
```json
{
  "session_id": 9,
  "mode": "technical",
  "difficulty": "medium",
  "target_role": "Software Engineer",
  "readiness_score": 25.6,
  "status_label": "Requires Targeted Practice",
  "delivery_measured": false,
  "weights_used": {
    "communication": 0.375,
    "technical": 0.375,
    "delivery": 0.0,
    "resume_consistency": 0.25
  },
  "subscores": {
    "communication": 20.0,
    "technical": 15.0,
    "delivery": null,
    "resume_consistency": 50.0
  },
  "insights": {
    "strongest_category": "Resume Consistency",
    "weakest_category": "Technical",
    "top_improvements": [
      "Strongest area is Resume Consistency with an average score of 50.0%.",
      "Primary growth opportunity lies in Technical (currently at 15.0%)."
    ]
  },
  "session_weaknesses": [
    {
      "id": "tech_shallow_depth",
      "dimension": "technical",
      "symptom": "5 answers scored below 60 in technical depth.",
      "explanation": "Technical depth dropped because answers lacked specific trade-offs or concrete metrics."
    }
  ],
  "timeline": [],
  "claim_consistency": [],
  "next_practice": []
}
```

## 3. Report Rendering & View States
- **Loading State**: Displays skeleton loaders for score, insights, and charts.
- **Success State**: Renders score hero banner (26/100), subscore bar chart, key observations, STAR strengths, weakness diagnosis, and recommended practice drill button.
- **Unauthorized State**: Renders "Your session has expired. Please log in again to view your report." with direct login action.
- **Not Found / Server Error State**: Renders explicit error banner with "Back to Dashboard", "View History", and "Start New Interview" buttons. Never renders a blank screen.

## 4. Camera & Video Preview Lifecycle
- **Fixed Preview Binding**: `<video ref={videoRef}>` is now permanently mounted in the DOM (`display: isCameraOn ? 'block' : 'none'`). Previously, conditionally unmounting `<video>` caused `srcObject = stream` to execute against `null`, resulting in a black preview rectangle.
- **Dimension Verification**: Camera state transitions to `isCameraOn = true` only after `video.videoWidth > 0` and `video.videoHeight > 0` are verified.
- **Status Badges**:
  - `Camera on` (Green indicator) — Active stream rendering frames.
  - `Camera initializing...` (Amber indicator) — Stream connecting.
  - `Camera unavailable / Camera off` (Gray indicator) — Camera denied or privacy mode.
  - Removed misleading "Framing active" label when video stream was unrendered.

## 5. Presentation Signals & Visual Delivery Analysis
- **Observable Metrics Tracked**:
  - **Camera Alignment / Centering Proxy**: Ratio of frames where face nose position remains within central 30% bounding corridor.
  - **Blink Frequency**: Measured blinks per minute using eye aspect ratio landmark distance.
  - **Pause Cadence**: Average pause duration (seconds) and pause frequency across turns.
- **Diagnostic Disclaimer**: Physical signals are framed explicitly as presentation delivery and pacing indicators. The system does NOT claim to detect internal emotional states, truthfulness, or psychological confidence.

## 6. Live Speech & Transcription Engine
- **Web Speech API**: Continuous recognition (`en-US`) with interim transcript feedback.
- **Text Fallback**: Seamless fallback to typed answers when microphone permissions are denied or unsupported.
- **Answer Metrics Persisted**: Spoken duration, word count, WPM, filler word count ("um", "uh", "like"), and pause intervals.

## 7. Adaptive Question Pipeline
- **Bounded Context**: Question Decision Service passes target role, difficulty, resume summary, current turn, previous question, previous answer, and rubric evaluation.
- **Question Continuity**: Selects contextual follow-ups probing technical specifics and trade-offs.
- **Backend Isolation**: Gemini LLM API calls executed strictly server-side. Secure fallback to rule-based question engine if LLM service is unreachable.

## 8. Presentation Performance & Progress Comparison
- **Score Re-normalization**: When camera is off, readiness score re-normalizes dynamically across Communication (37.5%), Technical (37.5%), and Resume Consistency (25.0%).
- **Targeted Practice Recommendation**: Direct one-click drill launch for identified weakest category (e.g. `TECHNICAL_DEPTH`).

## 9. Privacy & Data Integrity
- **Processing Scope**: Local browser processing for face landmarks; server-side text evaluation for scoring rubrics.
- **No Video Storage**: Raw video frames are processed transiently in browser memory and never uploaded to backend storage.

## 10. Automated & Real Browser Verification

| Test Suite / Target | Method | Status | Result |
| :--- | :--- | :--- | :--- |
| Pytest Test Suite | `./venv/bin/pytest` | PASS | 166 passed (0 failures) |
| Frontend Build | `npm --prefix frontend run build` | PASS | Built in 2.10s (0 errors) |
| Real Browser Report Verification | Google Chrome (Playwright) | PASS | `/report?sessionId=9` rendered, score 26/100 visible, all tabs interactive |
| Session Finalization & Report API | `GET /report/9` | PASS | HTTP 200 OK |
| Camera Stream Mounting | Video Ref State | PASS | Real mirrored stream rendered with active dimensions |
| Speech Recognition Fallback | Web Speech API | PASS | Switches to text mode gracefully on mic block |

## 11. Remaining Issues
- **None**: Report rendering crash resolved, camera preview stream fixed, API contracts aligned, and full test suite passing.
