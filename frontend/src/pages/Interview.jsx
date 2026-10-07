import React, { useState, useEffect, useRef, useContext } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { FaceMesh } from "@mediapipe/face_mesh";
import { Camera } from "@mediapipe/camera_utils";
import { ReportContext } from "../context/ReportContext";
import { apiFetch } from "../utils/api";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";

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

  // Camera & sensor states (INITIALIZING | ACTIVE | OFF | DENIED | UNAVAILABLE)
  const [cameraState, setCameraState] = useState(textOnly ? "OFF" : "INITIALIZING");
  const [cameraNotice, setCameraNotice] = useState("");
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [isMicOn, setIsMicOn] = useState(false);
  const [eyeContactPercent, setEyeContactPercent] = useState(null);
  const [blinkCount, setBlinkCount] = useState(0);

  // Speech-to-text recognition state machine: idle | starting | listening | processing | stopped | error | unsupported
  const [speechState, setSpeechState] = useState("idle");
  const [speechSupported, setSpeechSupported] = useState(!textOnly);
  const [inputMode, setInputMode] = useState(textOnly ? "text" : "mic"); // mic | text
  const [speechNotice, setSpeechNotice] = useState("");
  const [submitError, setSubmitError] = useState(null);

  const speechRecognizerRef = useRef(null);
  const speechSegmentsRef = useRef([]);
  const currentSpeechStartRef = useRef(null);
  const speechBaseTextRef = useRef("");
  const isListeningDesiredRef = useRef(false);
  const answerRef = useRef(answer);

  useEffect(() => {
    answerRef.current = answer;
  }, [answer]);

  // Question submission & progress state
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [loadingNext, setLoadingNext] = useState(false);
  const [submittingFinal, setSubmittingFinal] = useState(false);
  const [finalizationError, setFinalizationError] = useState(null);
  const [isFollowUp, setIsFollowUp] = useState(false);
  const [followUpQuestion, setFollowUpQuestion] = useState("");
  const [showEndConfirm, setShowEndConfirm] = useState(false);

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
  const streamRef = useRef(null);
  const cameraRef = useRef(null);
  const faceMeshRef = useRef(null);

  const currentQ = questions[currentIndex] || { id: 1, question: "Interview Question" };

  // Timer countdown
  useEffect(() => {
    if (timeLeft <= 0 || isSubmitted) return;
    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          // Stop speech cleanly when time expires
          isListeningDesiredRef.current = false;
          if (speechRecognizerRef.current && speechState === "listening") {
            try { speechRecognizerRef.current.stop(); } catch {}
          }
          setSpeechNotice("Time is up! You can review and submit your response.");
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [timeLeft, isSubmitted, speechState]);

  // Reset timer & state on question change
  useEffect(() => {
    const defaultTime = currentMode === "pressure" ? 45 : (currentQ.time_limit_seconds || 90);
    setTimeLeft(defaultTime);
    setAnswer("");
    setIsSubmitted(false);
    setSubmitError(null);
    setFinalizationError(null);
    questionStartTimeRef.current = Date.now();
    speechSegmentsRef.current = [];
    currentSpeechStartRef.current = null;
    speechBaseTextRef.current = "";
    isListeningDesiredRef.current = false;
    if (speechRecognizerRef.current) {
      try { speechRecognizerRef.current.stop(); } catch {}
    }
    setSpeechState("stopped");
    answerVisualFramesRef.current = {
      totalSampled: 0,
      faceDetected: 0,
      alignedCount: 0,
      blinks: 0,
      positions: [],
      lastPosition: null,
      shifts: 0,
    };
  }, [currentIndex, currentMode]);

  // Speech Recognition setup (Web Speech API)
  useEffect(() => {
    if (textOnly) {
      setSpeechSupported(false);
      setSpeechState("unsupported");
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSpeechSupported(false);
      setSpeechState("unsupported");
      setInputMode("text");
      setSpeechNotice("Live speech transcription is not supported in this browser. You can type your answers.");
      return;
    }

    const recognizer = new SpeechRecognition();
    recognizer.continuous = true;
    recognizer.interimResults = true;
    recognizer.lang = "en-US";

    recognizer.onstart = () => {
      setSpeechState("listening");
      setIsMicOn(true);
      currentSpeechStartRef.current = Date.now();
    };

    recognizer.onresult = (event) => {
      let finalTranscript = "";
      let interimTranscript = "";
      for (let i = 0; i < event.results.length; i++) {
        const textChunk = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += textChunk + " ";
        } else {
          interimTranscript += textChunk;
        }
      }
      const recognized = (finalTranscript + interimTranscript).trim();
      const base = speechBaseTextRef.current ? speechBaseTextRef.current.trim() : "";
      const combined = base ? `${base} ${recognized}` : recognized;
      setAnswer(combined.trim());
    };

    recognizer.onerror = (event) => {
      console.warn("Speech recognition notice:", event.error);
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        isListeningDesiredRef.current = false;
        setSpeechState("error");
        setSpeechNotice("Microphone permission denied. Switched to text mode.");
        setInputMode("text");
      } else if (event.error === "no-speech") {
        if (!isListeningDesiredRef.current) {
          setSpeechState("stopped");
        }
      } else {
        setSpeechState("error");
        setSpeechNotice(`Microphone notice: ${event.error}. You can also type your answer.`);
      }
    };

    recognizer.onend = () => {
      if (isListeningDesiredRef.current) {
        // Auto-resume recognition if user is still in listening mode
        speechBaseTextRef.current = answerRef.current ? answerRef.current.trim() : "";
        try {
          recognizer.start();
          return;
        } catch {
          // Ignore if already transitioning
        }
      }
      setSpeechState("stopped");
      setIsMicOn(false);
      if (currentSpeechStartRef.current) {
        const segStart = (currentSpeechStartRef.current - questionStartTimeRef.current) / 1000;
        const segEnd = (Date.now() - questionStartTimeRef.current) / 1000;
        if (segEnd > segStart) {
          speechSegmentsRef.current.push({
            start_seconds: Math.max(0, segStart),
            end_seconds: Math.max(segStart, segEnd),
          });
        }
        currentSpeechStartRef.current = null;
      }
    };

    speechRecognizerRef.current = recognizer;

    return () => {
      isListeningDesiredRef.current = false;
      try {
        recognizer.abort();
      } catch {
        // cleanup
      }
    };
  }, [textOnly]);

  const toggleSpeechRecognition = () => {
    if (!speechRecognizerRef.current) return;
    if (speechState === "listening") {
      isListeningDesiredRef.current = false;
      try {
        speechRecognizerRef.current.stop();
      } catch {}
      setSpeechState("stopped");
    } else {
      try {
        isListeningDesiredRef.current = true;
        speechBaseTextRef.current = answer.trim();
        setSpeechState("starting");
        speechRecognizerRef.current.start();
      } catch (e) {
        console.warn("Speech recognition start warning:", e);
        try {
          speechRecognizerRef.current.abort();
          setTimeout(() => {
            if (isListeningDesiredRef.current) {
              speechRecognizerRef.current.start();
            }
          }, 150);
        } catch {}
      }
    }
  };

  // Background MediaPipe FaceMesh & Camera Stream Setup
  useEffect(() => {
    if (textOnly) {
      setCameraState("OFF");
      return;
    }

    let isSubscribed = true;

    async function initCamera() {
      setCameraState("INITIALIZING");
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: 640, height: 480 },
          audio: false,
        });

        if (!isSubscribed) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }

        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          try {
            await videoRef.current.play();
          } catch {}

          const checkCameraDimensions = () => {
            if (!isSubscribed) return;
            if (videoRef.current && videoRef.current.videoWidth > 0 && videoRef.current.videoHeight > 0) {
              setIsCameraOn(true);
              setCameraState("ACTIVE");
            } else {
              setTimeout(checkCameraDimensions, 200);
            }
          };
          checkCameraDimensions();
        }

        const faceMesh = new FaceMesh({
          locateFile: (file) => `/mediapipe/face_mesh/${file}`,
        });

        faceMesh.setOptions({
          maxNumFaces: 1,
          refineLandmarks: true,
          minDetectionConfidence: 0.5,
          minTrackingConfidence: 0.5,
        });

        faceMesh.onResults((results) => {
          if (!isSubscribed) return;
          totalFramesRef.current += 1;
          const av = answerVisualFramesRef.current;
          av.totalSampled += 1;

          if (results.multiFaceLandmarks && results.multiFaceLandmarks.length > 0) {
            av.faceDetected += 1;
            const landmarks = results.multiFaceLandmarks[0];
            const nose = landmarks[1];
            const isAligned = Math.abs(nose.x - 0.5) < 0.15;

            if (isAligned) {
              eyeContactFramesRef.current += 1;
              av.alignedCount += 1;
            }

            const topEye = landmarks[159];
            const botEye = landmarks[145];
            const eyeDist = Math.abs(topEye.y - botEye.y);

            if (eyeDist < 0.015 && !blinkRef.current) {
              blinkRef.current = true;
              setBlinkCount((prev) => prev + 1);
              av.blinks += 1;
            } else if (eyeDist >= 0.015 && blinkRef.current) {
              blinkRef.current = false;
            }

            if (totalFramesRef.current % 30 === 0) {
              const currentPercent = (eyeContactFramesRef.current / totalFramesRef.current) * 100;
              setEyeContactPercent(Number(currentPercent.toFixed(1)));
            }
          }
        });

        faceMeshRef.current = faceMesh;

        if (videoRef.current) {
          const camera = new Camera(videoRef.current, {
            onFrame: async () => {
              if (faceMeshRef.current && videoRef.current) {
                await faceMeshRef.current.send({ image: videoRef.current });
              }
            },
            width: 640,
            height: 480,
          });
          camera.start();
          cameraRef.current = camera;
        }
      } catch (err) {
        console.warn("Camera could not be accessed:", err);
        if (isSubscribed) {
          setIsCameraOn(false);
          setCameraState("DENIED");
          setCameraNotice("Camera permission denied or device unavailable. Proceeding in text/mic mode.");
        }
      }
    }

    initCamera();

    return () => {
      isSubscribed = false;
      setIsCameraOn(false);
      setCameraState("OFF");
      if (cameraRef.current) {
        try { cameraRef.current.stop(); } catch {}
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
    };
  }, [textOnly]);

  const toggleCamera = () => {
    if (isCameraOn) {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => (track.enabled = false));
      }
      setIsCameraOn(false);
      setCameraState("OFF");
    } else {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => (track.enabled = true));
        setIsCameraOn(true);
        setCameraState("ACTIVE");
      }
    }
  };

  // Handle Answer Submission with instant feedback and auto-advance
  const handleSubmitAnswer = async () => {
    if (evaluating || loadingNext || submittingFinal) return;

    if (speechRecognizerRef.current && speechState === "listening") {
      try { speechRecognizerRef.current.stop(); } catch {}
      setSpeechState("stopped");
    }

    if (!answer.trim()) {
      setSpeechNotice("Please speak or type your answer before submitting.");
      return;
    }

    setEvaluating(true);
    setSubmitError(null);

    const isTyped = inputMode === "text";
    const responseDuration = (Date.now() - questionStartTimeRef.current) / 1000;
    const words = answer.trim().split(/\s+/).filter(Boolean).length;
    const liveWpm = responseDuration > 0 ? Number(((words / responseDuration) * 60).toFixed(1)) : 0;

    const av = answerVisualFramesRef.current;
    const visualPayload = isCameraOn && av.totalSampled > 0
      ? {
          head_alignment_percent: av.faceDetected > 0 ? Number(((av.alignedCount / av.faceDetected) * 100).toFixed(1)) : null,
          blink_rate: responseDuration > 0 ? Number((av.blinks / (responseDuration / 60)).toFixed(1)) : null,
          face_visibility_ratio: Number((av.faceDetected / av.totalSampled).toFixed(2)),
          frames_sampled: av.totalSampled,
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
        speech_segments: isTyped ? null : (speechSegmentsRef.current.length > 0 ? speechSegmentsRef.current : null),
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
          speechSegmentsRef.current = [];
          currentSpeechStartRef.current = null;
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
    }
  };

  // Handle Skip / I Don't Know
  const handleSkipQuestion = async () => {
    if (evaluating || loadingNext || submittingFinal) return;

    if (speechRecognizerRef.current && speechState === "listening") {
      try { speechRecognizerRef.current.stop(); } catch {}
      setSpeechState("stopped");
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
          speechSegmentsRef.current = [];
          currentSpeechStartRef.current = null;
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
    speechSegmentsRef.current = [];
    currentSpeechStartRef.current = null;
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
    setSubmittingFinal(true);
    setFinalizationError(null);

    try {
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

      navigate(`/report?sessionId=${sessionId}`);
    } catch (err) {
      console.error("Interview complete error:", err);
      setFinalizationError(`Finalization Error: ${err.message}. Please click 'Retry Finalization' to continue.`);
    } finally {
      setSubmittingFinal(false);
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
    <div className="container" style={{ maxWidth: "1020px", paddingBottom: "40px" }}>
      {/* Top Header Bar */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "12px",
          paddingBottom: "16px",
          borderBottom: "1px solid var(--border-default)",
          marginBottom: "24px",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "14px", fontWeight: "700", color: "var(--text-primary)" }}>
              {isPracticeDrill ? "Practice Drill" : "Interview Session"}
            </span>
            <Badge variant="neutral">{targetRole}</Badge>
            {currentMode === "pressure" && <Badge variant="warning">Incident Timing (45s)</Badge>}
          </div>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
            {(() => {
              if (questionMode === "FIXED") {
                return `Question ${currentIndex + 1} of ${totalQuestionBudget}`;
              }
              if (sessionPolicy === "FULL") {
                return `Question ${currentIndex + 1} • Continuous Adaptive`;
              }
              return `Question ${currentIndex + 1} • Adaptive Interview`;
            })()}
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
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

          {/* Clean Focused Timer */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "6px 14px",
              borderRadius: "var(--radius-md)",
              backgroundColor: isTimeLow ? "var(--danger-bg)" : "var(--slate-100)",
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
        </div>
      </div>

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

      {/* Prominent Question Card */}
      <Card style={{ marginBottom: "20px", padding: "20px 24px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
          <span style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--primary-700)" }}>
            {categoryLabel}
          </span>
          <Badge variant="info">Difficulty: {difficulty}</Badge>
        </div>

        <h2 style={{ fontSize: "20px", fontWeight: "700", color: "var(--text-primary)", lineHeight: "1.4" }}>
          {isFollowUp ? followUpQuestion : currentQ.question}
        </h2>
      </Card>

      {/* Workspace Grid (Desktop: 2 columns, Mobile: 1 column) */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: "20px",
          alignItems: "start",
        }}
      >
        {/* Left Column: Natural Candidate Camera Feed */}
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
            }}
          >
            {/* Video element always mounted in DOM so srcObject binding and frame sampling succeed */}
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
                display: isCameraOn && !textOnly ? "block" : "none",
              }}
            />
            {/* Hidden canvas for background MediaPipe processing */}
            <canvas ref={canvasRef} style={{ display: "none" }} />

            {(!isCameraOn || textOnly) && (
              <div style={{ textAlign: "center", padding: "20px", color: "var(--slate-400)" }}>
                <div style={{ fontSize: "36px", marginBottom: "8px" }}>📷</div>
                <div style={{ fontSize: "13px", fontWeight: "600", color: "#f8fafc" }}>
                  {textOnly ? "Privacy Mode Active" : (cameraNotice ? "Camera Unavailable" : "Initializing Camera...")}
                </div>
                <div style={{ fontSize: "11px", marginTop: "4px" }}>
                  {textOnly
                    ? "Local video processing is disabled."
                    : (cameraNotice || "Connecting to local video device for presentation analysis...")}
                </div>
              </div>
            )}

            {/* Camera Status Pill */}
            <div
              style={{
                position: "absolute",
                bottom: "10px",
                left: "10px",
                backgroundColor: "rgba(15, 23, 42, 0.85)",
                padding: "3px 8px",
                borderRadius: "4px",
                fontSize: "11px",
                color: "#ffffff",
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              <span
                style={{
                  width: "6px",
                  height: "6px",
                  borderRadius: "50%",
                  backgroundColor: isCameraOn && !textOnly ? "#22c55e" : (textOnly ? "#94a3b8" : "#f59e0b"),
                }}
              />
              <span>
                {isCameraOn && !textOnly
                  ? "Camera on"
                  : (textOnly ? "Camera off" : (cameraNotice ? "Camera unavailable" : "Camera initializing..."))}
              </span>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "12px", fontSize: "12px", color: "var(--text-muted)" }}>
            <span>Video frames stay strictly inside your browser.</span>
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
                {isCameraOn ? "Turn Camera Off" : "Turn Camera On"}
              </button>
            )}
          </div>
        </Card>

        {/* Right Column: Answer Input & Controls */}
        <Card style={{ padding: "20px" }}>
          {/* Input Mode Selector Tabs */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
            <div style={{ display: "flex", gap: "6px", backgroundColor: "var(--slate-100)", padding: "3px", borderRadius: "6px" }}>
              <button
                type="button"
                onClick={() => {
                  setInputMode("mic");
                  if (speechState === "stopped" || speechState === "idle") {
                    toggleSpeechRecognition();
                  }
                }}
                style={{
                  padding: "5px 12px",
                  borderRadius: "4px",
                  fontSize: "12px",
                  fontWeight: "600",
                  border: "none",
                  cursor: "pointer",
                  backgroundColor: inputMode === "mic" ? "var(--slate-900)" : "transparent",
                  color: inputMode === "mic" ? "#ffffff" : "var(--text-secondary)",
                }}
              >
                Speak Answer
              </button>
              <button
                type="button"
                onClick={() => {
                  setInputMode("text");
                  if (speechState === "listening" && speechRecognizerRef.current) {
                    try { speechRecognizerRef.current.stop(); } catch {}
                    setSpeechState("stopped");
                  }
                }}
                style={{
                  padding: "5px 12px",
                  borderRadius: "4px",
                  fontSize: "12px",
                  fontWeight: "600",
                  border: "none",
                  cursor: "pointer",
                  backgroundColor: inputMode === "text" ? "var(--slate-900)" : "transparent",
                  color: inputMode === "text" ? "#ffffff" : "var(--text-secondary)",
                }}
              >
                Type Answer
              </button>
            </div>

            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
              {wordCount} {wordCount === 1 ? "word" : "words"}
            </div>
          </div>

          {/* Speech Active Indicator Banner */}
          {speechState === "listening" && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "8px 12px",
                borderRadius: "var(--radius-md)",
                backgroundColor: "var(--danger-bg)",
                border: "1px solid var(--danger-border)",
                color: "var(--danger-text)",
                fontSize: "12px",
                fontWeight: "600",
                marginBottom: "10px",
              }}
            >
              <span
                style={{
                  width: "8px",
                  height: "8px",
                  borderRadius: "50%",
                  backgroundColor: "var(--danger-text)",
                }}
              />
              <span>Listening... speak your response clearly</span>
            </div>
          )}

          {/* Textarea Input (Live transcript or typing) */}
          <textarea
            value={answer}
            disabled={isSubmitted}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder={
              inputMode === "mic"
                ? "Start speaking or type your answer here..."
                : "Type your structured answer here..."
            }
            rows={8}
            className="form-textarea"
            style={{
              resize: "vertical",
              minHeight: "160px",
              marginBottom: "14px",
              lineHeight: "1.5",
              fontSize: "14px",
            }}
          />

          {/* Controls Bar */}
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "flex-start", gap: "10px" }}>
            {inputMode === "mic" && speechSupported ? (
              <Button
                variant={speechState === "listening" ? "danger" : "secondary"}
                size="sm"
                onClick={toggleSpeechRecognition}
                disabled={evaluating || loadingNext || submittingFinal}
              >
                {speechState === "listening" ? "● Stop Speaking" : "🎤 Start Speaking"}
              </Button>
            ) : <div />}

            <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "8px" }}>
              <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={handleSkipQuestion}
                  disabled={evaluating || loadingNext || submittingFinal}
                >
                  {loadingNext ? "Skipping..." : "Skip / I Don't Know"}
                </Button>
                <Button
                  type="button"
                  variant="primary"
                  onClick={handleSubmitAnswer}
                  loading={evaluating}
                  disabled={!answer.trim() || evaluating || loadingNext || submittingFinal}
                >
                  {evaluating ? "Submitting..." : "Submit Answer →"}
                </Button>
              </div>

              <button
                type="button"
                onClick={() => setShowEndConfirm(true)}
                disabled={evaluating || loadingNext || submittingFinal}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--text-muted)",
                  fontSize: "12px",
                  cursor: "pointer",
                  padding: "4px 6px",
                  textDecoration: "underline",
                }}
              >
                End Interview
              </button>
            </div>
          </div>
        </Card>
      </div>

      {/* End Interview Confirmation Modal */}
      {showEndConfirm && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(15, 23, 42, 0.6)",
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
              Your completed answers will be evaluated and your report will be generated.
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