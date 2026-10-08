import React, { useState, useEffect, useRef, useContext } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { FaceMesh } from "@mediapipe/face_mesh";
import { ReportContext } from "../context/ReportContext";
import { apiFetch } from "../utils/api";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { useSpeechRecognition, SPEECH_STATES } from "../utils/useSpeechRecognition";
import {
  FACE_STATES,
  ALIGNMENT_STATES,
  classifyCameraFrame,
  calculateFaceBoundingBox,
  FaceTemporalSmoother,
  evaluateCameraAlignment,
  BlinkDetector,
  HeadMovementTracker,
  ExpressionActivityTracker,
  calculatePresentationSignals,
} from "../utils/cameraTrackingLogic";
import {
  InterviewLifecycleState,
  setInterviewLifecycleState,
  isStateProtected,
  clearInterviewActiveState,
} from "../utils/interviewLifecycle";

/**
 * Authoritative Camera State Machine:
 * CAMERA_IDLE | CAMERA_REQUESTING | CAMERA_READY | CAMERA_ERROR | CAMERA_STOPPED
 */
export const CAMERA_STATES = {
  IDLE: "CAMERA_IDLE",
  REQUESTING: "CAMERA_REQUESTING",
  READY: "CAMERA_READY",
  ERROR: "CAMERA_ERROR",
  STOPPED: "CAMERA_STOPPED",
};

/**
 * Authoritative runtime camera stream & frame verification.
 * Camera is considered READY ONLY if:
 * 1. Stream exists with at least one video track
 * 2. Track is 'live' and enabled
 * 3. video.srcObject === stream
 * 4. video.readyState >= HAVE_CURRENT_DATA (valid pixel buffer exists)
 * 5. video.videoWidth > 0 and video.videoHeight > 0
 * 6. video is not paused and not ended
 */
export const isVideoFrameAuthoritative = (video, stream) => {
  if (!video || !stream) return false;
  const tracks = stream.getVideoTracks();
  if (!tracks || tracks.length === 0) return false;
  const track = tracks[0];
  if (track.readyState !== "live" || !track.enabled) return false;
  if (video.srcObject !== stream) return false;
  if (video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) return false;
  if (video.videoWidth <= 0 || video.videoHeight <= 0) return false;
  if (video.paused || video.ended) return false;
  return true;
};

