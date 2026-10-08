/**
 * Pure helper logic for Camera Face Analysis, Multi-Person Detection,
 * Temporal Smoothing, Alignment, Presentation Signals & Visual Quality Gating.
 */

export const FACE_STATES = {
  CAMERA_LOADING: "CAMERA_LOADING",
  CAMERA_READY: "CAMERA_READY",
  MODEL_LOADING: "MODEL_LOADING",
  MODEL_READY: "MODEL_READY",
  ANALYZING: "ANALYZING",
  ONE_FACE: "ONE_FACE",
  FACE_DETECTED: "ONE_FACE", // Alias for ONE_FACE
  NO_FACE: "NO_FACE",
  MULTIPLE_FACES: "MULTIPLE_FACES",
  ANALYSIS_ERROR: "ANALYSIS_ERROR",
  INSUFFICIENT_DATA: "INSUFFICIENT_DATA",
};

export const ALIGNMENT_STATES = {
  GOOD: "GOOD",
  SLIGHTLY_OFF_CENTER: "SLIGHTLY_OFF_CENTER",
  TOO_FAR: "TOO_FAR",
  TOO_CLOSE: "TOO_CLOSE",
};

/**
 * Classifies frame based on detected face landmark arrays.
 * @param {Array<Array<{x: number, y: number, z?: number}>>} multiFaceLandmarks
 * @returns {{ faceCount: number, state: string, isValidFrame: boolean, warning: string | null }}
 */
export function classifyCameraFrame(multiFaceLandmarks = []) {
  const faceCount = Array.isArray(multiFaceLandmarks) ? multiFaceLandmarks.length : 0;

  if (faceCount === 0) {
    return {
      faceCount: 0,
      state: FACE_STATES.NO_FACE,
      isValidFrame: false,
      warning: "Face not detected",
    };
  }

  if (faceCount === 1) {
    return {
      faceCount: 1,
      state: FACE_STATES.ONE_FACE,
      isValidFrame: true,
      warning: null,
    };
  }

  return {
    faceCount,
    state: FACE_STATES.MULTIPLE_FACES,
    isValidFrame: false,
    warning: "Multiple people detected. Please remain alone in the frame.",
  };
}

/**
 * Temporal smoother to prevent rapid UI flickering across raw frames.
 * - Requires 3-5 consecutive invalid frames to switch to NO_FACE
 * - Requires 3 consecutive valid frames to switch back to ONE_FACE
 * - Requires 2 consecutive frames to switch to MULTIPLE_FACES
 */
export class FaceTemporalSmoother {
  constructor({
    windowSize = 20,
    noFaceThreshold = 4,
    oneFaceThreshold = 3,
    multipleFacesThreshold = 2,
    initialState = FACE_STATES.ONE_FACE,
  } = {}) {
    this.windowSize = windowSize;
    this.noFaceThreshold = noFaceThreshold;
    this.oneFaceThreshold = oneFaceThreshold;
    this.multipleFacesThreshold = multipleFacesThreshold;
    this.smoothedState = initialState;
    this.history = [];
    this.consecutive = {
      [FACE_STATES.NO_FACE]: 0,
      [FACE_STATES.ONE_FACE]: 0,
      [FACE_STATES.MULTIPLE_FACES]: 0,
    };
  }

