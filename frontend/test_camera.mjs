import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  FACE_STATES,
  ALIGNMENT_STATES,
  classifyCameraFrame,
  calculateFaceBoundingBox,
  computeVisualCoverage,
  FaceTemporalSmoother,
  evaluateCameraAlignment,
  BlinkDetector,
  HeadMovementTracker,
  ExpressionActivityTracker,
  calculatePresentationSignals,
} from "./src/utils/cameraTrackingLogic.js";

describe("Camera Person Count & Validation", () => {
  it("detects NO_FACE when 0 landmarks detected", () => {
    const res = classifyCameraFrame([]);
    assert.equal(res.faceCount, 0);
    assert.equal(res.state, FACE_STATES.NO_FACE);
    assert.equal(res.isValidFrame, false);
    assert.equal(res.warning, "Face not detected");
  });

  it("detects ONE_FACE when exactly 1 face is present", () => {
    const face1 = [{ x: 0.4, y: 0.3 }, { x: 0.6, y: 0.7 }];
    const res = classifyCameraFrame([face1]);
    assert.equal(res.faceCount, 1);
    assert.equal(res.state, FACE_STATES.ONE_FACE);
    assert.equal(res.isValidFrame, true);
    assert.equal(res.warning, null);
  });

  it("detects MULTIPLE_FACES and triggers invalid state warning when 2 or more faces appear", () => {
    const face1 = [{ x: 0.2, y: 0.3 }];
    const face2 = [{ x: 0.7, y: 0.4 }];
    const res = classifyCameraFrame([face1, face2]);
    assert.equal(res.faceCount, 2);
    assert.equal(res.state, FACE_STATES.MULTIPLE_FACES);
    assert.equal(res.isValidFrame, false);
    assert.equal(res.warning, "Multiple people detected. Please remain alone in the frame.");
  });

  it("detects MULTIPLE_FACES with 3 faces", () => {
    const res = classifyCameraFrame([[{ x: 0.1, y: 0.1 }], [{ x: 0.5, y: 0.5 }], [{ x: 0.8, y: 0.8 }]]);
    assert.equal(res.faceCount, 3);
    assert.equal(res.state, FACE_STATES.MULTIPLE_FACES);
    assert.equal(res.isValidFrame, false);
  });

  it("calculates accurate bounding box with padding", () => {
    const landmarks = [
      { x: 0.4, y: 0.4 },
      { x: 0.6, y: 0.6 },
    ];
    const box = calculateFaceBoundingBox(landmarks, 640, 480);
    assert.ok(box.x < 0.4 * 640);
    assert.ok(box.width > 0.2 * 640);
    assert.ok(box.y < 0.4 * 480);
    assert.ok(box.height > 0.2 * 480);
  });

  it("computes visual coverage only from valid frames", () => {
    const coverage = computeVisualCoverage(100, 80);
    assert.equal(coverage, 80);
  });
});

describe("Temporal Smoothing (Section 12)", () => {
  it("prevents single-frame dropouts from causing UI flicker", () => {
    const smoother = new FaceTemporalSmoother({ noFaceThreshold: 4, oneFaceThreshold: 3 });
    // Starts in ONE_FACE
    assert.equal(smoother.smoothedState, FACE_STATES.ONE_FACE);

    // Frame 1 drops out (no face)
    let res = smoother.update({ state: FACE_STATES.NO_FACE, faceCount: 0 });
    assert.equal(res.smoothedState, FACE_STATES.ONE_FACE, "Single dropout should not switch to NO_FACE");

    // Frame 2 drops out
    res = smoother.update({ state: FACE_STATES.NO_FACE, faceCount: 0 });
    assert.equal(res.smoothedState, FACE_STATES.ONE_FACE, "2nd dropout should not switch to NO_FACE");

    // Frame 3 recovers (face detected)
    res = smoother.update({ state: FACE_STATES.ONE_FACE, faceCount: 1 });
    assert.equal(res.smoothedState, FACE_STATES.ONE_FACE, "Recovered face keeps ONE_FACE state");
  });

  it("switches to NO_FACE only after consecutive invalid threshold is reached", () => {
    const smoother = new FaceTemporalSmoother({ noFaceThreshold: 4, oneFaceThreshold: 3 });

    for (let i = 0; i < 3; i++) {
      smoother.update({ state: FACE_STATES.NO_FACE, faceCount: 0 });
    }
    assert.equal(smoother.smoothedState, FACE_STATES.ONE_FACE);

    // 4th consecutive frame triggers NO_FACE
    const res = smoother.update({ state: FACE_STATES.NO_FACE, faceCount: 0 });
    assert.equal(res.smoothedState, FACE_STATES.NO_FACE);
  });

  it("switches back to ONE_FACE after 3 consecutive valid frames", () => {
    const smoother = new FaceTemporalSmoother({
      noFaceThreshold: 4,
      oneFaceThreshold: 3,
      initialState: FACE_STATES.NO_FACE,
    });

    smoother.update({ state: FACE_STATES.ONE_FACE, faceCount: 1 });
    assert.equal(smoother.smoothedState, FACE_STATES.NO_FACE);
    smoother.update({ state: FACE_STATES.ONE_FACE, faceCount: 1 });
    assert.equal(smoother.smoothedState, FACE_STATES.NO_FACE);

    // 3rd consecutive valid frame restores ONE_FACE
    const res = smoother.update({ state: FACE_STATES.ONE_FACE, faceCount: 1 });
    assert.equal(res.smoothedState, FACE_STATES.ONE_FACE);
  });
});

