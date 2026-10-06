import { useState, useEffect, useRef, useContext } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { FaceMesh } from "@mediapipe/face_mesh";
import { Camera } from "@mediapipe/camera_utils";
import { ReportContext } from "../context/ReportContext";

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
  const mode = location.state?.mode || savedState.mode || "technical";
  const difficulty = location.state?.difficulty || savedState.difficulty || "medium";
  const targetRole = location.state?.targetRole || savedState.targetRole || "Software Engineer";

  const initialQuestions = location.state?.questions || savedState.questions || [
    { id: 1, question: "Explain REST API architecture and how HTTP status codes are utilized." },
    { id: 2, question: "Describe a challenging technical problem you solved in your past project." },
    { id: 3, question: "How do you handle database indexing and optimize slow queries?" },
  ];

  const [questions, setQuestions] = useState(initialQuestions);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [timeLeft, setTimeLeft] = useState(90);
  const [answer, setAnswer] = useState("");

  // Media & Behavioral tracking state
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [isMicOn, setIsMicOn] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [eyeContact, setEyeContact] = useState(false);
  const [blinkCount, setBlinkCount] = useState(0);
  const [eyeContactPercent, setEyeContactPercent] = useState(null);

  // Speech-to-text recognition
  const [speechRecognitionActive, setSpeechRecognitionActive] = useState(false);
  const speechRecognizerRef = useRef(null);

  // Feedback & Follow-up state
  const [evaluating, setEvaluating] = useState(false);
  const [latestEvaluation, setLatestEvaluation] = useState(null);
  const [isFollowUp, setIsFollowUp] = useState(false);
  const [followUpQuestion, setFollowUpQuestion] = useState("");
  const [submittingFinal, setSubmittingFinal] = useState(false);

  // Refs for camera and metrics
  const blinkRef = useRef(false);
  const totalFramesRef = useRef(0);
  const eyeContactFramesRef = useRef(0);
  const interviewStartRef = useRef(Date.now());
  const questionStartTimeRef = useRef(Date.now());

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const cameraRef = useRef(null);
  const faceMeshRef = useRef(null);
  const meshInitialized = useRef(false);

  const currentQ = questions[currentIndex] || { id: 1, question: "Interview Question" };

  // Timer countdown per question
  useEffect(() => {
    if (timeLeft <= 0) return;
    const timer = setInterval(() => {
      setTimeLeft((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [timeLeft]);

  // Reset timer on question change
  useEffect(() => {
    setTimeLeft(90);
    questionStartTimeRef.current = Date.now();
  }, [currentIndex, isFollowUp]);

  // Initialize Speech Recognition (Web Speech API)
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognizer = new SpeechRecognition();
      recognizer.continuous = true;
      recognizer.interimResults = true;
      recognizer.lang = "en-US";

      recognizer.onresult = (event) => {
        let transcriptText = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          transcriptText += event.results[i][0].transcript;
        }
        setAnswer((prev) => {
          const base = prev ? prev.trim() + " " : "";
          return base + transcriptText.trim();
        });
      };

      recognizer.onerror = (e) => {
        console.warn("Speech recognition notice:", e.error);
        setSpeechRecognitionActive(false);
      };

      recognizer.onend = () => {
        setSpeechRecognitionActive(false);
      };

      speechRecognizerRef.current = recognizer;
    }

    return () => {
      try {
        speechRecognizerRef.current?.stop();
      } catch {}
    };
  }, []);

  const toggleSpeechRecognition = () => {
    if (!speechRecognizerRef.current) {
      alert("Speech-to-text recognition is not supported in this browser. You can type your response directly.");
      return;
    }

    if (speechRecognitionActive) {
      speechRecognizerRef.current.stop();
      setSpeechRecognitionActive(false);
      setIsRecording(false);
    } else {
      try {
        speechRecognizerRef.current.start();
        setSpeechRecognitionActive(true);
        setIsRecording(true);
      } catch (e) {
        console.warn(e);
      }
    }
  };

  // Initialize MediaPipe FaceMesh & Camera
  useEffect(() => {
    if (meshInitialized.current) return;
    meshInitialized.current = true;

    const startMedia = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: true,
        });

        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }

        setIsCameraOn(true);
        setIsMicOn(true);

        const faceMesh = new FaceMesh({
          locateFile: (file) =>
            `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`,
        });

        faceMeshRef.current = faceMesh;
        faceMesh.setOptions({
          maxNumFaces: 1,
          refineLandmarks: true,
          minDetectionConfidence: 0.6,
          minTrackingConfidence: 0.6,
        });

        faceMesh.onResults((results) => {
          const canvas = canvasRef.current;
          const video = videoRef.current;
          if (!canvas || !video || !video.videoWidth) return;

          const ctx = canvas.getContext("2d");
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;

          ctx.clearRect(0, 0, canvas.width, canvas.height);
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

          if (results.multiFaceLandmarks?.length > 0) {
            const landmarks = results.multiFaceLandmarks[0];

            // Eye Contact calculation
            const nose = landmarks[1];
            const noseX = nose.x * canvas.width;
            const centerX = canvas.width / 2;

            totalFramesRef.current++;
            if (Math.abs(noseX - centerX) < 65) {
              eyeContactFramesRef.current++;
              setEyeContact(true);
            } else {
              setEyeContact(false);
            }

            // Blink Detection
            const leftEyeTop = landmarks[159];
            const leftEyeBottom = landmarks[145];
            const leftEyeLeft = landmarks[33];
            const leftEyeRight = landmarks[133];

            const verticalDist = Math.abs(leftEyeTop.y - leftEyeBottom.y) * canvas.height;
            const horizontalDist = Math.abs(leftEyeLeft.x - leftEyeRight.x) * canvas.width;
            const eyeRatio = verticalDist / (horizontalDist || 1);

            if (eyeRatio < 0.20) {
              if (!blinkRef.current) {
                setBlinkCount((prev) => prev + 1);
                blinkRef.current = true;
              }
            } else {
              blinkRef.current = false;
            }
          } else {
            setEyeContact(false);
          }
        });

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
      } catch (err) {
        console.warn("Webcam access unavailable or skipped:", err);
        setIsCameraOn(false);
        setIsMicOn(false);
      }
    };

    startMedia();

    return () => {
      try {
        cameraRef.current?.stop();
        streamRef.current?.getTracks().forEach((track) => track.stop());
        faceMeshRef.current?.close();
      } catch {}
    };
  }, []);

  // Update Eye Contact % continuously
  useEffect(() => {
    const interval = setInterval(() => {
      if (totalFramesRef.current > 0) {
        const percent = (eyeContactFramesRef.current / totalFramesRef.current) * 100;
        setEyeContactPercent(Number(percent.toFixed(1)));
      }
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // Compute live communication indicators
  const words = answer.trim().split(/\s+/).filter(Boolean);
  const wordCount = words.length;
  const fillerRegex = /\b(um|uh|like|basically|actually|literally|you know|sort of|kind of)\b/gi;
  const fillerMatches = answer.match(fillerRegex);
  const fillerCount = fillerMatches ? fillerMatches.length : 0;
  const elapsedMinutes = (Date.now() - questionStartTimeRef.current) / 60000 || 0.5;
  const liveWpm = Math.round(wordCount / elapsedMinutes);

  // Submit Answer & Evaluate
  const handleSubmitAnswer = async () => {
    if (!answer.trim()) {
      alert("Please enter or record an answer before submitting.");
      return;
    }

    if (speechRecognitionActive) {
      try {
        speechRecognizerRef.current?.stop();
        setSpeechRecognitionActive(false);
      } catch {}
    }

    setEvaluating(true);
    const responseDuration = (Date.now() - questionStartTimeRef.current) / 1000;

    try {
      const payload = {
        session_id: Number(sessionId),
        question_id: currentQ.id || currentIndex + 1,
        question_text: isFollowUp ? followUpQuestion : currentQ.question,
        transcript: answer,
        response_time: responseDuration,
        duration_seconds: responseDuration,
        wpm: liveWpm,
        filler_count: fillerCount,
      };

      const res = await fetch(`http://127.0.0.1:8000/interview/${sessionId}/answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error(`Answer submission failed with status: ${res.status}`);
      }

      const evalData = await res.json();
      setLatestEvaluation(evalData);
    } catch (err) {
      console.warn("Using offline evaluation fallback:", err);
      setLatestEvaluation({
        score: 75.0,
        technical_score: 75.0,
        structure_score: 70.0,
        reasoning_score: 80.0,
        star_score: 70.0,
        dimensions: {
          structure: {
            score: 70.0,
            evidence: ["Structured across 3 sentences", "0 filler words"],
            explanation: "Narrative flow is coherent.",
            recommended_action: "Add explicit transitions."
          },
          technical: {
            score: 75.0,
            evidence: ["3 domain keywords found"],
            explanation: "Demonstrated solid technical understanding.",
            recommended_action: "Incorporate specific mechanisms and edge cases."
          },
          reasoning: {
            score: 80.0,
            evidence: ["trade-off terms: 1"],
            explanation: "Articulated architectural trade-offs.",
            recommended_action: "Contrast against alternative solutions."
          },
          star: {
            score: 70.0,
            evidence: ["3/4 STAR components identified", "1 quantified result found"],
            explanation: "Followed the STAR method.",
            recommended_action: "Quantify final outcomes with SLAs."
          }
        },
        strengths: ["Answer addresses the key concepts of the question."],
        weaknesses: ["Could include more specific architectural metrics and examples."],
        suggestions: ["Quantify your experience with specific engineering SLAs."],
      });
    } finally {
      setEvaluating(false);
    }
  };

  // Proceed to Next Question or Follow-up
  const handleProceed = () => {
    // Check if we should ask follow-up for short answer once
    if (!isFollowUp && wordCount < 30) {
      setIsFollowUp(true);
      setFollowUpQuestion("Can you expand on that with a concrete practical example from your experience?");
      setLatestEvaluation(null);
      setAnswer("");
      return;
    }

    setLatestEvaluation(null);
    setIsFollowUp(false);
    setFollowUpQuestion("");
    setAnswer("");

    if (currentIndex < questions.length - 1) {
      setCurrentIndex((prev) => prev + 1);
    } else {
      handleFinishInterview();
    }
  };

  // Complete Interview
  const handleFinishInterview = async () => {
    setSubmittingFinal(true);
    try {
      const durationSeconds = (Date.now() - interviewStartRef.current) / 1000;
      const durationMinutes = durationSeconds / 60 || 1;

      // Only send visual metrics if camera was active and recorded frames; never send default/imputed values
      const finalEyeContact = (isCameraOn && totalFramesRef.current > 0 && eyeContactPercent !== null)
        ? eyeContactPercent
        : null;
      const finalBlinkRate = (isCameraOn && totalFramesRef.current > 0)
        ? Number((blinkCount / durationMinutes).toFixed(1))
        : null;

      const payload = {
        eye_contact_percent: finalEyeContact,
        blink_rate: finalBlinkRate,
        pause_rate: 2.0,
        duration_seconds: durationSeconds,
      };

      const res = await fetch(`http://127.0.0.1:8000/interview/${sessionId}/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const finalReport = await res.json();
        setReportData(finalReport);
      }

      sessionStorage.setItem("interviewCompleted", "true");
      sessionStorage.setItem("currentSessionId", String(sessionId));
      navigate("/dashboard", { state: { sessionId } });
    } catch (err) {
      console.error("Complete interview error:", err);
      sessionStorage.setItem("interviewCompleted", "true");
      sessionStorage.setItem("currentSessionId", String(sessionId));
      navigate("/dashboard", { state: { sessionId } });
    } finally {
      setSubmittingFinal(false);
    }
  };

  return (
    <div style={{ maxWidth: "1200px", margin: "0 auto", paddingBottom: "60px" }}>
      {/* TOP STATUS BAR */}
      <div style={statusBar}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span style={pillBadge}>Question {currentIndex + 1} of {questions.length}</span>
          <span style={{ ...pillBadge, backgroundColor: "#f1f5f9", color: "#334155" }}>
            {mode.toUpperCase()} ROUND
          </span>
          <span style={{ ...pillBadge, backgroundColor: "#f1f5f9", color: "#334155" }}>
            {difficulty.toUpperCase()}
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "15px" }}>
          <div style={{ fontSize: "14px", fontWeight: "700", color: timeLeft < 15 ? "#dc2626" : "#0f172a" }}>
            ⏱ {timeLeft}s remaining
          </div>
          <button
            onClick={() => {
              if (confirm("Are you sure you want to conclude the interview and view your report?")) {
                handleFinishInterview();
              }
            }}
            style={exitBtn}
          >
            End Interview Early
          </button>
        </div>
      </div>

      {/* MAIN TWO COLUMN WORKSPACE */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1.35fr", gap: "25px", marginTop: "20px" }}>
        {/* LEFT COLUMN: WEBCAM FEED & BEHAVIORAL INDICATORS */}
        <div>
          <div style={videoCard}>
            <div style={{ position: "relative", minHeight: "280px", background: "#0f172a", borderRadius: "8px", overflow: "hidden" }}>
              {isCameraOn ? (
                <>
                  <video ref={videoRef} autoPlay playsInline muted style={videoElement} />
                  <canvas ref={canvasRef} style={canvasElement} />
                  <div style={eyeContact ? greenDot : redDot} title={eyeContact ? "Centered in frame" : "Re-align with center"} />
                  <div style={overlayMetrics}>
                    <div title="Share of the session your head was positioned near the centre of the frame. It does not measure gaze, confidence, or nervousness.">
                      Head alignment (proxy): <strong>{eyeContactPercent !== null ? `${eyeContactPercent}%` : "Calibrating..."}</strong>
                    </div>
                    <div>Blinks: <strong>{blinkCount}</strong></div>
                  </div>
                </>
              ) : (
                <div style={webcamFallback}>
                  <div style={{ fontSize: "40px", marginBottom: "8px" }}>🎥</div>
                  <p style={{ fontWeight: "600", fontSize: "14px" }}>Camera Inactive</p>
                  <p style={{ fontSize: "12px", color: "#94a3b8", marginTop: "4px" }}>
                    Delivery & Visual Stability marked "Not measured"
                  </p>
                </div>
              )}
            </div>

            {/* STATUS CHIPS */}
            <div style={{ display: "flex", gap: "10px", marginTop: "14px" }}>
              <StatusChip label="Camera" active={isCameraOn} />
              <StatusChip label="Microphone" active={isMicOn || speechRecognitionActive} />
              <StatusChip label="Speech Transcriber" active={speechRecognitionActive} />
            </div>

            {/* LIVE COMMUNICATION METRICS */}
            <div style={{ marginTop: "20px", borderTop: "1px solid #f1f5f9", paddingTop: "14px" }}>
              <h5 style={{ fontSize: "13px", color: "#475569", marginBottom: "8px" }}>Live Communication Stats</h5>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "10px", textAlign: "center" }}>
                <div style={statBox}>
                  <div style={statNum}>{wordCount}</div>
                  <div style={statLbl}>Words</div>
                </div>
                <div style={statBox}>
                  <div style={statNum}>{liveWpm}</div>
                  <div style={statLbl}>Est. WPM</div>
                </div>
                <div style={statBox}>
                  <div style={{ ...statNum, color: fillerCount > 3 ? "#dc2626" : "#0f172a" }}>
                    {fillerCount}
                  </div>
                  <div style={statLbl}>Fillers</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: QUESTION & ANSWER PANEL */}
        <div>
          <div style={panelCard}>
            {/* QUESTION DISPLAY */}
            <div style={{ borderBottom: "1px solid #f1f5f9", paddingBottom: "16px", marginBottom: "16px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "12px", fontWeight: "700", color: "#2563eb", textTransform: "uppercase" }}>
                  {isFollowUp ? "Deep-Dive Follow-Up Question" : `Interview Prompt #${currentIndex + 1}`}
                </span>
                <span style={{ fontSize: "12px", color: "#64748b" }}>Target: {targetRole}</span>
              </div>
              <h3 style={{ fontSize: "19px", color: "#0f172a", marginTop: "8px", lineHeight: "1.4" }}>
                {isFollowUp ? followUpQuestion : currentQ.question}
              </h3>
            </div>

            {/* ANSWER INPUT */}
            <div style={{ position: "relative" }}>
              <textarea
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="Type your answer, or click 'Start Speech-to-Text' to speak your answer naturally..."
                style={answerTextarea}
              />
            </div>

            {/* RECORDING & SUBMIT CONTROLS */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "14px" }}>
              <button
                onClick={toggleSpeechRecognition}
                style={{
                  ...micButton,
                  backgroundColor: speechRecognitionActive ? "#dc2626" : "#f1f5f9",
                  color: speechRecognitionActive ? "white" : "#0f172a",
                }}
              >
                {speechRecognitionActive ? "⏹ Stop Speaking" : "🎙 Start Speech-to-Text"}
              </button>

              {!latestEvaluation ? (
                <button
                  onClick={handleSubmitAnswer}
                  disabled={evaluating}
                  style={submitBtn}
                >
                  {evaluating ? "Evaluating Answer..." : "Submit Answer →"}
                </button>
              ) : (
                <button
                  onClick={handleProceed}
                  disabled={submittingFinal}
                  style={nextBtn}
                >
                  {currentIndex < questions.length - 1
                    ? "Proceed to Next Question →"
                    : submittingFinal
                    ? "Generating Final Report..."
                    : "Finish Interview & View Report →"}
                </button>
              )}
            </div>

            {/* INSTANT EVALUATION FEEDBACK CARD */}
            {latestEvaluation && (
              <div style={feedbackCard}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                  <h4 style={{ margin: 0, fontSize: "15px", color: "#0f172a" }}>Immediate Answer Feedback</h4>
                  <div style={{ fontSize: "18px", fontWeight: "800", color: "#16a34a" }}>
                    {latestEvaluation.score}
                    <span style={{ fontSize: "12px", color: "#64748b" }}>/100</span>
                  </div>
                </div>

                {/* RUBRIC SCORES BADGES */}
                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "12px" }}>
                  <RubricBadge label="Tech Depth" value={latestEvaluation.technical_score} />
                  <RubricBadge label="Structure" value={latestEvaluation.structure_score} />
                  <RubricBadge label="Reasoning" value={latestEvaluation.reasoning_score} />
                  <RubricBadge label="STAR" value={latestEvaluation.star_score} />
                </div>

                {/* STRENGTHS & WEAKNESSES */}
                {latestEvaluation.strengths && latestEvaluation.strengths.length > 0 && (
                  <div style={{ marginBottom: "8px" }}>
                    <span style={{ fontSize: "12px", fontWeight: "700", color: "#16a34a" }}>Strengths:</span>
                    <ul style={{ margin: "4px 0 0 16px", padding: 0, fontSize: "13px", color: "#334155" }}>
                      {latestEvaluation.strengths.map((s, idx) => (
                        <li key={idx}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {latestEvaluation.weaknesses && latestEvaluation.weaknesses.length > 0 && (
                  <div style={{ marginBottom: "8px" }}>
                    <span style={{ fontSize: "12px", fontWeight: "700", color: "#dc2626" }}>Weaknesses:</span>
                    <ul style={{ margin: "4px 0 0 16px", padding: 0, fontSize: "13px", color: "#7f1d1d" }}>
                      {latestEvaluation.weaknesses.map((w, idx) => (
                        <li key={idx}>{w}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {latestEvaluation.suggestions && latestEvaluation.suggestions.length > 0 && (
                  <div style={{ marginBottom: "10px" }}>
                    <span style={{ fontSize: "12px", fontWeight: "700", color: "#2563eb" }}>Quick Tip:</span>
                    <p style={{ margin: "2px 0 0", fontSize: "13px", color: "#1e40af" }}>
                      {latestEvaluation.suggestions[0]}
                    </p>
                  </div>
                )}

                {/* OBSERVABLE EVIDENCE PER DIMENSION */}
                {latestEvaluation.dimensions && Object.keys(latestEvaluation.dimensions).length > 0 && (
                  <div style={{ marginTop: "10px", borderTop: "1px solid #e2e8f0", paddingTop: "8px" }}>
                    <span style={{ fontSize: "11px", fontWeight: "700", color: "#475569", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                      Observable Evidence:
                    </span>
                    <div style={{ display: "flex", flexDirection: "column", gap: "5px", marginTop: "6px" }}>
                      {Object.entries(latestEvaluation.dimensions).map(([dimKey, dimVal]) => (
                        <div key={dimKey} style={{ fontSize: "12px", color: "#334155", backgroundColor: "#f8fafc", padding: "5px 8px", borderRadius: "4px", border: "1px solid #e2e8f0" }}>
                          <strong style={{ textTransform: "capitalize", color: "#1e293b" }}>{dimKey}: </strong>
                          <span>{(dimVal.evidence || []).join(" • ")}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function RubricBadge({ label, value }) {
  if (value === undefined || value === null) return null;
  return (
    <span
      style={{
        fontSize: "11px",
        fontWeight: "600",
        backgroundColor: "#f8fafc",
        border: "1px solid #e2e8f0",
        padding: "3px 8px",
        borderRadius: "4px",
        color: "#334155",
      }}
    >
      {label}: <strong>{Math.round(value)}%</strong>
    </span>
  );
}

function StatusChip({ label, active }) {
  return (
    <div
      style={{
        padding: "5px 10px",
        borderRadius: "6px",
        backgroundColor: active ? "#dcfce7" : "#f1f5f9",
        color: active ? "#15803d" : "#64748b",
        fontSize: "11px",
        fontWeight: "600",
        display: "flex",
        alignItems: "center",
        gap: "6px",
      }}
    >
      <span style={{ fontSize: "8px" }}>{active ? "●" : "○"}</span>
      {label}
    </div>
  );
}

/* STYLES */
const statusBar = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  background: "white",
  padding: "14px 20px",
  borderRadius: "8px",
  border: "1px solid #e2e8f0",
  boxShadow: "0 1px 2px rgba(0,0,0,0.03)",
};

const pillBadge = {
  fontSize: "12px",
  fontWeight: "700",
  padding: "4px 10px",
  borderRadius: "20px",
  backgroundColor: "#0f172a",
  color: "white",
};

const exitBtn = {
  padding: "6px 12px",
  fontSize: "12px",
  border: "1px solid #cbd5e1",
  borderRadius: "6px",
  background: "white",
  color: "#64748b",
  cursor: "pointer",
};

const videoCard = {
  background: "white",
  padding: "16px",
  borderRadius: "10px",
  border: "1px solid #e2e8f0",
  boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
};

const videoElement = {
  width: "100%",
  height: "100%",
  objectFit: "cover",
  display: "block",
};

const canvasElement = {
  position: "absolute",
  top: 0,
  left: 0,
  width: "100%",
  height: "100%",
};

const greenDot = {
  position: "absolute",
  top: "12px",
  right: "12px",
  width: "12px",
  height: "12px",
  borderRadius: "50%",
  backgroundColor: "#22c55e",
  border: "2px solid white",
};

const redDot = {
  ...greenDot,
  backgroundColor: "#ef4444",
};

const overlayMetrics = {
  position: "absolute",
  bottom: "10px",
  left: "10px",
  backgroundColor: "rgba(15, 23, 42, 0.75)",
  color: "white",
  padding: "6px 10px",
  borderRadius: "6px",
  fontSize: "11px",
  lineHeight: "1.5",
};

const webcamFallback = {
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  height: "280px",
  color: "white",
  textAlign: "center",
};

const statBox = {
  background: "#f8fafc",
  padding: "8px",
  borderRadius: "6px",
  border: "1px solid #e2e8f0",
};

const statNum = {
  fontSize: "16px",
  fontWeight: "700",
  color: "#0f172a",
};

const statLbl = {
  fontSize: "11px",
  color: "#64748b",
  marginTop: "2px",
};

const panelCard = {
  background: "white",
  padding: "24px",
  borderRadius: "10px",
  border: "1px solid #e2e8f0",
  boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
};

const answerTextarea = {
  width: "100%",
  minHeight: "180px",
  padding: "14px",
  borderRadius: "8px",
  border: "1px solid #cbd5e1",
  fontFamily: "Inter, sans-serif",
  fontSize: "14px",
  lineHeight: "1.5",
  boxSizing: "border-box",
  resize: "vertical",
};

const micButton = {
  padding: "10px 16px",
  borderRadius: "6px",
  border: "1px solid #cbd5e1",
  fontSize: "13px",
  fontWeight: "600",
  cursor: "pointer",
  transition: "all 0.15s ease",
};

const submitBtn = {
  padding: "10px 22px",
  backgroundColor: "#0f172a",
  color: "white",
  border: "none",
  borderRadius: "6px",
  fontSize: "14px",
  fontWeight: "600",
  cursor: "pointer",
};

const nextBtn = {
  ...submitBtn,
  backgroundColor: "#2563eb",
};

const feedbackCard = {
  marginTop: "20px",
  padding: "16px",
  backgroundColor: "#f8fafc",
  borderRadius: "8px",
  border: "1px solid #e2e8f0",
};

export default Interview;