function Interview() {
  const navigate = useNavigate();
  const location = useLocation();
  const { setCurrentSessionId, setReportData } = useContext(ReportContext);

  // Restore state from location or sessionStorage
  const savedState = (() => {
    try {
      return JSON.parse(sessionStorage.getItem("interviewSetupState") || "{}");
    } catch {
      return {};
    }
  })();

  const sessionId = location.state?.sessionId || savedState.sessionId || 1;
  const initialMode = location.state?.mode || savedState.mode || "technical";
  const [currentMode, setCurrentMode] = useState(initialMode);
  const difficulty = location.state?.difficulty || savedState.difficulty || "medium";
  const targetRole = location.state?.targetRole || savedState.targetRole || "Software Engineer";
  const textOnly = Boolean(location.state?.textOnly ?? savedState.textOnly ?? false);
  const totalQuestionBudget = location.state?.questionCount || savedState.questionCount || 5;
  const sessionPolicy = location.state?.sessionPolicy || savedState.sessionPolicy || "STANDARD";
  const questionMode = location.state?.questionMode || savedState.questionMode || "ADAPTIVE";
  const isPracticeDrill = Boolean(location.state?.isPracticeDrill || savedState.isPracticeDrill || currentMode === "drill");

  const initialQuestions = location.state?.questions || savedState.questions || [
    { id: 1, question: "Explain REST API architecture and how HTTP status codes are utilized." },
    { id: 2, question: "Describe a challenging technical problem you solved in your past project." },
    { id: 3, question: "How do you handle database indexing and optimize slow queries?" },
    { id: 4, question: "What is the difference between SQL and NoSQL databases?" },
    { id: 5, question: "Explain the CAP theorem and how it applies to distributed systems." },
  ];

  const [questions, setQuestions] = useState(initialQuestions);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [timeLeft, setTimeLeft] = useState(currentMode === "pressure" ? 45 : 90);
  const [answer, setAnswer] = useState("");

  // Authoritative Camera & sensor states (CAMERA_IDLE | CAMERA_REQUESTING | CAMERA_READY | CAMERA_ERROR | CAMERA_STOPPED)
  const [cameraState, setCameraState] = useState(textOnly ? CAMERA_STATES.STOPPED : CAMERA_STATES.IDLE);
  const [cameraNotice, setCameraNotice] = useState("");
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [isMicOn, setIsMicOn] = useState(false);
  const [eyeContactPercent, setEyeContactPercent] = useState(null);
  const [blinkCount, setBlinkCount] = useState(0);
  const [visualCoverage, setVisualCoverage] = useState(null);

  // Speech-to-text recognition via resilient continuous state machine hook
  const [inputMode, setInputMode] = useState(textOnly ? "text" : "mic"); // mic | text
  const [submitError, setSubmitError] = useState(null);

  const {
    speechState,
    speechNotice,
    speechSupported,
    audioLevel,
    activeEngine,
    debugInfo,
    isListening,
    isRecording,
    isTranscribing,
    formattedTime,
    livePreviewText,
    startListening,
    stopListening,
    retryTranscription,
    resetTranscript,
    notifyManualTextChange,
    speechSegments,
  } = useSpeechRecognition({
    answer,
    setAnswer,
    textOnly,
    sessionId,
  });

  const toggleSpeechRecognition = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  const showDebugSpeech = typeof window !== "undefined" && new URLSearchParams(window.location.search).get("debugSpeech") === "1";
  const showDebugVision = typeof window !== "undefined" && new URLSearchParams(window.location.search).get("debugVision") === "1";

  // Distinct Face Model & Vision States:
  // MODEL_LOADING | MODEL_READY | MODEL_ERROR
  const [modelState, setModelState] = useState("IDLE");

  // Person Count State: { faceCount, state: ONE_FACE | NO_FACE | MULTIPLE_FACES | MODEL_LOADING | ANALYSIS_ERROR, isValidFrame, warning }
  const [personCountStatus, setPersonCountStatus] = useState({
    faceCount: 0,
    state: "INITIALIZING",
    isValidFrame: false,
    warning: null,
  });

  const [cameraAlignment, setCameraAlignment] = useState(null);
  const [presentationSignals, setPresentationSignals] = useState(null);
  const [visionFps, setVisionFps] = useState(0);

  // Question submission & progress state
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [loadingNext, setLoadingNext] = useState(false);
  const [submittingFinal, setSubmittingFinal] = useState(false);
  const [finalizationError, setFinalizationError] = useState(null);
  const [isFollowUp, setIsFollowUp] = useState(false);
  const [followUpQuestion, setFollowUpQuestion] = useState("");
  const [showEndConfirm, setShowEndConfirm] = useState(false);
  const [conversationHistory, setConversationHistory] = useState([]);
  const chatBottomRef = useRef(null);

  // Interview Lifecycle State Machine & Protection States
  const [lifecycleState, setLifecycleState] = useState(() => {
    const active = sessionStorage.getItem("interviewActive") === "true";
    return active ? InterviewLifecycleState.ACTIVE : InterviewLifecycleState.PREPARING;
  });

  const [interviewStarted, setInterviewStarted] = useState(() => {
    return sessionStorage.getItem("interviewActive") === "true";
  });
  const [isFullscreenActive, setIsFullscreenActive] = useState(false);
  const [showFullscreenNotice, setShowFullscreenNotice] = useState(false);
  const [showBackConfirm, setShowBackConfirm] = useState(false);
  const [micCheckState, setMicCheckState] = useState(textOnly ? "READY" : "CHECKING"); // CHECKING | READY | BLOCKED
  const [isInterviewPaused, setIsInterviewPaused] = useState(false);
  const [pauseReason, setPauseReason] = useState("");
  const [focusLostCount, setFocusLostCount] = useState(0);

  const focusLostAtRef = useRef(null);
  const focusLossEventsRef = useRef([]);
  const isFinalizingRef = useRef(false);
  const isSubmittingAnswerRef = useRef(false);

  // Synchronize lifecycle state to global storage for cross-component protection
  useEffect(() => {
    setInterviewLifecycleState(lifecycleState);
  }, [lifecycleState]);

  // Restore interview progress after page refresh
  useEffect(() => {
    try {
      const savedProgress = sessionStorage.getItem(`interviewProgress_${sessionId}`);
      if (savedProgress) {
        const parsed = JSON.parse(savedProgress);
        if (typeof parsed.currentIndex === "number" && parsed.currentIndex > 0) {
          setCurrentIndex(parsed.currentIndex);
        }
        if (Array.isArray(parsed.conversationHistory) && parsed.conversationHistory.length > 0) {
          setConversationHistory(parsed.conversationHistory);
        }
      }
      if (sessionStorage.getItem("interviewActive") === "true") {
        setInterviewStarted(true);
        setLifecycleState(InterviewLifecycleState.ACTIVE);
      }
    } catch (e) {
      console.warn("Interview progress restoration warning:", e);
    }
  }, [sessionId]);

  // Browser Back Button Navigation Guard (popstate interception)
  useEffect(() => {
    if (!isStateProtected(lifecycleState)) return;

    // Push guard state into browser history to intercept Back button
    window.history.pushState({ interviewGuard: true }, "", window.location.href);

    const handlePopState = (e) => {
      // Re-push immediately to keep current URL and route intact
      window.history.pushState({ interviewGuard: true }, "", window.location.href);
      setShowBackConfirm(true);
    };

    window.addEventListener("popstate", handlePopState);
    return () => {
      window.removeEventListener("popstate", handlePopState);
    };
  }, [lifecycleState]);

  const testMicrophonePermission = async () => {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setMicCheckState("BLOCKED");
        return;
      }
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((t) => t.stop());
      setMicCheckState("READY");
    } catch {
      setMicCheckState("BLOCKED");
    }
  };

  const requestInterviewFullscreen = async () => {
    try {
      const elem = document.documentElement;
      if (elem.requestFullscreen) {
        await elem.requestFullscreen();
      } else if (elem.webkitRequestFullscreen) {
        await elem.webkitRequestFullscreen();
      }
      setIsFullscreenActive(true);
      setShowFullscreenNotice(false);
      return true;
    } catch (err) {
      console.warn("Fullscreen request error:", err);
      return false;
    }
  };

  const startInterviewSession = async () => {
    if (!textOnly && (cameraState === "DENIED" || micCheckState === "BLOCKED")) {
      alert("Please ensure camera and microphone permissions are granted before starting.");
      return;
    }
    try {
      if (!document.fullscreenElement) {
        await requestInterviewFullscreen();
      }
    } catch {}
    setInterviewStarted(true);
    setLifecycleState(InterviewLifecycleState.ACTIVE);
    sessionStorage.setItem("interviewActive", "true");
    interviewStartRef.current = Date.now();
  };

  // Check initial microphone status
  useEffect(() => {
    if (textOnly) {
      setMicCheckState("READY");
      return;
    }
    async function checkMic() {
      try {
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          stream.getTracks().forEach((t) => t.stop());
          setMicCheckState("READY");
        } else {
          setMicCheckState("BLOCKED");
        }
      } catch {
        setMicCheckState("CHECKING");
      }
    }
    checkMic();
  }, [textOnly]);

  // Fullscreen change listener (Decoupled from interview state - never freezes interview)
  useEffect(() => {
    const handleFullscreenChange = () => {
      const isFull = Boolean(document.fullscreenElement || document.webkitFullscreenElement);
      setIsFullscreenActive(isFull);
      if (!isFull && interviewStarted && !isSubmitted) {
        setShowFullscreenNotice(true);
      } else if (isFull) {
        setShowFullscreenNotice(false);
      }
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    document.addEventListener("webkitfullscreenchange", handleFullscreenChange);
    return () => {
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
      document.removeEventListener("webkitfullscreenchange", handleFullscreenChange);
    };
  }, [interviewStarted, isSubmitted]);

  // Tab switch / visibility loss listener (preserves interview state)
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden && interviewStarted && !isSubmitted) {
        focusLostAtRef.current = Date.now();
        setFocusLostCount((prev) => prev + 1);
        focusLostAtRef.current = Date.now();
        setFocusLostCount((prev) => prev + 1);
        if (isListening) {
          try { stopListening(); } catch {}
        }
      } else if (!document.hidden && interviewStarted && !isSubmitted) {
        if (focusLostAtRef.current) {
          const duration = Date.now() - focusLostAtRef.current;
          focusLossEventsRef.current.push({
            lost_at: focusLostAtRef.current,
            returned_at: Date.now(),
            duration_ms: duration,
          });
          focusLostAtRef.current = null;
        }
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [interviewStarted, isSubmitted, isListening, stopListening]);

  // Window close / beforeunload prompt
  useEffect(() => {
    if (!interviewStarted || isSubmitted) return;
    const handleBeforeUnload = (e) => {
      e.preventDefault();
      e.returnValue = "Your interview session is active. Are you sure you want to leave?";
      return e.returnValue;
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, [interviewStarted, isSubmitted]);

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversationHistory, currentIndex, isFollowUp]);

  // Sensor calculation refs
  const blinkRef = useRef(false);
  const totalFramesRef = useRef(0);
  const eyeContactFramesRef = useRef(0);
  const interviewStartRef = useRef(Date.now());
  const questionStartTimeRef = useRef(Date.now());
  const answerVisualFramesRef = useRef({
    totalSampled: 0,
    faceDetected: 0,
    alignedCount: 0,
    blinks: 0,
    positions: [],
    lastPosition: null,
    shifts: 0,
  });

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const debugCanvasRef = useRef(null);
  const streamRef = useRef(null);
  const faceMeshRef = useRef(null);
  const modelReadyRef = useRef(false);
  const animationFrameIdRef = useRef(null);
  const smootherRef = useRef(new FaceTemporalSmoother());
  const blinkDetectorRef = useRef(new BlinkDetector());
  const headTrackerRef = useRef(new HeadMovementTracker());
  const expressionTrackerRef = useRef(new ExpressionActivityTracker());
  const lastAnalysisTimeRef = useRef(0);
  const isAnalyzingFrameRef = useRef(false);
  const fpsFramesCountRef = useRef(0);
  const fpsLastCalcTimeRef = useRef(Date.now());
  const totalAnalyzedFramesRef = useRef(0);
  const validSingleFramesRef = useRef(0);
  const invalidFramesCountRef = useRef(0);
  const lastUiUpdateRef = useRef(0);

  const currentQ = questions[currentIndex] || { id: 1, question: "Interview Question" };

  // Timer countdown
  useEffect(() => {
    if (timeLeft <= 0 || isSubmitted) return;
    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          if (isListening) {
            try { stopListening(); } catch {}
          }
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [timeLeft, isSubmitted, isListening, stopListening]);

  // Reset timer & state on question change
  useEffect(() => {
    const defaultTime = currentMode === "pressure" ? 45 : (currentQ.time_limit_seconds || 90);
    setTimeLeft(defaultTime);
    setAnswer("");
    setIsSubmitted(false);
    setSubmitError(null);
    setFinalizationError(null);
    questionStartTimeRef.current = Date.now();
    resetTranscript();
    answerVisualFramesRef.current = {
      totalSampled: 0,
      validFrames: 0,
      faceDetected: 0,
      alignedCount: 0,
      blinks: 0,
      positions: [],
      lastPosition: null,
      shifts: 0,
    };
  }, [currentIndex, currentMode, resetTranscript]);

  // Single source of truth: Load authoritative persisted turns from backend on mount (Part 12)
  useEffect(() => {
    let active = true;
    async function loadPersistedTurns() {
      try {
        const res = await apiFetch(`/interview/${sessionId}/turns`);
        if (res.ok && active) {
          const data = await res.json();
          if (Array.isArray(data.turns) && data.turns.length > 0) {
            const formatted = data.turns.map((t) => ({
              id: t.turn_id,
              qId: t.question_id,
              question: t.question_text,
              caption: t.category || "Technical Question",
              answer: t.answer_text,
              isSkipped: t.answer_status === "SKIPPED",
              status: t.answer_status?.toLowerCase(),
              score: t.score,
              timestamp: t.created_at ? new Date(t.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "",
            }));
            setConversationHistory(formatted);
          }
        }
      } catch (err) {
        console.warn("Could not load initial turns:", err);
      }
    }
    if (sessionId) {
      loadPersistedTurns();
    }
    return () => { active = false; };
  }, [sessionId]);

  // Background MediaPipe FaceMesh & Camera Stream Setup (Authoritative Single-Video Pipeline)
  useEffect(() => {
    if (textOnly) {
      setCameraState(CAMERA_STATES.STOPPED);
      setIsCameraOn(false);
      return;
    }

    let isSubscribed = true;

    async function initCamera() {
      setCameraState(CAMERA_STATES.REQUESTING);
      setCameraNotice("Requesting camera authorization...");
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 1280 },
            height: { ideal: 720 },
            facingMode: "user",
          },
          audio: false,
        });

        if (!isSubscribed) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }

        const videoTracks = stream.getVideoTracks();
        if (videoTracks.length > 0) {
          const track = videoTracks[0];
          console.log("[FACE] Camera video track acquired:", {
            readyState: track.readyState,
            enabled: track.enabled,
            settings: track.getSettings ? track.getSettings() : {},
          });
        }

        streamRef.current = stream;
        const video = videoRef.current;
        if (video) {
          video.srcObject = stream;
          try {
            await video.play();
          } catch (playErr) {
            console.warn("[FACE] Camera video play warning:", playErr);
          }

          const verifyVideoReady = () => {
            if (!isSubscribed) return;
            if (isVideoFrameAuthoritative(video, stream)) {
              setIsCameraOn(true);
              setCameraState(CAMERA_STATES.READY);
              setCameraNotice("");
              console.log("[FACE] Authoritative video stream ready:", {
                videoWidth: video.videoWidth,
                videoHeight: video.videoHeight,
                readyState: video.readyState,
              });
            } else {
              setTimeout(verifyVideoReady, 100);
            }
          };
          verifyVideoReady();
        }

        // Initialize MediaPipe FaceMesh model with explicit state machine (Sections 7 & 8)
        setModelState("MODEL_LOADING");
        setPersonCountStatus({
          faceCount: 0,
          state: FACE_STATES.MODEL_LOADING,
          isValidFrame: false,
          warning: "Loading face detection model...",
        });

        const faceMesh = new FaceMesh({
          locateFile: (file) => `/mediapipe/face_mesh/${file}`,
        });

        faceMesh.setOptions({
          maxNumFaces: 4,
          refineLandmarks: true,
          minDetectionConfidence: 0.5,
          minTrackingConfidence: 0.5,
        });

        // Explicitly await model initialization before feeding any frames
        await faceMesh.initialize();
        if (!isSubscribed) {
          try { faceMesh.close(); } catch {}
          return;
        }

        faceMeshRef.current = faceMesh;
        modelReadyRef.current = true;
        setModelState("MODEL_READY");
        console.log("[FACE] MediaPipe FaceMesh model initialized successfully. modelReady=true");

        faceMesh.onResults((results) => {
          if (!isSubscribed) return;
          const currentVideo = videoRef.current;
          const currentStream = streamRef.current;

          // Guard: Only process telemetry if video frame is authoritative & currently playing
          if (!isVideoFrameAuthoritative(currentVideo, currentStream)) {
            return;
          }

          const now = Date.now();
          const multiFaceLandmarks = results.multiFaceLandmarks || [];
          const rawClassification = classifyCameraFrame(multiFaceLandmarks);
          const smoothed = smootherRef.current.update(rawClassification, now);

          totalAnalyzedFramesRef.current += 1;
          fpsFramesCountRef.current += 1;

          const w = currentVideo.videoWidth || 640;
          const h = currentVideo.videoHeight || 480;

          // Track analysis FPS
          if (now - fpsLastCalcTimeRef.current >= 1000) {
            const elapsed = (now - fpsLastCalcTimeRef.current) / 1000;
            const currentFps = Number((fpsFramesCountRef.current / elapsed).toFixed(1));
            setVisionFps(currentFps);
            fpsFramesCountRef.current = 0;
            fpsLastCalcTimeRef.current = now;
          }

          let alignmentInfo = null;
          let blinkInfo = null;

          if (smoothed.smoothedState === FACE_STATES.ONE_FACE && multiFaceLandmarks.length >= 1) {
            validSingleFramesRef.current += 1;
            const landmarks = multiFaceLandmarks[0];

            // Evaluate camera alignment
            alignmentInfo = evaluateCameraAlignment(landmarks);

            // Blink detection
            blinkInfo = blinkDetectorRef.current.processFrame(landmarks, now);
            if (blinkInfo && blinkInfo.blinkCount !== blinkCount) {
              setBlinkCount(blinkInfo.blinkCount);
            }

            // Head movement
            headTrackerRef.current.processFrame(landmarks, now);

            // Expression activity
            expressionTrackerRef.current.processFrame(landmarks, now);

            // Aggregate question visual frames
            const av = answerVisualFramesRef.current;
            av.totalSampled += 1;
            av.validFrames = (av.validFrames || 0) + 1;
            av.faceDetected += 1;
            if (alignmentInfo && alignmentInfo.status === ALIGNMENT_STATES.GOOD) {
              av.alignedCount += 1;
            }
            if (blinkInfo) {
              av.blinks = blinkInfo.blinkCount;
            }

            if (av.validFrames % 30 === 0) {
              const currentPercent = (av.alignedCount / av.validFrames) * 100;
              setEyeContactPercent(Number(currentPercent.toFixed(1)));
            }

            if (av.totalSampled % 15 === 0 && av.totalSampled > 0) {
              const cov = Math.round(((av.validFrames || 0) / av.totalSampled) * 100);
              setVisualCoverage(cov);
            }
          } else {
            invalidFramesCountRef.current += 1;
            const av = answerVisualFramesRef.current;
            av.totalSampled += 1;
          }

          // Render tracked bounding boxes and debug HUD on canvas (Section 10 & 34)
          const canvas = canvasRef.current;
          if (canvas) {
            if (canvas.width !== w || canvas.height !== h) {
              canvas.width = w;
              canvas.height = h;
            }
            const ctx = canvas.getContext("2d");
            ctx.clearRect(0, 0, w, h);

            if (multiFaceLandmarks.length === 1) {
              const box = calculateFaceBoundingBox(multiFaceLandmarks[0], w, h);
              if (box) {
                // Video preview has CSS transform: scaleX(-1), so mirror box X coordinate
                const mirroredX = w - (box.x + box.width);
                ctx.strokeStyle = "#10b981";
                ctx.lineWidth = 2.5;
                ctx.strokeRect(mirroredX, box.y, box.width, box.height);
                ctx.fillStyle = "rgba(16, 185, 129, 0.9)";
                ctx.fillRect(mirroredX, Math.max(0, box.y - 22), 114, 20);
                ctx.fillStyle = "#ffffff";
                ctx.font = "bold 11px sans-serif";
                ctx.fillText("1 person detected", mirroredX + 6, Math.max(0, box.y - 22) + 14);
              }
            } else if (multiFaceLandmarks.length > 1) {
              for (let f = 0; f < multiFaceLandmarks.length; f++) {
                const box = calculateFaceBoundingBox(multiFaceLandmarks[f], w, h);
                if (box) {
                  const mirroredX = w - (box.x + box.width);
                  ctx.strokeStyle = "#ef4444";
                  ctx.lineWidth = 3.5;
                  ctx.strokeRect(mirroredX, box.y, box.width, box.height);
                  ctx.fillStyle = "rgba(239, 68, 68, 0.95)";
                  ctx.fillRect(mirroredX, Math.max(0, box.y - 22), 140, 20);
                  ctx.fillStyle = "#ffffff";
                  ctx.font = "bold 11px sans-serif";
                  ctx.fillText("Multiple people detected", mirroredX + 6, Math.max(0, box.y - 22) + 14);
                }
              }
            }

            // Diagnostic HUD when ?debugVision=1 (Section 10 & 34)
            if (showDebugVision) {
              ctx.fillStyle = "rgba(15, 23, 42, 0.88)";
              ctx.fillRect(10, 10, 210, 165);
              ctx.strokeStyle = "rgba(56, 189, 248, 0.4)";
              ctx.lineWidth = 1;
              ctx.strokeRect(10, 10, 210, 165);

              ctx.fillStyle = "#38bdf8";
              ctx.font = "bold 11px monospace";
              ctx.fillText("VISION DEBUG HUD", 18, 26);
              ctx.fillStyle = "#f8fafc";
              ctx.font = "10px monospace";
              ctx.fillText(`Camera: READY`, 18, 42);
              ctx.fillText(`Video: ${w}x${h}`, 18, 56);
              ctx.fillText(`Track: LIVE`, 18, 70);
              ctx.fillText(`Model: READY`, 18, 84);
              ctx.fillText(`FPS: ${(visionFps || 12).toFixed(1)}`, 18, 98);
              ctx.fillText(`Raw Faces: ${multiFaceLandmarks.length}`, 18, 112);
              ctx.fillText(`Smoothed: ${smoothed.smoothedState}`, 18, 126);
              ctx.fillText(`Valid Frames: ${validSingleFramesRef.current}`, 18, 140);
              ctx.fillText(`Invalid Frames: ${invalidFramesCountRef.current}`, 18, 154);
            }
          }

          // Throttle React state updates to ~300ms to avoid unnecessary rerenders (Section 32)
          if (now - lastUiUpdateRef.current >= 300) {
            lastUiUpdateRef.current = now;
            setPersonCountStatus({
              faceCount: smoothed.faceCount,
              state: smoothed.smoothedState,
              isValidFrame: smoothed.isValid,
              warning:
                smoothed.smoothedState === FACE_STATES.NO_FACE
                  ? "Face not detected"
                  : smoothed.smoothedState === FACE_STATES.MULTIPLE_FACES
                  ? "Multiple people detected. Please remain alone in the frame."
                  : null,
            });
            if (alignmentInfo) {
              setCameraAlignment(alignmentInfo);
            }
          }
        });

        // Launch controlled analysis loop targeting 10-15 FPS (Sections 5, 31, 32)
        const TARGET_INTERVAL_MS = 80; // ~12.5 FPS

        const runAnalysisLoop = () => {
          if (!isSubscribed) return;

          const scheduleNext = () => {
            if (!isSubscribed) return;
            const currentVid = videoRef.current;
            if (currentVid && typeof currentVid.requestVideoFrameCallback === "function") {
              currentVid.requestVideoFrameCallback(runAnalysisLoop);
            } else {
              animationFrameIdRef.current = requestAnimationFrame(runAnalysisLoop);
            }
          };

          const now = Date.now();
          if (now - lastAnalysisTimeRef.current < TARGET_INTERVAL_MS) {
            scheduleNext();
            return;
          }

          const currentVideo = videoRef.current;
          const currentStream = streamRef.current;
          const isAuthoritative = isVideoFrameAuthoritative(currentVideo, currentStream);

          if (!isAuthoritative || !modelReadyRef.current || !faceMeshRef.current || isAnalyzingFrameRef.current) {
            scheduleNext();
            return;
          }

          // Capture frame into debug/analysis canvas to verify frame is non-empty (Section 3)
          if (!debugCanvasRef.current) {
            debugCanvasRef.current = document.createElement("canvas");
          }
          const dCanvas = debugCanvasRef.current;
          if (dCanvas.width !== currentVideo.videoWidth || dCanvas.height !== currentVideo.videoHeight) {
            dCanvas.width = currentVideo.videoWidth;
            dCanvas.height = currentVideo.videoHeight;
          }
          const dCtx = dCanvas.getContext("2d");
          dCtx.drawImage(currentVideo, 0, 0, dCanvas.width, dCanvas.height);

          lastAnalysisTimeRef.current = now;
          isAnalyzingFrameRef.current = true;

          faceMeshRef.current
            .send({ image: currentVideo })
            .catch((frameErr) => {
              console.warn("[FACE] FaceMesh frame analysis error:", frameErr);
            })
            .finally(() => {
              isAnalyzingFrameRef.current = false;
              scheduleNext();
            });
        };

        const currentVideo = videoRef.current;
        if (currentVideo && typeof currentVideo.requestVideoFrameCallback === "function") {
          currentVideo.requestVideoFrameCallback(runAnalysisLoop);
        } else {
          animationFrameIdRef.current = requestAnimationFrame(runAnalysisLoop);
        }
      } catch (err) {
        console.warn("[FACE] Camera could not be accessed:", err);
        if (isSubscribed) {
          setIsCameraOn(false);
          setCameraState(CAMERA_STATES.ERROR);
          setCameraNotice("Camera permission denied or device unavailable. Proceeding in text/mic mode.");
        }
      }
    }

    initCamera();

    return () => {
      isSubscribed = false;
      setIsCameraOn(false);
      setCameraState(CAMERA_STATES.STOPPED);
      if (animationFrameIdRef.current) {
        cancelAnimationFrame(animationFrameIdRef.current);
        animationFrameIdRef.current = null;
      }
      modelReadyRef.current = false;
      if (faceMeshRef.current) {
        try { faceMeshRef.current.close(); } catch {}
        faceMeshRef.current = null;
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    };
  }, [textOnly, showDebugVision]);

  const retryCameraPermission = async () => {
    if (textOnly) return;
    setCameraNotice("Requesting camera access...");
    setCameraState(CAMERA_STATES.REQUESTING);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" },
        audio: false,
      });
      streamRef.current = stream;
      const video = videoRef.current;
      if (video) {
        video.srcObject = stream;
        try {
          await video.play();
        } catch {}
        setIsCameraOn(true);
        setCameraState(CAMERA_STATES.READY);
        setCameraNotice("");
      }
    } catch (err) {
      console.warn("[FACE] Camera retry failed:", err);
      setIsCameraOn(false);
      setCameraState(CAMERA_STATES.ERROR);
      setCameraNotice("Camera permission is required for visual interview analysis.");
    }
  };

  const toggleCamera = () => {
    if (cameraState === CAMERA_STATES.READY || isCameraOn) {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => (track.enabled = false));
      }
      setIsCameraOn(false);
      setCameraState(CAMERA_STATES.STOPPED);
      setCameraNotice("Camera disabled by candidate.");
    } else {
      if (streamRef.current && streamRef.current.getVideoTracks().length > 0) {
        streamRef.current.getTracks().forEach((track) => (track.enabled = true));
        if (videoRef.current) {
          try { videoRef.current.play(); } catch {}
        }
        setIsCameraOn(true);
        setCameraState(CAMERA_STATES.READY);
        setCameraNotice("");
      } else {
        retryCameraPermission();
      }
    }
  };

  // Handle Answer Submission with instant feedback and auto-advance
  const handleSubmitAnswer = async () => {
    if (evaluating || loadingNext || submittingFinal || isSubmittingAnswerRef.current) return;
    isSubmittingAnswerRef.current = true;

    if (isListening) {
      try { stopListening(); } catch {}
    }

    if (!answer.trim()) {
      setSubmitError("Please speak or type your answer before submitting.");
      isSubmittingAnswerRef.current = false;
      return;
    }

    setEvaluating(true);
    setSubmitError(null);
    setLifecycleState(InterviewLifecycleState.SUBMITTING);

    const isTyped = inputMode === "text";
    const responseDuration = (Date.now() - questionStartTimeRef.current) / 1000;
    const words = answer.trim().split(/\s+/).filter(Boolean).length;
    const liveWpm = responseDuration > 0 ? Number(((words / responseDuration) * 60).toFixed(1)) : 0;

    const av = answerVisualFramesRef.current;
    const currentBlinkRate = blinkDetectorRef.current ? blinkDetectorRef.current.getBlinkRate() : 0;
    const headMetrics = headTrackerRef.current ? headTrackerRef.current.getStabilityMetrics() : null;
    const expressionLevel = expressionTrackerRef.current ? expressionTrackerRef.current.getActivityLevel() : "MODERATE";

    const presentationResult = calculatePresentationSignals({
      totalSampledFrames: av.totalSampled,
      validSingleFaceFrames: av.validFrames || 0,
      alignedCount: av.alignedCount || 0,
      blinkRate: currentBlinkRate,
      headStability: headMetrics?.stability || "STABLE",
      facingCameraPercent: headMetrics?.facingCameraPercent || 90,
      expressionActivity: expressionLevel,
      minValidFramesRequired: 15,
    });

    const visualPayload = isCameraOn && av.totalSampled > 0
      ? {
          head_alignment_percent: presentationResult.hasSufficientData ? (av.validFrames > 0 ? Number(((av.alignedCount / av.validFrames) * 100).toFixed(1)) : null) : null,
          blink_rate: presentationResult.hasSufficientData && responseDuration > 0 ? Number((av.blinks / (responseDuration / 60)).toFixed(1)) : null,
          face_visibility_ratio: av.totalSampled > 0 ? Number((((av.validFrames || 0) / av.totalSampled)).toFixed(2)) : null,
          frames_sampled: av.totalSampled,
          valid_frames: av.validFrames || 0,
          presentation_score: presentationResult.presentationScore,
          presentation_signals: presentationResult,
        }
      : null;

    try {
      const payload = {
        session_id: Number(sessionId),
        question_id: currentQ.id || currentIndex + 1,
        question_text: isFollowUp ? followUpQuestion : currentQ.question,
        transcript: answer,
        response_time: responseDuration,
        duration_seconds: responseDuration,
        wpm: liveWpm,
        filler_count: 0,
        speech_segments: isTyped ? null : (speechSegments && speechSegments.length > 0 ? speechSegments : null),
        speech_source: isTyped ? "typed" : "speech",
        visual_metrics: visualPayload,
      };

      const res = await apiFetch(`/interview/${sessionId}/answer`, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error("Answer recording failed on server.");
      }

      const answerResp = await res.json();

      // Record turn into persistent conversation thread using authoritative server data
      const currentPromptText = isFollowUp ? followUpQuestion : currentQ.question;
      const turnRecord = {
        id: answerResp.turn_id || answerResp.answer_id || Date.now(),
        qId: currentQ.id || currentIndex + 1,
        question: currentPromptText,
        caption: currentQ.caption || (isFollowUp ? "Deep-Dive Follow-Up" : "Technical Question"),
        answer: answer.trim() || "[Submitted Answer]",
        isSkipped: false,
        status: answerResp.answer_status?.toLowerCase() || "answered",
        score: answerResp.score,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setConversationHistory((prev) => [...prev, turnRecord]);

      // Automatically fetch next question without requiring manual second click
      const nextRes = await apiFetch(`/interview/${sessionId}/next`, { method: "POST" });
      if (nextRes.ok) {
        const nextData = await nextRes.json();
        if (nextData.done) {
          await handleFinishInterview();
          return;
        }

        if (nextData.question) {
          const nextQ = {
            id: nextData.question.id,
            question: nextData.question.question || nextData.question.question_text,
            caption: nextData.question.caption || null,
            time_limit_seconds: nextData.question.time_limit_seconds || 90,
            question_type: nextData.question.question_type || "technical",
            difficulty: nextData.question.difficulty || difficulty,
          };
          setQuestions((prev) => [...prev, nextQ]);
          setCurrentIndex((prev) => prev + 1);
          setAnswer("");
          setIsFollowUp(false);
          setFollowUpQuestion("");
          return;
        }
      }

      // Fallback: local queue progression or finish
      if (currentIndex < questions.length - 1) {
        setCurrentIndex((prev) => prev + 1);
        setAnswer("");
      } else {
        await handleFinishInterview();
      }
    } catch (err) {
      console.warn("Answer submission notice (preserving transcript):", err);
      setSubmitError("Your answer wasn't submitted due to a network issue. Your transcript is preserved.");
    } finally {
      setEvaluating(false);
      isSubmittingAnswerRef.current = false;
      setLifecycleState(InterviewLifecycleState.ACTIVE);
    }
  };

  // Handle Skip / I Don't Know
  const handleSkipQuestion = async () => {
    if (evaluating || loadingNext || submittingFinal) return;

    if (isListening) {
      try { stopListening(); } catch {}
    }

    setLoadingNext(true);
    setSubmitError(null);

    try {
      const payload = {
        session_id: Number(sessionId),
        question_id: currentQ.id || currentIndex + 1,
        question_text: isFollowUp ? followUpQuestion : currentQ.question,
        reason: "candidate_skipped",
      };

      const res = await apiFetch(`/interview/${sessionId}/skip`, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const data = await res.json();
        // Record skipped turn in conversation thread
        const currentPromptText = isFollowUp ? followUpQuestion : currentQ.question;
        const skipRecord = {
          id: data.turn_id || Date.now(),
          qId: currentQ.id || currentIndex + 1,
          question: currentPromptText,
          caption: currentQ.caption || "Skipped Question",
          answer: "Candidate chose not to answer this question.",
          isSkipped: true,
          status: "skipped",
          score: null,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        };
        setConversationHistory((prev) => [...prev, skipRecord]);

        if (data.done) {
          await handleFinishInterview();
          return;
        }

        if (data.question) {
          const nextQ = {
            id: data.question.id,
            question: data.question.question || data.question.question_text,
            caption: data.question.caption || null,
            time_limit_seconds: data.question.time_limit_seconds || 90,
            question_type: data.question.question_type || "technical",
            difficulty: data.question.difficulty || difficulty,
          };
          setQuestions((prev) => [...prev, nextQ]);
          setCurrentIndex((prev) => prev + 1);
          setAnswer("");
          setIsFollowUp(false);
          setFollowUpQuestion("");
          return;
        }
      }

      // Fallback
      if (currentIndex < questions.length - 1) {
        setCurrentIndex((prev) => prev + 1);
        setAnswer("");
      } else {
        await handleFinishInterview();
      }
    } catch (err) {
      console.warn("Skip question error:", err);
      if (currentIndex < questions.length - 1) {
        setCurrentIndex((prev) => prev + 1);
        setAnswer("");
      } else {
        await handleFinishInterview();
      }
    } finally {
      setLoadingNext(false);
    }
  };

  // Proceed to next question via adaptive policy (fallback action)
  const handleProceed = async () => {
    setLoadingNext(true);

    try {
      const res = await apiFetch(`/interview/${sessionId}/next`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        if (data.done) {
          await handleFinishInterview();
          return;
        }

        if (data.question) {
          const nextQ = {
            id: data.question.id,
            question: data.question.question || data.question.question_text,
            caption: data.question.caption || null,
            time_limit_seconds: data.question.time_limit_seconds || 90,
            question_type: data.question.question_type || "technical",
            difficulty: data.question.difficulty || difficulty,
          };
          setQuestions((prev) => [...prev, nextQ]);
          setCurrentIndex((prev) => prev + 1);
          setIsFollowUp(false);
          setFollowUpQuestion("");
          return;
        }
      }
    } catch (err) {
      console.warn("Adaptive next question fetch notice:", err);
    } finally {
      setLoadingNext(false);
    }

    // Local queue fallback
    if (currentIndex < questions.length - 1) {
      setCurrentIndex((prev) => prev + 1);
    } else {
      handleFinishInterview();
    }
  };

  // Complete interview and navigate to Report
  const handleFinishInterview = async () => {
    if (isFinalizingRef.current) return;
    isFinalizingRef.current = true;

    setSubmittingFinal(true);
    setFinalizationError(null);
    setLifecycleState(InterviewLifecycleState.ENDING);

    try {
      // 1. Stop active speech recognition and tracks
      if (isListening) {
        try { stopListening(); } catch {}
      }
      if (streamRef.current) {
        try { streamRef.current.getTracks().forEach((t) => t.stop()); } catch {}
      }
      if (document.fullscreenElement) {
        try { await document.exitFullscreen(); } catch {}
      }

      const durationSeconds = (Date.now() - interviewStartRef.current) / 1000;
      const durationMinutes = durationSeconds / 60 || 1;

      const finalEyeContact = isCameraOn && totalFramesRef.current > 0 && eyeContactPercent !== null
        ? eyeContactPercent
        : null;
      const finalBlinkRate = isCameraOn && totalFramesRef.current > 0
        ? Number((blinkCount / durationMinutes).toFixed(1))
        : null;

      const payload = {
        eye_contact_percent: finalEyeContact,
        blink_rate: finalBlinkRate,
        pause_rate: 2.0,
        duration_seconds: durationSeconds,
      };

      const res = await apiFetch(`/interview/${sessionId}/complete`, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData?.error?.message || errData?.detail || "Session finalization failed.");
      }

      const finalReport = await res.json();
      setReportData(finalReport);
      sessionStorage.setItem("interviewCompleted", "true");
      sessionStorage.setItem("currentSessionId", String(sessionId));
      sessionStorage.removeItem(`interviewProgress_${sessionId}`);

      setLifecycleState(InterviewLifecycleState.COMPLETED);
      clearInterviewActiveState();

      navigate(`/report?sessionId=${sessionId}`);
    } catch (err) {
      console.error("Interview complete error:", err);
      setFinalizationError(`Finalization Error: ${err.message}. Please click 'Retry Finalization' to continue.`);
      isFinalizingRef.current = false;
      setSubmittingFinal(false);
      setLifecycleState(InterviewLifecycleState.ACTIVE);
    }
  };

  // De-escalate from pressure mode to standard
  const handleSwitchToStandard = async () => {
    try {
      const res = await apiFetch(`/interview/${sessionId}/switch-mode`, { method: "POST" });
      if (res.ok) {
        setCurrentMode("technical");
        setTimeLeft(90);
        setSpeechNotice("Switched to standard timing. Time limit relaxed to 90 seconds.");
      }
    } catch (err) {
      console.warn("Mode switch notice:", err);
    }
  };

  const minutes = Math.floor(timeLeft / 60);
  const seconds = timeLeft % 60;
  const timeFormatted = `${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
  const isTimeLow = timeLeft <= 15;
  const wordCount = answer.trim().split(/\s+/).filter(Boolean).length;
  const totalCount = Math.max(questions.length, totalQuestionBudget);

  // Human readable category badge mapping
  const categoryLabel = (() => {
    if (isFollowUp) return "Deep-Dive Follow-Up";
    const type = (currentQ.question_type || currentQ.caption || "technical").toLowerCase();
    if (type.includes("resume") || type.includes("claim")) return "Resume Defense";
    if (type.includes("system") || type.includes("architecture")) return "System Design";
    if (type.includes("behavioral") || type.includes("star")) return "Behavioral";
    return "Technical Depth";
  })();

  return (
    <div className="container" style={{ maxWidth: "1120px", paddingBottom: "40px" }}>
      {/* Non-blocking Fullscreen Ended Notice (Part 6 & 7) */}
      {showFullscreenNotice && !isFullscreenActive && interviewStarted && !isSubmitted && (
        <div
          style={{
            backgroundColor: "rgba(30, 41, 59, 0.95)",
            border: "1px solid var(--border-default)",
            borderRadius: "8px",
            padding: "10px 16px",
            marginBottom: "16px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "12px",
            fontSize: "13px",
            color: "#f8fafc",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span>ℹ️</span>
            <span>Fullscreen ended. Your interview is still active.</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Button size="sm" variant="secondary" onClick={requestInterviewFullscreen}>
              Return to Fullscreen
            </Button>
            <button
              type="button"
              onClick={() => setShowFullscreenNotice(false)}
              style={{
                background: "none",
                border: "none",
                color: "#94a3b8",
                cursor: "pointer",
                fontSize: "18px",
                lineHeight: 1,
                padding: "0 4px",
              }}
              title="Dismiss"
            >
              ×
            </button>
          </div>
        </div>
      )}

      {/* Top Header */}
      {!interviewStarted ? (
        <div
          style={{
            paddingBottom: "16px",
            borderBottom: "1px solid var(--border-default)",
            marginBottom: "20px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
            <Badge variant="info">Interview Readiness Verification</Badge>
            <Badge variant="neutral">{questionMode === "FIXED" ? "Standard" : "Adaptive"}</Badge>
          </div>
          <h1
            style={{
              fontSize: "24px",
              fontWeight: "800",
              color: "var(--text-primary)",
              marginTop: "4px",
              letterSpacing: "-0.02em",
            }}
          >
            Interview Environment & Device Check
          </h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "13px", marginTop: "4px" }}>
            Verify your live camera feed, microphone access, and enter fullscreen mode before starting your session.
          </p>
        </div>
      ) : (
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "12px",
            paddingBottom: "16px",
            borderBottom: "1px solid var(--border-default)",
            marginBottom: "20px",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
              <span style={{ fontSize: "16px", fontWeight: "700", color: "var(--text-primary)" }}>
                {targetRole} {currentMode === "behavioral" ? "Behavioral Interview" : "Technical Interview"}
              </span>
              <Badge variant="neutral">{questionMode === "FIXED" ? "Standard" : "Adaptive"}</Badge>
              <Badge variant="info">
                Conversation: {conversationHistory.length} {conversationHistory.length === 1 ? "turn" : "turns"}
              </Badge>
              {currentMode === "pressure" && <Badge variant="warning">Pressure Incident (45s)</Badge>}
            </div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
              {isPracticeDrill ? "Targeted Practice Session" : "Comprehensive Performance Assessment"} • Evidence-gated evaluation
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            {currentMode === "pressure" && (
              <button
                type="button"
                onClick={handleSwitchToStandard}
                style={{
                  fontSize: "12px",
                  color: "var(--text-secondary)",
                  background: "none",
                  border: "1px solid var(--border-default)",
                  borderRadius: "4px",
                  padding: "4px 8px",
                  cursor: "pointer",
                }}
              >
                Switch to Standard (90s)
              </button>
            )}

            {/* Focused Timer */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "6px 14px",
                borderRadius: "var(--radius-md)",
                backgroundColor: isTimeLow ? "var(--danger-bg)" : "var(--bg-subtle, var(--slate-100))",
                border: `1px solid ${isTimeLow ? "var(--danger-border)" : "var(--border-default)"}`,
                color: isTimeLow ? "var(--danger-text)" : "var(--text-primary)",
                fontWeight: "700",
                fontSize: "15px",
                fontFamily: "var(--font-family-mono)",
              }}
            >
              <span>⏱</span>
              <span>{timeFormatted}</span>
            </div>

            <Button
              size="sm"
              variant="secondary"
              onClick={() => setShowEndConfirm(true)}
              style={{ color: "var(--danger-text, #ef4444)" }}
            >
              End Interview
            </Button>
          </div>
        </div>
      )}

      {speechNotice && (
        <div className="alert alert-info" style={{ marginBottom: "16px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span>{speechNotice}</span>
          <button
            type="button"
            onClick={() => setSpeechNotice("")}
            style={{ background: "none", border: "none", cursor: "pointer", fontWeight: "bold" }}
          >
            ✕
          </button>
        </div>
      )}

      {submitError && (
        <div className="alert alert-warning" style={{ marginBottom: "16px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span>{submitError}</span>
          <Button size="sm" variant="secondary" onClick={handleSubmitAnswer}>
            Retry Submission
          </Button>
        </div>
      )}

      {finalizationError && (
        <div className="alert alert-warning" style={{ marginBottom: "16px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span>{finalizationError}</span>
          <Button size="sm" variant="primary" onClick={handleFinishInterview} loading={submittingFinal}>
            Retry Finalization
          </Button>
        </div>
      )}

      {/* 2-Column Conversational Grid:
          Left: Pre-Flight Check OR Chat Conversation Thread + Prompt + Input
          Right: Camera Video Stream + Telemetry (Always mounted, zero black screen)
      */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 1.45fr) minmax(310px, 0.95fr)",
          gap: "20px",
          alignItems: "start",
        }}
      >
        {/* Left Column */}
        {!interviewStarted ? (
          <Card style={{ padding: "32px", border: "1px solid var(--border-default)" }}>
            <div style={{ marginBottom: "24px" }}>
              <Badge variant="info">Interview Readiness Verification</Badge>
              <h2 style={{ fontSize: "20px", fontWeight: "800", color: "var(--text-primary)", marginTop: "8px", letterSpacing: "-0.02em" }}>
                Device & Proctoring Checklist
              </h2>
              <p style={{ color: "var(--text-secondary)", fontSize: "13px", marginTop: "4px" }}>
                Verify device access and enter fullscreen mode before starting your session.
              </p>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginBottom: "32px" }}>
              {/* Camera Status */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "16px 20px",
                  borderRadius: "8px",
                  border: "1px solid var(--border-default)",
                  backgroundColor: "var(--bg-app)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
                  <div style={{ fontSize: "28px" }}>📷</div>
                  <div>
                    <div style={{ fontWeight: "700", color: "var(--text-primary)", fontSize: "15px" }}>
                      Camera Status
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "2px" }}>
                      {textOnly
                        ? "Privacy mode enabled (camera disabled)"
                        : cameraState === CAMERA_STATES.READY
                        ? "Camera verified & live face tracking active"
                        : cameraState === CAMERA_STATES.ERROR
                        ? "Camera permission is required for visual analysis."
                        : cameraNotice || "Initializing camera..."}
                    </div>
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  {!textOnly && cameraState === CAMERA_STATES.ERROR && (
                    <Button size="sm" variant="secondary" onClick={retryCameraPermission}>
                      Retry Camera
                    </Button>
                  )}
                  <Badge
                    variant={
                      textOnly || cameraState === CAMERA_STATES.READY
                        ? "success"
                        : cameraState === CAMERA_STATES.ERROR
                        ? "danger"
                        : "warning"
                    }
                  >
                    {textOnly
                      ? "OPTIONAL"
                      : cameraState === CAMERA_STATES.READY
                      ? "READY"
                      : cameraState === CAMERA_STATES.ERROR
                      ? "BLOCKED"
                      : "INITIALIZING"}
                  </Badge>
                </div>
              </div>

              {/* Microphone Status */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "16px 20px",
                  borderRadius: "8px",
                  border: "1px solid var(--border-default)",
                  backgroundColor: "var(--bg-app)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
                  <div style={{ fontSize: "28px" }}>🎙️</div>
                  <div>
                    <div style={{ fontWeight: "700", color: "var(--text-primary)", fontSize: "15px" }}>
                      Microphone Status
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "2px" }}>
                      {textOnly
                        ? "Privacy mode enabled (mic disabled)"
                        : micCheckState === "READY"
                        ? "Audio capture authorized"
                        : "Microphone permission required"}
                    </div>
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  {!textOnly && micCheckState !== "READY" && (
                    <Button size="sm" variant="secondary" onClick={testMicrophonePermission}>
                      Test Mic
                    </Button>
                  )}
                  <Badge
                    variant={
                      textOnly || micCheckState === "READY"
                        ? "success"
                        : micCheckState === "BLOCKED"
                        ? "danger"
                        : "warning"
                    }
                  >
                    {textOnly
                      ? "OPTIONAL"
                      : micCheckState === "READY"
                      ? "READY"
                      : micCheckState === "BLOCKED"
                      ? "BLOCKED"
                      : "CHECK REQUIRED"}
                  </Badge>
                </div>
              </div>

              {/* Fullscreen Mode */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "16px 20px",
                  borderRadius: "8px",
                  border: "1px solid var(--border-default)",
                  backgroundColor: "var(--bg-app)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
                  <div style={{ fontSize: "28px" }}>🖥️</div>
                  <div>
                    <div style={{ fontWeight: "700", color: "var(--text-primary)", fontSize: "15px" }}>
                      Controlled Fullscreen Mode
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "2px" }}>
                      Required for focused interview evaluation and proctoring
                    </div>
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  {!isFullscreenActive && (
                    <Button size="sm" variant="secondary" onClick={requestInterviewFullscreen}>
                      Enable Fullscreen
                    </Button>
                  )}
                  <Badge variant={isFullscreenActive ? "success" : "warning"}>
                    {isFullscreenActive ? "READY" : "NOT ACTIVE"}
                  </Badge>
                </div>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid var(--border-default)", paddingTop: "20px" }}>
              <Link to="/dashboard" style={{ textDecoration: "none" }}>
                <Button variant="secondary" size="md">
                  Cancel & Return
                </Button>
              </Link>
              <Button
                variant="primary"
                size="lg"
                onClick={startInterviewSession}
                disabled={
                  !textOnly &&
                  (cameraState === CAMERA_STATES.ERROR || micCheckState === "BLOCKED")
                }
              >
                Begin Interview Session →
              </Button>
            </div>
          </Card>
        ) : (
          /* Left Column: Conversational Stream & Input */
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {/* Conversation History Stream */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "14px",
              maxHeight: "360px",
              overflowY: "auto",
              paddingRight: "6px",
            }}
          >
            {conversationHistory.length === 0 ? (
              <div
                style={{
                  padding: "16px 20px",
                  borderRadius: "8px",
                  backgroundColor: "var(--bg-subtle)",
                  border: "1px dashed var(--border-default)",
                  fontSize: "13px",
                  color: "var(--text-muted)",
                  textAlign: "center",
                }}
              >
                Welcome to your interactive interview session. Speak or type your answers below. Each response will build your conversation record.
              </div>
            ) : (
              conversationHistory.map((turn, tIdx) => (
                <div key={turn.id || tIdx} style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {/* Interviewer Bubble */}
                  <div
                    style={{
                      backgroundColor: "var(--bg-surface)",
                      border: "1px solid var(--border-default)",
                      borderRadius: "10px",
                      padding: "14px 18px",
                      boxShadow: "var(--shadow-xs)",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ fontSize: "11px", fontWeight: "800", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--primary-600)" }}>
                          INTERVIEWER
                        </span>
                        <Badge variant="neutral">{turn.caption || "Interview Question"}</Badge>
                      </div>
                      <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>{turn.timestamp}</span>
                    </div>
                    <div style={{ fontSize: "15px", fontWeight: "600", color: "var(--text-primary)", lineHeight: "1.45" }}>
                      "{turn.question}"
                    </div>
                  </div>

                  {/* Candidate Bubble */}
                  <div
                    style={{
                      alignSelf: "flex-end",
                      maxWidth: "92%",
                      backgroundColor: turn.isSkipped ? "var(--bg-subtle)" : "var(--primary-50)",
                      border: `1px solid ${turn.isSkipped ? "var(--border-default)" : "var(--primary-200)"}`,
                      borderRadius: "10px",
                      padding: "12px 16px",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
                      <span style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", color: "var(--text-secondary)" }}>
                        YOU
                      </span>
                      {turn.isSkipped && <Badge variant="warning">Skipped</Badge>}
                    </div>
                    <div
                      style={{
                        fontSize: "14px",
                        color: turn.isSkipped ? "var(--text-muted)" : "var(--text-primary)",
                        fontStyle: turn.isSkipped ? "italic" : "normal",
                        lineHeight: "1.5",
                        whiteSpace: "pre-wrap",
                      }}
                    >
                      {turn.answer}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Active Interviewer Prompt Card */}
          <Card
            style={{
              padding: "18px 22px",
              border: "1px solid var(--border-focus)",
              backgroundColor: "var(--bg-surface)",
              boxShadow: "var(--shadow-sm)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span
                  style={{
                    width: "8px",
                    height: "8px",
                    borderRadius: "50%",
                    backgroundColor: "var(--primary-600)",
                    display: "inline-block",
                  }}
                />
                <span style={{ fontSize: "12px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--primary-600)" }}>
                  Interviewer
                </span>
                <Badge variant="info">{currentQ.caption || categoryLabel}</Badge>
              </div>
              <Badge variant="neutral">Difficulty: {difficulty}</Badge>
            </div>

            <h2 style={{ fontSize: "18px", fontWeight: "700", color: "var(--text-primary)", lineHeight: "1.4", margin: "4px 0 0" }}>
              {isFollowUp ? followUpQuestion : currentQ.question}
            </h2>
          </Card>

          {/* Unified Answer Input Area */}
          <Card style={{ padding: "18px 20px" }}>
            {/* Input Mode Selector Tabs */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
              <div style={{ display: "flex", gap: "6px", backgroundColor: "var(--bg-subtle)", padding: "3px", borderRadius: "6px" }}>
                <button
                  type="button"
                  onClick={() => {
                    setInputMode("mic");
                    if (!isListening) {
                      startListening();
                    }
                  }}
                  style={{
                    padding: "5px 14px",
                    borderRadius: "4px",
                    fontSize: "12px",
                    fontWeight: "600",
                    border: "none",
                    cursor: "pointer",
                    backgroundColor: inputMode === "mic" ? "var(--slate-900)" : "transparent",
                    color: inputMode === "mic" ? "#ffffff" : "var(--text-secondary)",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  <span>🎙</span>
                  <span>Speak Answer</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setInputMode("text");
                    if (isListening) {
                      try { stopListening(); } catch {}
                    }
                  }}
                  style={{
                    padding: "5px 14px",
                    borderRadius: "4px",
                    fontSize: "12px",
                    fontWeight: "600",
                    border: "none",
                    cursor: "pointer",
                    backgroundColor: inputMode === "text" ? "var(--slate-900)" : "transparent",
                    color: inputMode === "text" ? "#ffffff" : "var(--text-secondary)",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  <span>⌨</span>
                  <span>Type Answer</span>
                </button>
              </div>

              <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                {wordCount} {wordCount === 1 ? "word" : "words"}
              </div>
            </div>

            {/* Speech Active Feedback Banner (Recording) */}
            {isRecording && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "8px 12px",
                  borderRadius: "var(--radius-md)",
                  backgroundColor: "var(--danger-bg, #fef2f2)",
                  border: "1px solid var(--danger-border, #fca5a5)",
                  color: "var(--danger-text, #b91c1c)",
                  fontSize: "12px",
                  fontWeight: "600",
                  marginBottom: "10px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span
                    style={{
                      width: "8px",
                      height: "8px",
                      borderRadius: "50%",
                      backgroundColor: "var(--danger-text, #ef4444)",
                      animation: "pulse 1.2s infinite",
                    }}
                  />
                  <span>
                    Recording... {formattedTime} {audioLevel > 0.02 ? `(Mic input: ${Math.round(audioLevel * 100)}%)` : ""}
                  </span>
                  {livePreviewText && (
                    <span
                      style={{
                        fontSize: "11px",
                        color: "#6b7280",
                        fontStyle: "italic",
                        maxWidth: "240px",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      preview: "{livePreviewText}"
                    </span>
                  )}
                </div>
                <button
                  type="button"
                  onClick={stopListening}
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--danger-text, #b91c1c)",
                    fontWeight: "700",
                    cursor: "pointer",
                    fontSize: "11px",
                  }}
                >
                  ● Stop Speaking
                </button>
              </div>
            )}

            {/* Speech Transcribing Banner */}
            {isTranscribing && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  padding: "8px 12px",
                  borderRadius: "var(--radius-md)",
                  backgroundColor: "#eff6ff",
                  border: "1px solid #bfdbfe",
                  color: "#1d4ed8",
                  fontSize: "12px",
                  fontWeight: "600",
                  marginBottom: "10px",
                }}
              >
                <span style={{ animation: "spin 1s linear infinite", display: "inline-block" }}>⟳</span>
                <span>Transcribing your answer with Gemini 3.5... Your audio is being processed securely.</span>
              </div>
            )}

            {/* Speech Completed Notice */}
            {speechState === SPEECH_STATES.TRANSCRIPTION_COMPLETE && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "6px 12px",
                  borderRadius: "var(--radius-md)",
                  backgroundColor: "#f0fdf4",
                  border: "1px solid #bbf7d0",
                  color: "#15803d",
                  fontSize: "12px",
                  fontWeight: "600",
                  marginBottom: "10px",
                }}
              >
                <span>✓ Transcript ready. You can edit your answer below before sending.</span>
                <button
                  type="button"
                  onClick={startListening}
                  style={{
                    background: "none",
                    border: "none",
                    color: "#15803d",
                    fontSize: "11px",
                    fontWeight: "700",
                    cursor: "pointer",
                    textDecoration: "underline",
                  }}
                >
                  Record more +
                </button>
              </div>
            )}

            {/* Speech Error Banner with Retry */}
            {speechState === SPEECH_STATES.ERROR && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "8px 12px",
                  borderRadius: "var(--radius-md)",
                  backgroundColor: "#fff7ed",
                  border: "1px solid #fed7aa",
                  color: "#c2410c",
                  fontSize: "12px",
                  fontWeight: "600",
                  marginBottom: "10px",
                }}
              >
                <span>{speechNotice || "Transcription failed. Your recording was not lost."}</span>
                <div style={{ display: "flex", gap: "6px" }}>
                  {retryTranscription && (
                    <button
                      type="button"
                      onClick={retryTranscription}
                      style={{
                        padding: "3px 8px",
                        borderRadius: "4px",
                        border: "1px solid #ea580c",
                        backgroundColor: "#ffffff",
                        color: "#ea580c",
                        fontSize: "11px",
                        fontWeight: "700",
                        cursor: "pointer",
                      }}
                    >
                      Retry Transcription ↻
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => setInputMode("text")}
                    style={{
                      padding: "3px 8px",
                      borderRadius: "4px",
                      border: "1px solid #cbd5e1",
                      backgroundColor: "#ffffff",
                      color: "#475569",
                      fontSize: "11px",
                      fontWeight: "600",
                      cursor: "pointer",
                    }}
                  >
                    Type Manually
                  </button>
                </div>
              </div>
            )}

            {/* Textarea Input (Live Speech Appending + Typing) */}
            <textarea
              value={answer}
              disabled={isSubmitted}
              onChange={(e) => {
                setAnswer(e.target.value);
                notifyManualTextChange(e.target.value);
              }}
              placeholder={
                inputMode === "mic"
                  ? "Click [Start Speaking] or begin typing your structured answer here..."
                  : "Type your structured technical answer here..."
              }
              rows={7}
              className="form-textarea"
              style={{
                width: "100%",
                padding: "12px",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-default)",
                backgroundColor: "var(--bg-app)",
                color: "var(--text-primary)",
                fontFamily: "var(--font-family-sans)",
                fontSize: "14px",
                lineHeight: "1.6",
                resize: "vertical",
                marginBottom: "12px",
              }}
            />

            {/* Optional Diagnostic Speech Debug Panel (?debugSpeech=1) */}
            {showDebugSpeech && (
              <div
                id="speech-debug-panel"
                style={{
                  marginBottom: "12px",
                  padding: "10px 14px",
                  backgroundColor: "#0f172a",
                  color: "#f8fafc",
                  borderRadius: "6px",
                  fontSize: "11px",
                  fontFamily: "monospace",
                  lineHeight: "1.5",
                  border: "1px solid #334155",
                }}
              >
                <div style={{ fontWeight: "700", color: "#38bdf8", marginBottom: "4px" }}>
                  [Speech Diagnostic Inspector]
                </div>
                <div>Microphone: {debugInfo.micStatus} | Audio RMS: {(audioLevel * 100).toFixed(1)}%</div>
                <div>Engine: {activeEngine} | State: {speechState} | Connection: {debugInfo.connection}</div>
                <div>Last Event: {debugInfo.lastTranscriptEvent || "none"}</div>
                <div>Authoritative Answer ({wordCount} words): "{answer.slice(0, 100)}{answer.length > 100 ? "..." : ""}"</div>
                {debugInfo.error && <div style={{ color: "#ef4444" }}>Error: {debugInfo.error}</div>}
              </div>
            )}

            {/* Bottom Actions: Mic trigger, Skip, and Send */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                {speechSupported && (
                  <Button
                    size="sm"
                    variant={isListening ? "danger" : "secondary"}
                    onClick={toggleSpeechRecognition}
                    disabled={evaluating || loadingNext || submittingFinal}
                  >
                    {isListening ? "● Stop Speaking" : "🎤 Start Speaking"}
                  </Button>
                )}
                {isTimeLow && (
                  <span style={{ fontSize: "11px", color: "var(--danger-text)", fontWeight: "600" }}>
                    Time running low
                  </span>
                )}
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Button
                  size="md"
                  variant="subtle"
                  onClick={handleSkipQuestion}
                  disabled={evaluating || loadingNext || submittingFinal}
                >
                  {loadingNext ? "Skipping..." : "Skip / I Don't Know"}
                </Button>
                <Button
                  size="md"
                  variant="primary"
                  onClick={handleSubmitAnswer}
                  loading={evaluating}
                  disabled={loadingNext || submittingFinal}
                >
                  Send Answer →
                </Button>
              </div>
            </div>
            <div ref={chatBottomRef} />
          </Card>
        </div>
      )}

        {/* Right Column: Candidate Camera Feed & Telemetry (Mounted permanently across pre-flight & interview) */}
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <Card style={{ padding: "16px" }}>
            <div
              style={{
                position: "relative",
                aspectRatio: "4/3",
                backgroundColor: "var(--slate-900)",
                borderRadius: "var(--radius-md)",
                overflow: "hidden",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                border:
                  cameraState === CAMERA_STATES.READY && isCameraOn && !textOnly
                    ? personCountStatus.state === FACE_STATES.NO_FACE
                      ? "3px solid #ef4444"
                      : personCountStatus.state === FACE_STATES.MULTIPLE_FACES
                      ? "3px solid #ef4444"
                      : personCountStatus.state === FACE_STATES.ONE_FACE
                      ? "2px solid #10b981"
                      : "1px solid var(--border-color)"
                    : "1px solid var(--border-color)",
                boxShadow:
                  cameraState === CAMERA_STATES.READY && isCameraOn && !textOnly && (personCountStatus.state === FACE_STATES.NO_FACE || personCountStatus.state === FACE_STATES.MULTIPLE_FACES)
                    ? "0 0 12px rgba(239, 68, 68, 0.4)"
                    : "none",
                transition: "border 0.2s ease, box-shadow 0.2s ease",
              }}
            >
              {/* Single Video element always mounted in DOM so srcObject binding and frame sampling succeed */}
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                style={{
                  width: "100%",
                  height: "100%",
                  objectFit: "cover",
                  transform: "scaleX(-1)", // Mirror camera feed naturally
                  display: cameraState === CAMERA_STATES.READY && isCameraOn && !textOnly ? "block" : "none",
                }}
              />
              {/* Active overlay canvas for tracked face bounding boxes */}
              <canvas
                ref={canvasRef}
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  width: "100%",
                  height: "100%",
                  pointerEvents: "none",
                  display: cameraState === CAMERA_STATES.READY && isCameraOn && !textOnly ? "block" : "none",
                }}
              />

              {/* Multi-Person Live Warning (Section 13 & 14) */}
              {cameraState === CAMERA_STATES.READY && isCameraOn && !textOnly && personCountStatus.state === FACE_STATES.MULTIPLE_FACES && (
                <div
                  style={{
                    position: "absolute",
                    top: "12px",
                    left: "12px",
                    right: "12px",
                    backgroundColor: "rgba(220, 38, 38, 0.95)",
                    color: "#ffffff",
                    padding: "8px 12px",
                    borderRadius: "6px",
                    fontSize: "12px",
                    fontWeight: "700",
                    textAlign: "center",
                    zIndex: 10,
                    boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
                  }}
                >
                  ⚠️ MULTIPLE PEOPLE DETECTED — Only one person should be visible.
                </div>
              )}

              {/* No-Face Live Warning (Section 14) */}
              {cameraState === CAMERA_STATES.READY && isCameraOn && !textOnly && personCountStatus.state === FACE_STATES.NO_FACE && (
                <div
                  style={{
                    position: "absolute",
                    top: "12px",
                    left: "12px",
                    right: "12px",
                    backgroundColor: "rgba(220, 38, 38, 0.95)",
                    color: "#ffffff",
                    padding: "8px 12px",
                    borderRadius: "6px",
                    fontSize: "12px",
                    fontWeight: "700",
                    textAlign: "center",
                    zIndex: 10,
                    boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
                  }}
                >
                  ⚠️ NO FACE DETECTED — Keep your face visible in the camera.
                </div>
              )}

              {/* Camera Alignment Guidance (Section 18) */}
              {cameraState === CAMERA_STATES.READY && isCameraOn && !textOnly && personCountStatus.state === FACE_STATES.ONE_FACE && cameraAlignment && cameraAlignment.status !== ALIGNMENT_STATES.GOOD && (
                <div
                  style={{
                    position: "absolute",
                    top: "12px",
                    left: "12px",
                    right: "12px",
                    backgroundColor: "rgba(15, 23, 42, 0.85)",
                    color: "#93c5fd",
                    padding: "6px 10px",
                    borderRadius: "6px",
                    fontSize: "11px",
                    fontWeight: "600",
                    textAlign: "center",
                    zIndex: 10,
                    border: "1px solid rgba(147, 197, 253, 0.3)",
                  }}
                >
                  ℹ️ {cameraAlignment.message}
                </div>
              )}

              {/* Fallback placeholder when camera is not ready or text-only */}
              {(cameraState !== CAMERA_STATES.READY || !isCameraOn || textOnly) && (
                <div style={{ textAlign: "center", padding: "24px 16px", color: "var(--slate-400)" }}>
                  <div style={{ fontSize: "36px", marginBottom: "8px" }}>
                    {cameraState === CAMERA_STATES.ERROR ? "🚫" : textOnly ? "🔒" : "📷"}
                  </div>
                  <div style={{ fontSize: "14px", fontWeight: "600", color: "#f8fafc" }}>
                    {textOnly
                      ? "Privacy Mode Active"
                      : cameraState === CAMERA_STATES.ERROR
                      ? "Camera Unavailable"
                      : cameraState === CAMERA_STATES.REQUESTING
                      ? "Connecting to Camera..."
                      : cameraState === CAMERA_STATES.STOPPED
                      ? "Camera Turned Off"
                      : "Initializing Camera..."}
                  </div>
                  <div style={{ fontSize: "12px", marginTop: "4px", lineHeight: "1.4" }}>
                    {textOnly
                      ? "Local video processing is disabled."
                      : cameraNotice || (cameraState === CAMERA_STATES.ERROR
                        ? "Camera permission is required for visual analysis."
                        : "Connecting to local video device for presentation analysis...")}
                  </div>
                  {cameraState === CAMERA_STATES.ERROR && !textOnly && (
                    <div style={{ marginTop: "14px" }}>
                      <Button size="sm" variant="secondary" onClick={retryCameraPermission}>
                        Retry Camera Access
                      </Button>
                    </div>
                  )}
                </div>
              )}

              {/* Authoritative Camera Status Pill (Section 8, 11, 14) */}
              <div
                style={{
                  position: "absolute",
                  bottom: "10px",
                  left: "10px",
                  backgroundColor: "rgba(15, 23, 42, 0.88)",
                  padding: "4px 9px",
                  borderRadius: "5px",
                  fontSize: "11px",
                  color: "#ffffff",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  zIndex: 10,
                  boxShadow: "0 1px 4px rgba(0,0,0,0.4)",
                }}
              >
                <span
                  style={{
                    width: "7px",
                    height: "7px",
                    borderRadius: "50%",
                    backgroundColor:
                      cameraState === CAMERA_STATES.READY && isCameraOn && !textOnly
                        ? personCountStatus.state === FACE_STATES.MULTIPLE_FACES
                          ? "#ef4444"
                          : personCountStatus.state === FACE_STATES.ONE_FACE
                          ? "#22c55e"
                          : personCountStatus.state === FACE_STATES.NO_FACE
                          ? "#ef4444"
                          : personCountStatus.state === FACE_STATES.ANALYSIS_ERROR
                          ? "#ef4444"
                          : "#f59e0b"
                        : cameraState === CAMERA_STATES.ERROR
                        ? "#ef4444"
                        : textOnly
                        ? "#94a3b8"
                        : "#f59e0b",
                  }}
                />
                <span style={{ fontWeight: 500 }}>
                  {cameraState === CAMERA_STATES.READY && isCameraOn && !textOnly
                    ? personCountStatus.state === FACE_STATES.MULTIPLE_FACES
                      ? "Multiple people detected"
                      : personCountStatus.state === FACE_STATES.ONE_FACE
                      ? "Face detected (1 person)"
                      : personCountStatus.state === FACE_STATES.NO_FACE
                      ? "No face detected"
                      : personCountStatus.state === FACE_STATES.ANALYSIS_ERROR
                      ? "Vision analysis error"
                      : modelState === "MODEL_LOADING"
                      ? "Loading face model..."
                      : "Camera analyzing..."
                    : cameraState === CAMERA_STATES.ERROR
                    ? "Camera blocked / unavailable"
                    : cameraState === CAMERA_STATES.REQUESTING
                    ? "Requesting camera..."
                    : cameraState === CAMERA_STATES.STOPPED
                    ? "Camera off"
                    : textOnly
                    ? "Camera off (privacy)"
                    : "Camera initializing..."}
                </span>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "12px", fontSize: "12px", color: "var(--text-muted)" }}>
              <span>Local browser analysis only.</span>
              {!textOnly && (
                <button
                  type="button"
                  onClick={toggleCamera}
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--primary-600)",
                    cursor: "pointer",
                    fontSize: "11px",
                    fontWeight: "600",
                  }}
                >
                  {cameraState === CAMERA_STATES.READY && isCameraOn ? "Turn Camera Off" : "Turn Camera On"}
                </button>
              )}
            </div>
          </Card>

          {/* Session Overview Card */}
          <Card style={{ padding: "16px" }}>
            <div style={{ fontSize: "12px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-muted)", marginBottom: "10px" }}>
              Session Information
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "13px" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-secondary)" }}>Role:</span>
                <span style={{ fontWeight: "600", color: "var(--text-primary)" }}>{targetRole}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-secondary)" }}>Mode:</span>
                <span style={{ fontWeight: "600", color: "var(--text-primary)" }}>{currentMode.toUpperCase()}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-secondary)" }}>Turns Logged:</span>
                <span style={{ fontWeight: "600", color: "var(--text-primary)" }}>
                  {conversationHistory.length} {conversationHistory.length === 1 ? "turn" : "turns"}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-secondary)" }}>Eye Contact:</span>
                <span style={{ fontWeight: "600", color: "var(--text-primary)" }}>
                  {cameraState !== CAMERA_STATES.READY || !isCameraOn
                    ? "Not available"
                    : eyeContactPercent !== null
                    ? `${eyeContactPercent}%`
                    : "Calculating..."}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-secondary)" }}>Visual Coverage:</span>
                <span style={{ fontWeight: "600", color: "var(--text-primary)" }}>
                  {cameraState !== CAMERA_STATES.READY || !isCameraOn
                    ? "Not available"
                    : visualCoverage !== null
                    ? `${visualCoverage}%`
                    : "Calculating..."}
                </span>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Browser Back Navigation Confirmation Modal (Part 3) */}
      {showBackConfirm && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(15, 23, 42, 0.75)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1100,
            padding: "16px",
          }}
        >
          <Card style={{ maxWidth: "440px", width: "100%", padding: "24px", boxShadow: "var(--shadow-xl)" }}>
            <h3 style={{ fontSize: "18px", fontWeight: "700", color: "var(--text-primary)", marginBottom: "8px" }}>
              You're still in an active interview.
            </h3>
            <p style={{ fontSize: "14px", color: "var(--text-secondary)", marginBottom: "20px", lineHeight: "1.5" }}>
              Leaving now will interrupt your interview session.
            </p>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
              <Button
                variant="secondary"
                onClick={() => setShowBackConfirm(false)}
                disabled={submittingFinal}
              >
                Stay in Interview
              </Button>
              <Button
                variant="primary"
                onClick={async () => {
                  setShowBackConfirm(false);
                  await handleFinishInterview();
                }}
                loading={submittingFinal}
              >
                End Interview
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* End Interview Confirmation Modal (Part 11) */}
      {showEndConfirm && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(15, 23, 42, 0.65)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "16px",
          }}
        >
          <Card style={{ maxWidth: "440px", width: "100%", padding: "24px", boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.2)" }}>
            <h3 style={{ fontSize: "18px", fontWeight: "700", color: "var(--text-primary)", marginBottom: "8px" }}>
              End interview?
            </h3>
            <p style={{ fontSize: "14px", color: "var(--text-secondary)", marginBottom: "20px", lineHeight: "1.5" }}>
              Your completed answers and performance data from this session will be saved.
            </p>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
              <Button
                variant="secondary"
                onClick={() => setShowEndConfirm(false)}
                disabled={submittingFinal}
              >
                Continue Interview
              </Button>
              <Button
                variant="primary"
                onClick={async () => {
                  setShowEndConfirm(false);
                  await handleFinishInterview();
                }}
                loading={submittingFinal}
              >
                End Interview
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

export default Interview;