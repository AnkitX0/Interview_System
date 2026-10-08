/**
 * Pure helper functions for Speech Recognition state machine,
 * transcript accumulation, error mapping, and session tracking.
 * Allows thorough, deterministic unit testing without requiring browser globals.
 */

export const SPEECH_STATES = {
  IDLE: "IDLE",
  REQUESTING_PERMISSION: "REQUESTING_PERMISSION",
  RECORDING: "RECORDING",
  STOPPING: "STOPPING",
  UPLOADING: "UPLOADING",
  TRANSCRIBING: "TRANSCRIBING",
  TRANSCRIPTION_COMPLETE: "TRANSCRIPTION_COMPLETE",
  PAUSED: "PAUSED",
  ERROR: "ERROR",
  UNSUPPORTED: "UNSUPPORTED",

  // Compatibility aliases
  CONNECTING: "RECORDING",
  LISTENING: "RECORDING",
  RECEIVING_TRANSCRIPT: "TRANSCRIBING",
};

/**
 * Validates state transitions for the complete-answer recording state machine.
 */
export function canTransition(currentState, nextState) {
  const validTransitions = {
    [SPEECH_STATES.IDLE]: [
      SPEECH_STATES.REQUESTING_PERMISSION,
      SPEECH_STATES.RECORDING,
      SPEECH_STATES.UNSUPPORTED,
      SPEECH_STATES.ERROR,
    ],
    [SPEECH_STATES.REQUESTING_PERMISSION]: [
      SPEECH_STATES.RECORDING,
      SPEECH_STATES.ERROR,
      SPEECH_STATES.IDLE,
    ],
    [SPEECH_STATES.RECORDING]: [
      SPEECH_STATES.STOPPING,
      SPEECH_STATES.PAUSED,
      SPEECH_STATES.ERROR,
      SPEECH_STATES.IDLE,
    ],
    [SPEECH_STATES.STOPPING]: [
      SPEECH_STATES.UPLOADING,
      SPEECH_STATES.TRANSCRIBING,
      SPEECH_STATES.ERROR,
      SPEECH_STATES.IDLE,
    ],
    [SPEECH_STATES.UPLOADING]: [
      SPEECH_STATES.TRANSCRIBING,
      SPEECH_STATES.TRANSCRIPTION_COMPLETE,
      SPEECH_STATES.ERROR,
      SPEECH_STATES.IDLE,
    ],
    [SPEECH_STATES.TRANSCRIBING]: [
      SPEECH_STATES.TRANSCRIPTION_COMPLETE,
      SPEECH_STATES.ERROR,
      SPEECH_STATES.IDLE,
    ],
    [SPEECH_STATES.TRANSCRIPTION_COMPLETE]: [
      SPEECH_STATES.IDLE,
      SPEECH_STATES.REQUESTING_PERMISSION,
      SPEECH_STATES.RECORDING,
    ],
    [SPEECH_STATES.PAUSED]: [
      SPEECH_STATES.RECORDING,
      SPEECH_STATES.STOPPING,
      SPEECH_STATES.IDLE,
    ],
    [SPEECH_STATES.ERROR]: [
      SPEECH_STATES.IDLE,
      SPEECH_STATES.REQUESTING_PERMISSION,
      SPEECH_STATES.RECORDING,
      SPEECH_STATES.UPLOADING,
      SPEECH_STATES.TRANSCRIBING,
    ],
    [SPEECH_STATES.UNSUPPORTED]: [],
  };

  return (validTransitions[currentState] || []).includes(nextState);
}

/**
 * Formats seconds into MM:SS display for active recording UX.
 */
export function formatRecordingTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

/**
 * Maps audio capture and transcription error codes to clear candidate notices.
 */
export function mapSpeechError(errorCode) {
  switch (errorCode) {
    case "not-allowed":
    case "service-not-allowed":
    case "PERMISSION_DENIED":
      return "Microphone permission was denied. Please allow microphone access in your browser settings.";
    case "audio-capture":
    case "AUDIO_TRACK_UNAVAILABLE":
      return "No usable microphone was detected on your system.";
    case "network":
    case "NETWORK_ERROR":
      return "Transcription service connection dropped. Your recording is preserved.";
    case "no-speech":
    case "NO_SPEECH_DETECTED":
      return "No clear speech was detected. Try speaking closer to the microphone.";
    case "EMPTY_AUDIO":
      return "Recording was too short or empty. Please speak your answer clearly.";
    case "aborted":
      return "Recording was cancelled.";
    case "unsupported":
      return "Audio recording is unavailable in this browser.";
    default:
      return `Transcription notice: ${errorCode || "unknown notice"}.`;
  }
}

/**
 * Combines previously typed text with new authoritative transcript.
 */
export function combineAnswerWithTranscript(baseText, authoritativeTranscript) {
  const base = (baseText || "").trim();
  const transcript = (authoritativeTranscript || "").trim();
  if (!base) return transcript;
  if (!transcript) return base;
  return `${base} ${transcript}`;
}

/**
 * Computes composite visible answer from base, final, and interim transcripts.
 * Kept for backwards-compatibility with live preview testing.
 */
export function buildCompositeAnswer(base, finalized, interim) {
  let out = (base || "").trim();
  const fin = (finalized || "").trim();
  const inter = (interim || "").trim();

  if (fin) {
    out = out ? `${out} ${fin}` : fin;
  }
  if (inter) {
    out = out ? `${out} ${inter}` : inter;
  }
  return out;
}

/**
 * Accumulates speech segments preventing duplicate text across repeated result events.
 */
export function processSpeechEvent(baseText, currentSessionFinal, resultList, resultIndex = 0) {
  let newlyFinalized = "";
  let currentInterim = "";

  for (let i = resultIndex; i < resultList.length; ++i) {
    const item = resultList[i];
    if (item.isFinal) {
      newlyFinalized += (item.transcript || "") + " ";
    } else {
      currentInterim += (item.transcript || "");
    }
  }

  let updatedFinal = currentSessionFinal;
  if (newlyFinalized.trim()) {
    updatedFinal = (updatedFinal + " " + newlyFinalized)
      .replace(/\s+/g, " ")
      .trim();
  }

  const combined = buildCompositeAnswer(baseText, updatedFinal, currentInterim);

  return {
    combinedText: combined,
    updatedSessionFinal: updatedFinal,
    currentInterim: currentInterim.trim(),
  };
}

/**
 * Merges manual typing into base text so subsequent speech appends seamlessly.
 */
export function mergeManualTyping(currentText, newlyTyped) {
  return (newlyTyped !== undefined ? newlyTyped : currentText).trim();
}

/**
 * Tracks speech recognizer sessions to enforce single active session constraint.
 */
export class SpeechSessionTracker {
  constructor() {
    this.activeSessionId = 0;
    this.activeInstances = 0;
  }

  createSession() {
    this.activeSessionId += 1;
    this.activeInstances = 1;
    return this.activeSessionId;
  }

  destroySession(sessionId) {
    if (sessionId === this.activeSessionId) {
      this.activeInstances = 0;
    }
  }

  hasMultipleActiveSessions() {
    return this.activeInstances > 1;
  }
}