  update(rawClassification, timestamp = Date.now()) {
    const rawState = rawClassification?.state || FACE_STATES.NO_FACE;
    const faceCount = rawClassification?.faceCount ?? 0;

    this.history.push({ rawState, faceCount, timestamp });
    if (this.history.length > this.windowSize) {
      this.history.shift();
    }

    // Update consecutive counts
    for (const key of Object.keys(this.consecutive)) {
      if (key === rawState) {
        this.consecutive[key] += 1;
      } else {
        this.consecutive[key] = 0;
      }
    }

    // Transition checks
    if (
      this.smoothedState !== FACE_STATES.MULTIPLE_FACES &&
      this.consecutive[FACE_STATES.MULTIPLE_FACES] >= this.multipleFacesThreshold
    ) {
      this.smoothedState = FACE_STATES.MULTIPLE_FACES;
    } else if (
      this.smoothedState !== FACE_STATES.NO_FACE &&
      this.consecutive[FACE_STATES.NO_FACE] >= this.noFaceThreshold
    ) {
      this.smoothedState = FACE_STATES.NO_FACE;
    } else if (
      this.smoothedState !== FACE_STATES.ONE_FACE &&
      this.consecutive[FACE_STATES.ONE_FACE] >= this.oneFaceThreshold
    ) {
      this.smoothedState = FACE_STATES.ONE_FACE;
    }

    return {
      smoothedState: this.smoothedState,
      rawState,
      faceCount,
      isValid: this.smoothedState === FACE_STATES.ONE_FACE,
    };
  }

  reset() {
    this.history = [];
    this.consecutive = {
      [FACE_STATES.NO_FACE]: 0,
      [FACE_STATES.ONE_FACE]: 0,
      [FACE_STATES.MULTIPLE_FACES]: 0,
    };
  }
}

/**
 * Calculates normalized bounding box from face mesh landmarks.
 * @param {Array<{x: number, y: number}>} landmarks
 * @param {number} width
 * @param {number} height
 * @returns {{ x: number, y: number, width: number, height: number } | null}
 */
export function calculateFaceBoundingBox(landmarks, width, height) {
  if (!landmarks || landmarks.length === 0 || width <= 0 || height <= 0) return null;

  let minX = 1.0, maxX = 0.0, minY = 1.0, maxY = 0.0;
  for (let i = 0; i < landmarks.length; i++) {
    const pt = landmarks[i];
    if (pt.x < minX) minX = pt.x;
    if (pt.x > maxX) maxX = pt.x;
    if (pt.y < minY) minY = pt.y;
    if (pt.y > maxY) maxY = pt.y;
  }

  // Add 10% breathing room padding
  const padX = (maxX - minX) * 0.1;
  const padY = (maxY - minY) * 0.1;

  const boxMinX = Math.max(0, minX - padX);
  const boxMaxX = Math.min(1.0, maxX + padX);
  const boxMinY = Math.max(0, minY - padY);
  const boxMaxY = Math.min(1.0, maxY + padY);

  return {
    x: boxMinX * width,
    y: boxMinY * height,
    width: (boxMaxX - boxMinX) * width,
    height: (boxMaxY - boxMinY) * height,
  };
}

/**
 * Computes visual analysis coverage strictly considering valid frames.
 */
export function computeVisualCoverage(totalFrames, validFrames) {
  if (!totalFrames || totalFrames <= 0) return 0;
  return Math.min(100, Math.max(0, Math.round((validFrames / totalFrames) * 100)));
}

/**
 * Evaluates candidate camera alignment and distance.
 * Returns human-readable UI positioning guidance.
 */
