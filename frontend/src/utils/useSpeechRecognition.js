/**
 * frontend/src/utils/useSpeechRecognition.js
 *
 * Production Audio Transcription Hook — Complete-Answer Recording Pipeline.
 *
 * Architecture (Section 2, 4, 12, 15, 16):
 * 1. User clicks "Speak Answer" -> getUserMedia audio track verified.
 * 2. MediaRecorder records continuously into memory with supported browser MIME.
 * 3. Web Audio API AnalyserNode monitors RMS volume level strictly for diagnostics.
 * 4. User clicks "Stop Speaking" -> recorder stops -> full audio Blob assembled.
 * 5. Full recording POSTed to /interview/transcribe (Gemini 3.5 Transcribe).
 * 6. Authoritative verbatim transcript inserted into answer textarea.
 * 7. Candidate can freely edit the transcript before submitting.
 * 8. Web Speech API (if present) is used strictly as an optional non-authoritative live preview
 *    and NEVER overwrites the authoritative complete-answer transcript.
 * 9. Audio Blob kept in memory on failure for instant retry without repeating speech.
 */

import { useState, useRef, useEffect, useCallback } from "react";
import { apiFetch } from "./api";
import {
  SPEECH_STATES,
  mapSpeechError,
  combineAnswerWithTranscript,
  formatRecordingTime,
} from "./speechRecognitionLogic";

export { SPEECH_STATES };

function getSupportedAudioMime() {
  const mimeCandidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/mp4",
    "audio/ogg;codecs=opus",
    "audio/ogg",
    "audio/wav",
  ];
  if (typeof window !== "undefined" && window.MediaRecorder && typeof MediaRecorder.isTypeSupported === "function") {
    for (const mime of mimeCandidates) {
      if (MediaRecorder.isTypeSupported(mime)) {
        return mime;
      }
    }
  }
  return "audio/webm";
}