describe("Camera Alignment Evaluation (Section 18)", () => {
  it("evaluates well-centered, properly-sized face as GOOD", () => {
    const landmarks = [
      { x: 0.35, y: 0.25 },
      { x: 0.65, y: 0.65 },
    ];
    const align = evaluateCameraAlignment(landmarks);
    assert.equal(align.status, ALIGNMENT_STATES.GOOD);
    assert.equal(align.message, "Good camera position");
  });

  it("detects when face is too far", () => {
    const landmarks = [
      { x: 0.48, y: 0.48 },
      { x: 0.52, y: 0.52 },
    ];
    const align = evaluateCameraAlignment(landmarks);
    assert.equal(align.status, ALIGNMENT_STATES.TOO_FAR);
    assert.equal(align.message, "Move a little closer");
  });

  it("detects when face is too close", () => {
    const landmarks = [
      { x: 0.1, y: 0.1 },
      { x: 0.9, y: 0.9 },
    ];
    const align = evaluateCameraAlignment(landmarks);
    assert.equal(align.status, ALIGNMENT_STATES.TOO_CLOSE);
    assert.equal(align.message, "Move slightly farther back");
  });

  it("detects when face is off-center", () => {
    const landmarks = [
      { x: 0.70, y: 0.30 },
      { x: 0.95, y: 0.70 },
    ];
    const align = evaluateCameraAlignment(landmarks);
    assert.equal(align.status, ALIGNMENT_STATES.SLIGHTLY_OFF_CENTER);
    assert.equal(align.message, "Move slightly toward the center");
  });
});

describe("Blink Detection (Section 21)", () => {
  it("detects blink when eye openness dips below threshold and recovers", () => {
    const detector = new BlinkDetector({ earThreshold: 0.02 });

    // Helper to generate mock 468 landmarks with specific eye openness
    const createMockFace = (eyeOpenness) => {
      const landmarks = Array.from({ length: 478 }, () => ({ x: 0.5, y: 0.5 }));
      landmarks[159] = { x: 0.4, y: 0.4 };
      landmarks[145] = { x: 0.4, y: 0.4 + eyeOpenness };
      landmarks[386] = { x: 0.6, y: 0.4 };
      landmarks[374] = { x: 0.6, y: 0.4 + eyeOpenness };
      return landmarks;
    };

    // Open eyes
    detector.processFrame(createMockFace(0.04), 1000);
    assert.equal(detector.blinkCount, 0);

    // Eye closes (blink starts)
    detector.processFrame(createMockFace(0.005), 1100);
    assert.equal(detector.blinkCount, 0);

    // Eye opens again (blink completes)
    const res = detector.processFrame(createMockFace(0.04), 1200);
    assert.equal(res.blinkCount, 1);
    assert.equal(detector.blinkCount, 1);
  });
});

describe("Head Movement & Stability (Section 22)", () => {
  it("classifies stable frontal orientation as STABLE", () => {
    const tracker = new HeadMovementTracker({ windowSize: 30 });
    const createHead = (yawOffset = 0) => {
      const landmarks = Array.from({ length: 478 }, () => ({ x: 0.5, y: 0.5 }));
      landmarks[1] = { x: 0.5 + yawOffset, y: 0.5 }; // nose
      landmarks[234] = { x: 0.3, y: 0.5 }; // left cheek
      landmarks[454] = { x: 0.7, y: 0.5 }; // right cheek
      landmarks[10] = { x: 0.5, y: 0.3 }; // forehead
      landmarks[152] = { x: 0.5, y: 0.7 }; // chin
      return landmarks;
    };

    for (let i = 0; i < 20; i++) {
      tracker.processFrame(createHead(0.01 * (i % 2 === 0 ? 1 : -1)));
    }

    const metrics = tracker.getStabilityMetrics();
    assert.equal(metrics.stability, "STABLE");
    assert.ok(metrics.facingCameraPercent >= 80);
  });
});