export function evaluateCameraAlignment(landmarks) {
  if (!landmarks || landmarks.length === 0) return null;

  let minX = 1.0, maxX = 0.0, minY = 1.0, maxY = 0.0;
  for (let i = 0; i < landmarks.length; i++) {
    const pt = landmarks[i];
    if (pt.x < minX) minX = pt.x;
    if (pt.x > maxX) maxX = pt.x;
    if (pt.y < minY) minY = pt.y;
    if (pt.y > maxY) maxY = pt.y;
  }

  const centerX = (minX + maxX) / 2;
  const centerY = (minY + maxY) / 2;
  const faceWidth = maxX - minX;
  const faceHeight = maxY - minY;

  // Face size checks relative to frame
  if (faceWidth < 0.15 || faceHeight < 0.18) {
    return {
      status: ALIGNMENT_STATES.TOO_FAR,
      message: "Move a little closer",
      centerX,
      centerY,
      faceWidth,
      faceHeight,
    };
  }

  if (faceWidth > 0.65 || faceHeight > 0.75) {
    return {
      status: ALIGNMENT_STATES.TOO_CLOSE,
      message: "Move slightly farther back",
      centerX,
      centerY,
      faceWidth,
      faceHeight,
    };
  }

  // Centering check (frame center is 0.5, allow +/- 0.16 horizontal tolerance)
  if (Math.abs(centerX - 0.5) > 0.16 || Math.abs(centerY - 0.45) > 0.22) {
    return {
      status: ALIGNMENT_STATES.SLIGHTLY_OFF_CENTER,
      message: "Move slightly toward the center",
      centerX,
      centerY,
      faceWidth,
      faceHeight,
    };
  }

  return {
    status: ALIGNMENT_STATES.GOOD,
    message: "Good camera position",
    centerX,
    centerY,
    faceWidth,
    faceHeight,
  };
}

/**
 * Blink Detector using Eye Aspect Ratio (EAR) across consecutive frames.
 */
export class BlinkDetector {
  constructor({
    earThreshold = 0.015,
    minConsecutiveFrames = 1,
    maxConsecutiveFrames = 15,
  } = {}) {
    this.earThreshold = earThreshold;
    this.minConsecutiveFrames = minConsecutiveFrames;
    this.maxConsecutiveFrames = maxConsecutiveFrames;
    this.blinkCount = 0;
    this.blinkTimestamps = [];
    this.isBlinking = false;
    this.closedFrameCount = 0;
  }

  processFrame(landmarks, timestamp = Date.now()) {
    if (!landmarks || landmarks.length < 468) {
      return {
        blinkCount: this.blinkCount,
        blinkRate: this.getBlinkRate(timestamp),
        eyeOpenness: null,
      };
    }

    // Left eye vertical distance: 159 (top) to 145 (bottom)
    // Right eye vertical distance: 386 (top) to 374 (bottom)
    const leftTop = landmarks[159];
    const leftBot = landmarks[145];
    const rightTop = landmarks[386];
    const rightBot = landmarks[374];

    const leftDist = Math.hypot(leftTop.x - leftBot.x, leftTop.y - leftBot.y);
    const rightDist = Math.hypot(rightTop.x - rightBot.x, rightTop.y - rightBot.y);
    const avgOpenness = (leftDist + rightDist) / 2;

    if (avgOpenness < this.earThreshold) {
      this.closedFrameCount += 1;
      if (this.closedFrameCount >= this.minConsecutiveFrames && !this.isBlinking) {
        this.isBlinking = true;
      }
    } else {
      if (this.isBlinking && this.closedFrameCount <= this.maxConsecutiveFrames) {
        this.blinkCount += 1;
        this.blinkTimestamps.push(timestamp);
      }
      this.isBlinking = false;
      this.closedFrameCount = 0;
    }

    // Retain blink events within the last 60 seconds
    this.blinkTimestamps = this.blinkTimestamps.filter((t) => timestamp - t <= 60000);

    return {
      blinkCount: this.blinkCount,
      blinkRate: this.getBlinkRate(timestamp),
      eyeOpenness: Number(avgOpenness.toFixed(4)),
    };
  }

  getBlinkRate(now = Date.now()) {
    const recent = this.blinkTimestamps.filter((t) => now - t <= 60000);
    return recent.length; // Blinks in the last 60 seconds
  }

  reset() {
    this.blinkCount = 0;
    this.blinkTimestamps = [];
    this.isBlinking = false;
    this.closedFrameCount = 0;
  }
}

/**
 * Head Movement Tracker to monitor yaw, pitch, and camera orientation stability.
 */
export class HeadMovementTracker {
  constructor({ windowSize = 60 } = {}) {
    this.windowSize = windowSize;
    this.history = []; // { yaw, pitch, roll, timestamp }
  }

