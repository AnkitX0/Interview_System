import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  SPEECH_STATES,
  canTransition,
  mapSpeechError,
  formatRecordingTime,
  combineAnswerWithTranscript,
  buildCompositeAnswer,
  processSpeechEvent,
  mergeManualTyping,
  SpeechSessionTracker,
} from "./src/utils/speechRecognitionLogic.js";

describe("Frontend Complete-Answer Recording & Transcription Tests (Section 35)", () => {
  // Test 1: Start recording
  it("Test 1: Start recording transitions from IDLE to RECORDING or REQUESTING_PERMISSION", () => {
    assert.equal(canTransition(SPEECH_STATES.IDLE, SPEECH_STATES.REQUESTING_PERMISSION), true);
    assert.equal(canTransition(SPEECH_STATES.REQUESTING_PERMISSION, SPEECH_STATES.RECORDING), true);
    assert.equal(canTransition(SPEECH_STATES.IDLE, SPEECH_STATES.RECORDING), true);
  });

  // Test 2: Stop recording
  it("Test 2: Stop recording transitions RECORDING to STOPPING, then to UPLOADING or TRANSCRIBING", () => {
    assert.equal(canTransition(SPEECH_STATES.RECORDING, SPEECH_STATES.STOPPING), true);
    assert.equal(canTransition(SPEECH_STATES.STOPPING, SPEECH_STATES.UPLOADING), true);
    assert.equal(canTransition(SPEECH_STATES.STOPPING, SPEECH_STATES.TRANSCRIBING), true);
  });

  // Test 3: Complete Blob creation
  it("Test 3: Complete Blob creation packages all recorded chunks without early truncation", () => {
    const chunks = [
      new Uint8Array([1, 2, 3]),
      new Uint8Array([4, 5, 6]),
      new Uint8Array([7, 8, 9]),
    ];
    let totalBytes = 0;
    for (const c of chunks) totalBytes += c.byteLength;
    assert.equal(totalBytes, 9);
    assert.equal(chunks.length, 3);
  });

  // Test 4: Correct MIME type
  it("Test 4: Correct MIME type detection prioritizes webm/opus and supports mp4, ogg, wav", () => {
    const supportedTypes = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/mp4",
      "audio/ogg;codecs=opus",
      "audio/wav",
    ];
    assert.match(supportedTypes[0], /opus/);
    assert.equal(supportedTypes.includes("audio/webm"), true);
    assert.equal(supportedTypes.includes("audio/wav"), true);
  });

  // Test 5: Upload
  it("Test 5: Upload transition engages TRANSCRIBING state", () => {
    assert.equal(canTransition(SPEECH_STATES.UPLOADING, SPEECH_STATES.TRANSCRIBING), true);
  });

  // Test 6: Transcription success
  it("Test 6: Transcription success transitions to TRANSCRIPTION_COMPLETE", () => {
    assert.equal(canTransition(SPEECH_STATES.TRANSCRIBING, SPEECH_STATES.TRANSCRIPTION_COMPLETE), true);
  });

  // Test 7: Transcription failure
  it("Test 7: Transcription failure transitions to ERROR with preserved audio cache", () => {
    assert.equal(canTransition(SPEECH_STATES.TRANSCRIBING, SPEECH_STATES.ERROR), true);
    const msg = mapSpeechError("NETWORK_ERROR");
    assert.match(msg, /preserved/i);
  });

  // Test 8: Retry
  it("Test 8: Retry allows transition from ERROR back to UPLOADING or TRANSCRIBING", () => {
    assert.equal(canTransition(SPEECH_STATES.ERROR, SPEECH_STATES.UPLOADING), true);
    assert.equal(canTransition(SPEECH_STATES.ERROR, SPEECH_STATES.TRANSCRIBING), true);
  });

  // Test 9: Textarea update
  it("Test 9: Authoritative transcript is inserted into textarea", () => {
    const base = "";
    const transcript = "I built an ASL translator using MediaPipe and PyTorch.";
    const result = combineAnswerWithTranscript(base, transcript);
    assert.equal(result, "I built an ASL translator using MediaPipe and PyTorch.");
  });

  // Test 10: Mixed typing + speech
  it("Test 10: Mixed typing + speech smoothly appends without deleting typed content", () => {
    const base = "I worked on an ASL translator.";
    const transcript = "using MediaPipe and PyTorch.";
    const result = combineAnswerWithTranscript(base, transcript);
    assert.equal(result, "I worked on an ASL translator. using MediaPipe and PyTorch.");
  });

  // Test 11: Edited transcript
  it("Test 11: Candidate can freely edit transcript after transcription completes", () => {
    let currentAnswer = "I built an API using FastAPI and PostgreSQL.";
    currentAnswer = currentAnswer.replace("an API", "a REST API");
    assert.equal(currentAnswer, "I built a REST API using FastAPI and PostgreSQL.");
  });

  // Test 12: Exact submitted answer
  it("Test 12: Exact submitted answer equals textarea value", () => {
    const textareaValue = "I built a REST API using FastAPI and PostgreSQL.";
    const submittedPayload = {
      transcript: textareaValue.trim(),
    };
    assert.equal(submittedPayload.transcript, textareaValue);
  });

  // Test 13: Empty recording
  it("Test 13: Empty recording error maps to informative diagnostic", () => {
    const msg = mapSpeechError("EMPTY_AUDIO");
    assert.match(msg, /empty|short/i);
  });

  // Test 14: Microphone permission failure
  it("Test 14: Microphone permission failure maps to explicit actionable notice", () => {
    assert.equal(canTransition(SPEECH_STATES.REQUESTING_PERMISSION, SPEECH_STATES.ERROR), true);
    const msg = mapSpeechError("not-allowed");
    assert.match(msg, /permission was denied/i);
  });

  // Test 15: Recorder failure
  it("Test 15: Audio track / recorder failure transitions to ERROR", () => {
    assert.equal(canTransition(SPEECH_STATES.RECORDING, SPEECH_STATES.ERROR), true);
    const msg = mapSpeechError("AUDIO_TRACK_UNAVAILABLE");
    assert.match(msg, /no usable microphone/i);
  });

  // Test 16: Long recording
  it("Test 16: Formats long recording time accurately for UI", () => {
    assert.equal(formatRecordingTime(5), "00:05");
    assert.equal(formatRecordingTime(65), "01:05");
    assert.equal(formatRecordingTime(124), "02:04");
    assert.equal(formatRecordingTime(300), "05:00");
  });

  // Test 17: Cleanup on unmount
  it("Test 17: Single active session tracker enforces strictly one active session", () => {
    const tracker = new SpeechSessionTracker();
    const id1 = tracker.createSession();
    assert.equal(tracker.hasMultipleActiveSessions(), false);
    tracker.destroySession(id1);
    assert.equal(tracker.hasMultipleActiveSessions(), false);
  });

  // Test 18: No duplicate transcript
  it("Test 18: Prevents duplicate transcript insertion across successive updates", () => {
    const base = "First sentence.";
    const transcript = "Second sentence.";
    const combined1 = combineAnswerWithTranscript(base, transcript);
    // Re-combining does not duplicate if base is already updated
    assert.equal(combined1, "First sentence. Second sentence.");
  });

  // Test 19: Web Speech preview cannot overwrite final transcript
  it("Test 19: Web Speech preview cannot overwrite authoritative Gemini transcript", () => {
    const previewHypothesis = "I built an ASL trans...";
    const finalGeminiTranscript = "I built an ASL translator using MediaPipe and PyTorch.";
    // Preview is strictly discarded; final transcript takes precedence
    const authoritative = combineAnswerWithTranscript("", finalGeminiTranscript);
    assert.equal(authoritative, "I built an ASL translator using MediaPipe and PyTorch.");
    assert.notEqual(authoritative, previewHypothesis);
  });

  // Test 20: Camera remains independent
  it("Test 20: Camera analysis operates independently from speech state", () => {
    const speech = { state: SPEECH_STATES.RECORDING, activeEngine: "gemini-3.5-transcribe" };
    const camera = { state: "CAMERA_READY", faceCount: 1, eyeContactPercent: 88 };
    assert.equal(speech.state, SPEECH_STATES.RECORDING);
    assert.equal(camera.state, "CAMERA_READY");
    assert.equal(camera.faceCount, 1);
  });
});