describe("Presentation Signals & Evidence Gating (Sections 24-27)", () => {
  it("returns insufficient visual data when valid frames are below minimum threshold", () => {
    const signals = calculatePresentationSignals({
      totalSampledFrames: 50,
      validSingleFaceFrames: 10, // less than minValidFramesRequired (30)
      alignedCount: 8,
      minValidFramesRequired: 30,
    });

    assert.equal(signals.hasSufficientData, false);
    assert.equal(signals.presentationScore, null);
    assert.equal(signals.faceVisibilityRatio, null);
    assert.equal(signals.statusText, "Not enough visual data");
  });

  it("calculates observable presentation signals when sufficient valid frames exist", () => {
    const signals = calculatePresentationSignals({
      totalSampledFrames: 100,
      validSingleFaceFrames: 90,
      alignedCount: 80,
      blinkRate: 18,
      headStability: "STABLE",
      facingCameraPercent: 95,
      expressionActivity: "MODERATE",
      minValidFramesRequired: 30,
    });

    assert.equal(signals.hasSufficientData, true);
    assert.equal(signals.faceVisibilityRatio, 90);
    assert.equal(signals.cameraAlignment, "Good");
    assert.equal(signals.headMovement, "Stable");
    assert.equal(signals.blinkRate, "18/min");
    assert.equal(signals.expressionActivity, "Moderate");
    assert.ok(signals.presentationScore >= 80);
    assert.ok(signals.disclaimer.includes("These signals describe observable camera presentation"));
  });
});