  processFrame(landmarks, timestamp = Date.now()) {
    if (!landmarks || landmarks.length < 468) return null;

    const nose = landmarks[1];
    const leftSide = landmarks[234];
    const rightSide = landmarks[454];
    const forehead = landmarks[10];
    const chin = landmarks[152];

    const faceWidth = Math.abs(rightSide.x - leftSide.x) || 0.001;
    const faceHeight = Math.abs(chin.y - forehead.y) || 0.001;

    // Yaw: relative nose horizontal offset
    const midX = (leftSide.x + rightSide.x) / 2;
    const yaw = (nose.x - midX) / faceWidth;

    // Pitch: relative nose vertical offset
    const midY = (forehead.y + chin.y) / 2;
    const pitch = (nose.y - midY) / faceHeight;

    // Roll: head tilt angle
    const roll = Math.atan2(rightSide.y - leftSide.y, rightSide.x - leftSide.x);

    this.history.push({ yaw, pitch, roll, timestamp });
    if (this.history.length > this.windowSize) {
      this.history.shift();
    }

    return { yaw, pitch, roll };
  }

  getStabilityMetrics() {
    if (this.history.length < 5) {
      return {
        stability: "INSUFFICIENT_DATA",
        description: "Collecting head movement data...",
        facingCameraPercent: 100,
      };
    }

    // Calculate facing camera percentage (|yaw| < 0.20 && |pitch| < 0.25)
    let facingCount = 0;
    for (let i = 0; i < this.history.length; i++) {
      const { yaw, pitch } = this.history[i];
      if (Math.abs(yaw) < 0.20 && Math.abs(pitch) < 0.25) {
        facingCount += 1;
      }
    }
    const facingCameraPercent = Math.round((facingCount / this.history.length) * 100);

    // Calculate movement deltas
    let totalDelta = 0;
    for (let i = 1; i < this.history.length; i++) {
      const prev = this.history[i - 1];
      const curr = this.history[i];
      totalDelta += Math.abs(curr.yaw - prev.yaw) + Math.abs(curr.pitch - prev.pitch);
    }
    const avgDelta = totalDelta / (this.history.length - 1);

    if (facingCameraPercent >= 80 && avgDelta < 0.06) {
      return {
        stability: "STABLE",
        description: "Your head position stayed mostly stable.",
        facingCameraPercent,
      };
    } else if (facingCameraPercent < 55 || avgDelta > 0.15) {
      return {
        stability: "FREQUENT_TURNS",
        description: "You frequently turned away from the camera while answering.",
        facingCameraPercent,
      };
    }

    return {
      stability: "MODERATE",
      description: "Moderate head movement observed.",
      facingCameraPercent,
    };
  }

  reset() {
    this.history = [];
  }
}

/**
 * Expression Activity Tracker based on mouth & brow motion over rolling window.
 */
export class ExpressionActivityTracker {
  constructor({ windowSize = 60 } = {}) {
    this.windowSize = windowSize;
    this.history = []; // { mouthOpen, mouthWidth, timestamp }
  }

  processFrame(landmarks, timestamp = Date.now()) {
    if (!landmarks || landmarks.length < 468) return null;

    // Mouth corners: 61 (left) and 291 (right)
    // Lips: 13 (top) and 14 (bottom)
    const mouthLeft = landmarks[61];
    const mouthRight = landmarks[291];
    const lipTop = landmarks[13];
    const lipBot = landmarks[14];

    const mouthWidth = Math.hypot(mouthRight.x - mouthLeft.x, mouthRight.y - mouthLeft.y);
    const mouthHeight = Math.hypot(lipBot.x - lipTop.x, lipBot.y - lipTop.y);
    const mouthRatio = mouthWidth > 0 ? mouthHeight / mouthWidth : 0;

    this.history.push({ mouthRatio, mouthWidth, timestamp });
    if (this.history.length > this.windowSize) {
      this.history.shift();
    }

    return { mouthRatio, mouthWidth };
  }

