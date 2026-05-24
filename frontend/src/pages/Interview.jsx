import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { FaceMesh } from "@mediapipe/face_mesh";
import { Camera } from "@mediapipe/camera_utils";
import { useLocation } from "react-router-dom";
import { questionBank } from "../data/questionBank";

function Interview() {
  const [timeLeft, setTimeLeft] = useState(60);
  const [answer, setAnswer] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [isMicOn, setIsMicOn] = useState(false);
  const [eyeContact, setEyeContact] = useState(false);
  const [blinkCount, setBlinkCount] = useState(0);
  const [eyeContactPercent, setEyeContactPercent] = useState(0);

  const [isFollowUp, setIsFollowUp] = useState(false);
const [followUpQuestion, setFollowUpQuestion] = useState("");

  const blinkRef = useRef(false);
  const totalFramesRef = useRef(0);
  const eyeContactFramesRef = useRef(0);
  const interviewStartRef = useRef(Date.now());

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const cameraRef = useRef(null);
  const faceMeshRef = useRef(null);
  const meshInitialized = useRef(false);

  const navigate = useNavigate();

 const location = useLocation();

const { mode, difficulty, questionCount } = location.state || {
  mode: "practice",
  difficulty: "easy",
  questionCount: 3,
};

const [selectedQuestions, setSelectedQuestions] = useState([]);
const [currentIndex, setCurrentIndex] = useState(0);

useEffect(() => {
  const allQuestions = questionBank[mode][difficulty] || [];

  const shuffled = [...allQuestions]
    .sort(() => 0.5 - Math.random())
    .slice(0, questionCount);

  setSelectedQuestions(shuffled);
}, [mode, difficulty, questionCount]);

const currentQuestion = selectedQuestions[currentIndex];

const generateFollowUp = (answerText) => {
  if (!answerText || answerText.length < 80) {
    return "Can you explain that in more detail?";
  }

  const hasNumbers = /\d/.test(answerText);

  if (!hasNumbers) {
    return "Can you quantify the impact of your work?";
  }

  if (!answerText.toLowerCase().includes("challenge")) {
    return "What was the biggest challenge you faced?";
  }

  return null;
};
  /* ================= TIMER ================= */
  useEffect(() => {
    if (timeLeft === 0) return;
    const timer = setTimeout(() => setTimeLeft((prev) => prev - 1), 1000);
    return () => clearTimeout(timer);
  }, [timeLeft]);

  /* ================= INIT MEDIA + FACEMESH ================= */
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
        videoRef.current.srcObject = stream;

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

            // Eye Contact
            const nose = landmarks[1];
            const noseX = nose.x * canvas.width;
            const centerX = canvas.width / 2;

            totalFramesRef.current++;

            if (Math.abs(noseX - centerX) < 60) {
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

            const verticalDist =
              Math.abs(leftEyeTop.y - leftEyeBottom.y) * canvas.height;

            const horizontalDist =
              Math.abs(leftEyeLeft.x - leftEyeRight.x) * canvas.width;

            const eyeRatio = verticalDist / horizontalDist;

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
            if (faceMeshRef.current) {
              await faceMeshRef.current.send({ image: videoRef.current });
            }
          },
          width: 640,
          height: 480,
        });

        camera.start();
        cameraRef.current = camera;
      } catch (err) {
        console.error("Permission denied:", err);
      }
    };

    startMedia();

    return () => {
      cameraRef.current?.stop();
      streamRef.current?.getTracks().forEach((track) => track.stop());
      faceMeshRef.current?.close();
    };
  }, []);

  /* ===== Update Eye Contact % ===== */
  useEffect(() => {
    const interval = setInterval(() => {
      if (totalFramesRef.current > 0) {
        const percent =
          (eyeContactFramesRef.current / totalFramesRef.current) * 100;
        setEyeContactPercent(percent.toFixed(1));
      }
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  /* ================= RECORDING ================= */
  const startRecording = () => {
    if (!streamRef.current) return;

    audioChunksRef.current = [];
    const recorder = new MediaRecorder(streamRef.current);
    mediaRecorderRef.current = recorder;

    recorder.ondataavailable = (event) => {
      audioChunksRef.current.push(event.data);
    };

    recorder.start();
    setIsRecording(true);
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  };

  /* ================= SUBMIT ================= */
const handleNext = () => {
  if (!isFollowUp) {
    const followUp = generateFollowUp(answer);

    if (followUp) {
      setFollowUpQuestion(followUp);
      setIsFollowUp(true);
      setAnswer("");
      return;
    }
  }

  // Save question-level data here

  setBlinkCount(0);
  eyeContactFramesRef.current = 0;
  totalFramesRef.current = 0;

  setIsFollowUp(false);
  setFollowUpQuestion("");
  setAnswer("");

  if (currentIndex < selectedQuestions.length - 1) {
    setCurrentIndex((prev) => prev + 1);
  } else {
    handleSubmit();
  }
};
  const handleSubmit = async () => {
    try {
      const durationSeconds =
        (Date.now() - interviewStartRef.current) / 1000;

      const durationMinutes = durationSeconds / 60 || 1;
      const blinkRate = blinkCount / durationMinutes;

      const response = await fetch(
        "http://127.0.0.1:8000/interview/submit",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            mode,
            difficulty,
            duration_seconds: durationSeconds,
            eye_contact_percent: parseFloat(eyeContactPercent),
            blink_rate: blinkRate,
            pause_rate: 2,
          }),
        }
      );

      const data = await response.json();
      console.log("Backend Response:", data);

      navigate("/dashboard");
    } catch (error) {
      console.error("Submission error:", error);
    }
  };

  return (
    <div style={{ maxWidth: "1100px", margin: "0 auto" }}>
      <h2>Live Mock Interview</h2>

      <div style={{ display: "flex", gap: "30px", marginTop: "30px" }}>
        <div style={videoContainer}>
          <div style={{ position: "relative" }}>
            <video ref={videoRef} autoPlay playsInline style={videoStyle} />
            <canvas ref={canvasRef} style={canvasStyle} />

            <div style={eyeContact ? greenDot : redDot}></div>

            <div style={overlayInfo}>
              Blinks: {blinkCount}
              <br />
              Eye Contact: {eyeContactPercent}%
            </div>
          </div>

          <div style={statusRow}>
            <Status label="Camera" active={isCameraOn} />
            <Status label="Mic" active={isMicOn} />
            {isRecording && <Status label="Recording" active />}
          </div>
        </div>

        <div style={panel}>
          <h4>AI Question:</h4>
          <p>
  {isFollowUp
    ? followUpQuestion
    : currentQuestion || "Loading question..."}
</p>
          <p>⏱ {timeLeft}s remaining</p>

          <textarea
            style={textareaStyle}
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Start answering..."
          />

          {!isRecording ? (
            <button style={btn} onClick={startRecording}>
              Start Recording
            </button>
          ) : (
            <button style={btn} onClick={stopRecording}>
              Stop Recording
            </button>
          )}

          <button style={btn} onClick={handleNext}>
  {currentIndex < selectedQuestions.length - 1
    ? "Next Question"
    : "Finish Interview"}
</button>
        </div>
      </div>
    </div>
  );
}