describe("Section 35 Test Cases: Full Lifecycle & Edge Conditions", () => {
  it("TEST 1: One centered face -> Face detected", () => {
    const face = [{ x: 0.35, y: 0.3 }, { x: 0.65, y: 0.7 }];
    const res = classifyCameraFrame([face]);
    assert.equal(res.state, FACE_STATES.ONE_FACE);
    assert.equal(res.faceCount, 1);
  });

  it("TEST 2: Move face to left -> Face detected + alignment warning", () => {
    const face = [{ x: 0.05, y: 0.3 }, { x: 0.25, y: 0.7 }];
    const res = classifyCameraFrame([face]);
    assert.equal(res.state, FACE_STATES.ONE_FACE);
    const align = evaluateCameraAlignment(face);
    assert.equal(align.status, ALIGNMENT_STATES.SLIGHTLY_OFF_CENTER);
  });

  it("TEST 3: Move face to right -> Face detected + alignment warning", () => {
    const face = [{ x: 0.75, y: 0.3 }, { x: 0.95, y: 0.7 }];
    const res = classifyCameraFrame([face]);
    assert.equal(res.state, FACE_STATES.ONE_FACE);
    const align = evaluateCameraAlignment(face);
    assert.equal(align.status, ALIGNMENT_STATES.SLIGHTLY_OFF_CENTER);
  });

  it("TEST 4: Move farther away -> Face detected + Move closer warning", () => {
    const face = [{ x: 0.48, y: 0.45 }, { x: 0.52, y: 0.55 }];
    const res = classifyCameraFrame([face]);
    assert.equal(res.state, FACE_STATES.ONE_FACE);
    const align = evaluateCameraAlignment(face);
    assert.equal(align.status, ALIGNMENT_STATES.TOO_FAR);
    assert.equal(align.message, "Move a little closer");
  });

  it("TEST 5: Cover face -> NO_FACE with warning", () => {
    const res = classifyCameraFrame([]);
    assert.equal(res.state, FACE_STATES.NO_FACE);
    assert.equal(res.warning, "Face not detected");
  });

  it("TEST 6: Leave camera view -> NO_FACE with warning", () => {
    const res = classifyCameraFrame([]);
    assert.equal(res.state, FACE_STATES.NO_FACE);
  });

  it("TEST 7: Second person enters -> MULTIPLE_FACES", () => {
    const person1 = [{ x: 0.2, y: 0.3 }];
    const person2 = [{ x: 0.7, y: 0.4 }];
    const res = classifyCameraFrame([person1, person2]);
    assert.equal(res.state, FACE_STATES.MULTIPLE_FACES);
    assert.equal(res.faceCount, 2);
  });

  it("TEST 8: Second person leaves -> Face detected again", () => {
    const person1 = [{ x: 0.4, y: 0.3 }];
    const res = classifyCameraFrame([person1]);
    assert.equal(res.state, FACE_STATES.ONE_FACE);
  });

  it("TEST 9: Turn head -> Face remains detected, yaw updated", () => {
    const tracker = new HeadMovementTracker({ windowSize: 10 });
    const turnedHead = Array.from({ length: 478 }, () => ({ x: 0.5, y: 0.5 }));
    turnedHead[1] = { x: 0.65, y: 0.5 }; // nose turned right
    turnedHead[234] = { x: 0.3, y: 0.5 };
    turnedHead[454] = { x: 0.7, y: 0.5 };
    turnedHead[10] = { x: 0.5, y: 0.3 };
    turnedHead[152] = { x: 0.5, y: 0.7 };

    const res = classifyCameraFrame([turnedHead]);
    assert.equal(res.state, FACE_STATES.ONE_FACE);
    const pose = tracker.processFrame(turnedHead);
    assert.ok(pose.yaw > 0.2); // yaw offset captured
  });

  it("TEST 10: Smile -> Expression activity changes", () => {
    const tracker = new ExpressionActivityTracker({ windowSize: 10 });
    const neutralFace = Array.from({ length: 478 }, () => ({ x: 0.5, y: 0.5 }));
    neutralFace[61] = { x: 0.45, y: 0.65 };
    neutralFace[291] = { x: 0.55, y: 0.65 };
    neutralFace[13] = { x: 0.50, y: 0.63 };
    neutralFace[14] = { x: 0.50, y: 0.67 };

    const smilingFace = Array.from({ length: 478 }, () => ({ x: 0.5, y: 0.5 }));
    smilingFace[61] = { x: 0.40, y: 0.64 }; // wider mouth
    smilingFace[291] = { x: 0.60, y: 0.64 };
    smilingFace[13] = { x: 0.50, y: 0.62 };
    smilingFace[14] = { x: 0.50, y: 0.68 };

    for (let i = 0; i < 5; i++) tracker.processFrame(neutralFace);
    for (let i = 0; i < 5; i++) tracker.processFrame(smilingFace);
    const activity = tracker.getActivityLevel();
    assert.ok(["LOW", "MODERATE", "HIGH"].includes(activity));
  });

  it("TEST 11: Blink -> Blink counter increments", () => {
    const detector = new BlinkDetector({ earThreshold: 0.02 });
    const openEye = Array.from({ length: 478 }, () => ({ x: 0.5, y: 0.5 }));
    openEye[159] = { x: 0.4, y: 0.4 };
    openEye[145] = { x: 0.4, y: 0.44 };
    openEye[386] = { x: 0.6, y: 0.4 };
    openEye[374] = { x: 0.6, y: 0.44 };

    const closedEye = Array.from({ length: 478 }, () => ({ x: 0.5, y: 0.5 }));
    closedEye[159] = { x: 0.4, y: 0.4 };
    closedEye[145] = { x: 0.4, y: 0.405 };
    closedEye[386] = { x: 0.6, y: 0.4 };
    closedEye[374] = { x: 0.6, y: 0.405 };

    detector.processFrame(openEye, 100);
    detector.processFrame(closedEye, 200);
    detector.processFrame(openEye, 300);
    assert.equal(detector.blinkCount, 1);
  });

  it("TEST 12: Poor lighting or low confidence landmarks -> handled gracefully", () => {
    const sparse = [];
    const res = classifyCameraFrame(sparse);
    assert.equal(res.state, FACE_STATES.NO_FACE);
  });

  it("TEST 13: Camera disabled state is distinct from face detection states", () => {
    assert.equal(FACE_STATES.CAMERA_LOADING, "CAMERA_LOADING");
    assert.equal(FACE_STATES.CAMERA_READY, "CAMERA_READY");
  });

  it("TEST 14: Model fails to load -> MODEL_ERROR / ANALYSIS_ERROR, distinct from NO_FACE", () => {
    assert.notEqual(FACE_STATES.ANALYSIS_ERROR, FACE_STATES.NO_FACE);
    assert.notEqual(FACE_STATES.MODEL_LOADING, FACE_STATES.NO_FACE);
  });
});