  getActivityLevel() {
    if (this.history.length < 5) return "MODERATE";

    let varianceSum = 0;
    let meanRatio = 0;
    for (let i = 0; i < this.history.length; i++) {
      meanRatio += this.history[i].mouthRatio;
    }
    meanRatio /= this.history.length;

    for (let i = 0; i < this.history.length; i++) {
      const diff = this.history[i].mouthRatio - meanRatio;
      varianceSum += diff * diff;
    }
    const stdDev = Math.sqrt(varianceSum / this.history.length);

    if (stdDev < 0.02) return "LOW";
    if (stdDev > 0.08) return "HIGH";
    return "MODERATE";
  }

  reset() {
    this.history = [];
  }
}

/**
 * Calculates complete presentation signals summary.
 * Strictly adheres to observable presentation signals with evidence gating.
 */
export function calculatePresentationSignals({
  totalSampledFrames = 0,
  validSingleFaceFrames = 0,
  alignedCount = 0,
  blinkRate = 0,
  headStability = "STABLE",
  facingCameraPercent = 100,
  expressionActivity = "MODERATE",
  minValidFramesRequired = 30, // Minimum data gating (approx. 3-5 seconds of valid video)
} = {}) {
  // If no face was ever detected or insufficient observations exist
  if (totalSampledFrames === 0 || validSingleFaceFrames < minValidFramesRequired) {
    return {
      hasSufficientData: false,
      faceVisibilityRatio: null,
      cameraAlignment: null,
      headMovement: null,
      blinkRate: null,
      expressionActivity: null,
      presentationScore: null,
      disclaimer:
        "These signals describe observable camera presentation. They do not determine confidence, honesty, or emotional state.",
      statusText: "Not enough visual data",
    };
  }

  // Observable face visibility ratio
  const faceVisibilityRatio = Math.min(
    100,
    Math.round((validSingleFaceFrames / totalSampledFrames) * 100)
  );

  // Camera alignment ratio among valid frames
  const alignmentPercent = Math.min(
    100,
    Math.round((alignedCount / validSingleFaceFrames) * 100)
  );
  const cameraAlignment =
    alignmentPercent >= 75
      ? "Good"
      : alignmentPercent >= 50
      ? "Slightly off-center"
      : "Needs adjustment";

  // Weighted Presentation Score:
  // Face visibility: 35%, Camera alignment: 25%, Head orientation: 20%, Blink quality: 10%, Expression activity: 10%
  const visibilityScore = faceVisibilityRatio * 0.35;
  const alignmentScore = alignmentPercent * 0.25;
  const headScore = (facingCameraPercent || 90) * 0.20;
  // Reasonable blink rate is between 12-25 blinks/min (100%), penalize if 0 or extreme
  const blinkScore = (blinkRate >= 8 && blinkRate <= 35 ? 100 : 70) * 0.10;
  const expressionScore =
    (expressionActivity === "MODERATE" ? 95 : expressionActivity === "HIGH" ? 90 : 80) * 0.10;

  const presentationScore = Math.round(
    visibilityScore + alignmentScore + headScore + blinkScore + expressionScore
  );

  return {
    hasSufficientData: true,
    faceVisibilityRatio,
    cameraAlignment,
    headMovement:
      headStability === "STABLE"
        ? "Stable"
        : headStability === "FREQUENT_TURNS"
        ? "Frequent turns"
        : "Moderate",
    blinkRate: `${blinkRate}/min`,
    expressionActivity:
      expressionActivity === "HIGH"
        ? "High"
        : expressionActivity === "LOW"
        ? "Low"
        : "Moderate",
    presentationScore,
    disclaimer:
      "These signals describe observable camera presentation. They do not determine confidence, honesty, or emotional state.",
    statusText: "Observable presentation signals calculated",
  };
}