export function useSpeechRecognition({
  answer = "",
  setAnswer = () => {},
  textOnly = false,
  sessionId = null,
  vocabulary = [],
  language = "en-IN",
  onNotice = () => {},
}) {
  const [speechState, setSpeechState] = useState(SPEECH_STATES.IDLE);
  const [speechNotice, setSpeechNotice] = useState("");
  const [speechSupported, setSpeechSupported] = useState(true);
  const [audioLevel, setAudioLevel] = useState(0.0);
  const [activeEngine, setActiveEngine] = useState("none");
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [livePreviewText, setLivePreviewText] = useState("");

  const [debugInfo, setDebugInfo] = useState({
    micStatus: "IDLE",
    audioLevel: 0.0,
    engine: "none",
    connection: "DISCONNECTED",
    lastTranscriptEvent: null,
    lastTranscriptText: "",
    error: null,
    recordingDuration: 0,
    mimeType: "none",
    blobSize: 0,
  });

  // State & Ref Anchors
  const baseTextRef = useRef(answer);
  const latestAnswerRef = useRef(answer);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const actualMimeTypeRef = useRef("audio/webm");
  const lastRecordedBlobRef = useRef(null);
  const recordingTimerRef = useRef(null);

  const microphoneStreamRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const audioLevelIntervalRef = useRef(null);

  // Optional non-authoritative preview recognizer
  const webSpeechPreviewRef = useRef(null);

  const isExplicitlyStoppedRef = useRef(false);
  const isUploadingRef = useRef(false);
  const speechSessionIdRef = useRef(0);

  // Synchronize latestAnswerRef with answer prop
  useEffect(() => {
    latestAnswerRef.current = answer;
  }, [answer]);

  const updateNotice = useCallback(
    (msg) => {
      setSpeechNotice(msg);
      onNotice(msg);
    },
    [onNotice]
  );

  // Check hardware/browser capability on mount
  useEffect(() => {
    if (textOnly) {
      setSpeechSupported(false);
      setSpeechState(SPEECH_STATES.UNSUPPORTED);
      return;
    }
    const hasMediaDevices = Boolean(
      typeof navigator !== "undefined" &&
      navigator.mediaDevices &&
      navigator.mediaDevices.getUserMedia
    );
    const hasMediaRecorder = Boolean(typeof window !== "undefined" && window.MediaRecorder);
    if (!hasMediaDevices || !hasMediaRecorder) {
      setSpeechSupported(false);
      setSpeechState(SPEECH_STATES.UNSUPPORTED);
      updateNotice("Audio recording is not supported in this browser. Please type your answer.");
    } else {
      setSpeechSupported(true);
    }
  }, [textOnly, updateNotice]);

  // Web Audio RMS volume level monitoring
  const stopAudioLevelMonitoring = useCallback(() => {
    if (audioLevelIntervalRef.current) {
      clearInterval(audioLevelIntervalRef.current);
      audioLevelIntervalRef.current = null;
    }
    if (audioContextRef.current) {
      try {
        if (audioContextRef.current.state !== "closed") {
          audioContextRef.current.close();
        }
      } catch {}
      audioContextRef.current = null;
    }
    analyserRef.current = null;
    setAudioLevel(0.0);
  }, []);

  const startAudioLevelMonitoring = useCallback((stream) => {
    stopAudioLevelMonitoring();
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      audioContextRef.current = ctx;

      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.5;
      source.connect(analyser);
      analyserRef.current = analyser;

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      audioLevelIntervalRef.current = setInterval(() => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        const avg = sum / dataArray.length;
        const normalized = Math.min(1.0, Math.round((avg / 128) * 100) / 100);
        setAudioLevel(normalized);

        setDebugInfo((prev) => ({
          ...prev,
          audioLevel: normalized,
        }));
      }, 120);
    } catch (e) {
      console.warn("[SPEECH] Web Audio monitoring notice:", e);
    }
  }, [stopAudioLevelMonitoring]);

  // Release microphone hardware
  const releaseMicrophone = useCallback(() => {
    stopAudioLevelMonitoring();
    if (microphoneStreamRef.current) {
      microphoneStreamRef.current.getTracks().forEach((track) => {
        try {
          track.stop();
        } catch {}
      });
      microphoneStreamRef.current = null;
    }
  }, [stopAudioLevelMonitoring]);

  // Upload complete recorded Blob to /interview/transcribe
  const uploadAndTranscribe = useCallback(
    async (audioBlob) => {
      if (!audioBlob || audioBlob.size < 200 || isUploadingRef.current) return;
      isUploadingRef.current = true;
      setSpeechState(SPEECH_STATES.TRANSCRIBING);
      updateNotice("Transcribing your answer with Gemini 3.5...");

      try {
        const formData = new FormData();
        const extension = audioBlob.type.includes("mp4")
          ? "mp4"
          : audioBlob.type.includes("ogg")
          ? "ogg"
          : audioBlob.type.includes("wav")
          ? "wav"
          : "webm";

        formData.append("audio", audioBlob, `complete_answer.${extension}`);
        if (sessionId) formData.append("session_id", String(sessionId));
        formData.append("language", language || "en-IN");
        formData.append("mode", "verbatim");
        if (vocabulary && vocabulary.length > 0) {
          formData.append("vocabulary", vocabulary.join(","));
        }

        const res = await apiFetch("/interview/transcribe", {
          method: "POST",
          body: formData,
        });

        if (res.ok) {
          const data = await res.json();
          const transcript = (data.transcript || "").trim();

          if (transcript) {
            const combined = combineAnswerWithTranscript(baseTextRef.current, transcript);
            setAnswer(combined);
            latestAnswerRef.current = combined;
            baseTextRef.current = combined;

            setActiveEngine(data.engine || "gemini-3.5-transcribe");
            setSpeechState(SPEECH_STATES.TRANSCRIPTION_COMPLETE);
            updateNotice("Transcript ready.");
            setLivePreviewText("");

            setDebugInfo((prev) => ({
              ...prev,
              engine: data.engine || "gemini-3.5-transcribe",
              lastTranscriptEvent: new Date().toLocaleTimeString(),
              lastTranscriptText: combined,
              recordingDuration: data.duration_seconds || 0,
            }));
          } else {
            setSpeechState(SPEECH_STATES.ERROR);
            updateNotice("No speech was detected in your recording. You can retry or type your answer.");
          }
        } else {
          const errData = await res.json().catch(() => ({}));
          const errMsg = errData?.detail || errData?.error?.message || "Transcription failed.";
          setSpeechState(SPEECH_STATES.ERROR);
          updateNotice(`Transcription failed: ${errMsg}. Your recording was preserved.`);
        }
      } catch (err) {
        console.warn("[SPEECH] Upload transcription error:", err);
        setSpeechState(SPEECH_STATES.ERROR);
        updateNotice("Transcription failed due to network glitch. Your recording was preserved.");
      } finally {
        isUploadingRef.current = false;
        releaseMicrophone();
      }
    },
    [language, releaseMicrophone, sessionId, setAnswer, updateNotice, vocabulary]
  );

  // Retry transcription using cached audio Blob
  const retryTranscription = useCallback(async () => {
    if (lastRecordedBlobRef.current) {
      await uploadAndTranscribe(lastRecordedBlobRef.current);
    } else {
      updateNotice("No cached audio available to retry. Please record your answer again.");
    }
  }, [uploadAndTranscribe, updateNotice]);

  // Start Speaking / Recording Complete Answer
  const startListening = useCallback(async () => {
    if (textOnly) {
      updateNotice("Voice input is not supported in text-only mode.");
      return;
    }

    speechSessionIdRef.current += 1;
    isExplicitlyStoppedRef.current = false;
    audioChunksRef.current = [];
    setLivePreviewText("");
    setElapsedSeconds(0);

    // Anchor baseTextRef to whatever is currently in the textarea
    baseTextRef.current = (latestAnswerRef.current || "").trim();

    setSpeechState(SPEECH_STATES.REQUESTING_PERMISSION);
    updateNotice("Requesting microphone permission...");
    setDebugInfo((prev) => ({
      ...prev,
      micStatus: "REQUESTING_PERMISSION",
      error: null,
      blobSize: 0,
    }));

    let stream = null;
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("getUserMedia not supported");
      }

      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      const audioTracks = stream.getAudioTracks();
      if (!audioTracks || audioTracks.length === 0 || audioTracks[0].readyState !== "live") {
        throw new Error("AUDIO_TRACK_UNAVAILABLE");
      }

      microphoneStreamRef.current = stream;
      startAudioLevelMonitoring(stream);
    } catch (permErr) {
      console.warn("[SPEECH] Microphone permission error:", permErr);
      setSpeechState(SPEECH_STATES.ERROR);
      setDebugInfo((prev) => ({
        ...prev,
        micStatus: "ERROR",
        error: "PERMISSION_DENIED",
      }));
      updateNotice("Microphone permission was denied. Please allow microphone access.");
      return;
    }

    // Determine supported MIME and start MediaRecorder
    const mime = getSupportedAudioMime();
    actualMimeTypeRef.current = mime;

    try {
      const recorder = new MediaRecorder(stream, { mimeType: mime });
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      recorder.onstop = async () => {
        if (audioChunksRef.current.length > 0) {
          const fullBlob = new Blob(audioChunksRef.current, { type: actualMimeTypeRef.current });
          lastRecordedBlobRef.current = fullBlob;
          setDebugInfo((prev) => ({
            ...prev,
            blobSize: fullBlob.size,
            mimeType: actualMimeTypeRef.current,
          }));
          await uploadAndTranscribe(fullBlob);
        } else {
          setSpeechState(SPEECH_STATES.ERROR);
          updateNotice("Empty audio recording received.");
        }
      };

      // Gather slices into memory
      recorder.start(400);

      setSpeechState(SPEECH_STATES.RECORDING);
      setActiveEngine("media_recorder_gemini");
      updateNotice("Recording your answer... Speak naturally.");

      // Start elapsed recording timer
      let secs = 0;
      if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = setInterval(() => {
        secs += 1;
        setElapsedSeconds(secs);
      }, 1000);

      setDebugInfo((prev) => ({
        ...prev,
        micStatus: "RECORDING",
        engine: "media_recorder_gemini",
        connection: "CONNECTED",
        mimeType: mime,
      }));

      // Optional non-authoritative live preview via Web Speech (if available)
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRecognition) {
        try {
          const preview = new SpeechRecognition();
          preview.continuous = true;
          preview.interimResults = true;
          preview.lang = language || "en-IN";

          preview.onresult = (evt) => {
            if (isExplicitlyStoppedRef.current) return;
            let interim = "";
            for (let i = 0; i < evt.results.length; ++i) {
              interim += evt.results[i][0]?.transcript || "";
            }
            if (interim.trim()) {
              setLivePreviewText(interim.trim());
            }
          };

          preview.onerror = () => {
            // Non-authoritative preview errors are completely non-fatal
          };

          preview.start();
          webSpeechPreviewRef.current = preview;
        } catch {}
      }
    } catch (recErr) {
      console.warn("[SPEECH] MediaRecorder start error:", recErr);
      setSpeechState(SPEECH_STATES.ERROR);
      updateNotice("Could not start audio recorder on your system.");
      releaseMicrophone();
    }
  }, [
    language,
    releaseMicrophone,
    startAudioLevelMonitoring,
    textOnly,
    updateNotice,
    uploadAndTranscribe,
  ]);

  // Stop Speaking / Finalize and upload
  const stopListening = useCallback(async () => {
    isExplicitlyStoppedRef.current = true;
    setSpeechState(SPEECH_STATES.STOPPING);
    updateNotice("Processing recorded audio...");

    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }

    // Stop and discard non-authoritative live preview
    if (webSpeechPreviewRef.current) {
      try {
        webSpeechPreviewRef.current.abort();
      } catch {}
      webSpeechPreviewRef.current = null;
    }
    setLivePreviewText("");

    // Stop MediaRecorder (triggers recorder.onstop -> uploadAndTranscribe)
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      try {
        mediaRecorderRef.current.stop();
      } catch (err) {
        console.warn("[SPEECH] MediaRecorder stop error:", err);
      }
    }
  }, [updateNotice]);

  // Handle manual typing so speech appends smoothly
  const notifyManualTextChange = useCallback((newText) => {
    baseTextRef.current = newText;
    latestAnswerRef.current = newText;
  }, []);

  // Reset transcript for new question
  const resetTranscript = useCallback(() => {
    isExplicitlyStoppedRef.current = true;
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }
    if (webSpeechPreviewRef.current) {
      try {
        webSpeechPreviewRef.current.abort();
      } catch {}
      webSpeechPreviewRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      try {
        mediaRecorderRef.current.stop();
      } catch {}
    }
    releaseMicrophone();

    baseTextRef.current = "";
    latestAnswerRef.current = "";
    lastRecordedBlobRef.current = null;
    audioChunksRef.current = [];
    setElapsedSeconds(0);
    setLivePreviewText("");

    setSpeechState(SPEECH_STATES.IDLE);
    setActiveEngine("none");
    setSpeechNotice("");
    setAudioLevel(0.0);
    setDebugInfo((prev) => ({
      ...prev,
      micStatus: "IDLE",
      audioLevel: 0.0,
      engine: "none",
      connection: "DISCONNECTED",
      error: null,
      recordingDuration: 0,
      blobSize: 0,
    }));
  }, [releaseMicrophone]);

  // Clean unmount
  useEffect(() => {
    return () => {
      isExplicitlyStoppedRef.current = true;
      if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
      if (webSpeechPreviewRef.current) {
        try {
          webSpeechPreviewRef.current.abort();
        } catch {}
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        try {
          mediaRecorderRef.current.stop();
        } catch {}
      }
      releaseMicrophone();
    };
  }, [releaseMicrophone]);

  return {
    speechState,
    speechNotice,
    speechSupported,
    audioLevel,
    activeEngine,
    elapsedSeconds,
    formattedTime: formatRecordingTime(elapsedSeconds),
    livePreviewText,
    debugInfo,
    isListening: speechState === SPEECH_STATES.RECORDING,
    isRecording: speechState === SPEECH_STATES.RECORDING,
    isTranscribing:
      speechState === SPEECH_STATES.STOPPING ||
      speechState === SPEECH_STATES.UPLOADING ||
      speechState === SPEECH_STATES.TRANSCRIBING,
    startListening,
    stopListening,
    retryTranscription,
    resetTranscript,
    notifyManualTextChange,
    lastRecordedBlob: lastRecordedBlobRef.current,
  };
}