/* ================= UI COMPONENTS ================= */

function Status({ label, active }) {
  return (
    <div
      style={{
        padding: "6px 10px",
        borderRadius: "6px",
        background: active ? "#16a34a" : "#dc2626",
        color: "white",
        fontSize: "12px",
      }}
    >
      {label}
    </div>
  );
}

/* ================= STYLES ================= */

const videoContainer = {
  flex: 1,
  background: "white",
  padding: "20px",
  borderRadius: "8px",
  boxShadow: "0 2px 8px rgba(0,0,0,0.05)",
};

const videoStyle = { width: "100%", borderRadius: "8px" };

const canvasStyle = {
  position: "absolute",
  top: 0,
  left: 0,
  width: "100%",
  height: "100%",
};

const greenDot = {
  position: "absolute",
  top: "10px",
  right: "10px",
  width: "15px",
  height: "15px",
  borderRadius: "50%",
  background: "green",
};

const redDot = { ...greenDot, background: "red" };

const overlayInfo = {
  position: "absolute",
  bottom: "10px",
  left: "10px",
  background: "rgba(0,0,0,0.6)",
  color: "white",
  padding: "6px 10px",
  borderRadius: "6px",
  fontSize: "12px",
};

const statusRow = { display: "flex", gap: "10px", marginTop: "15px" };

const panel = {
  flex: 1,
  background: "white",
  padding: "25px",
  borderRadius: "8px",
  boxShadow: "0 2px 8px rgba(0,0,0,0.05)",
};

const textareaStyle = {
  width: "100%",
  minHeight: "120px",
  marginTop: "15px",
  padding: "10px",
  borderRadius: "6px",
  border: "1px solid #ddd",
};

const btn = {
  marginTop: "15px",
  padding: "10px 15px",
  borderRadius: "6px",
  border: "none",
  background: "#0f172a",
  color: "white",
  cursor: "pointer",
};

export default Interview;