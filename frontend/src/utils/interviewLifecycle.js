/**
 * frontend/src/utils/interviewLifecycle.js
 * 
 * Formal Interview Lifecycle State Machine:
 * IDLE -> STARTING -> PREPARING -> ACTIVE -> PAUSED -> SUBMITTING -> FINALIZING -> COMPLETED -> ENDING -> ABORTED
 * 
 * Manages:
 * 1. Global lifecycle state synchronized across React components and sessionStorage.
 * 2. Active interview guard checks for navigation and route protection.
 * 3. Session cleanup on completion or intentional exit.
 */

export const InterviewLifecycleState = Object.freeze({
  IDLE: "IDLE",
  STARTING: "STARTING",
  PREPARING: "PREPARING",
  ACTIVE: "ACTIVE",
  PAUSED: "PAUSED",
  SUBMITTING: "SUBMITTING",
  FINALIZING: "FINALIZING",
  COMPLETED: "COMPLETED",
  ENDING: "ENDING",
  ABORTED: "ABORTED",
});

const STORAGE_KEY_LIFECYCLE = "interviewLifecycleState";
const STORAGE_KEY_ACTIVE = "interviewActive";

/**
 * Returns current lifecycle state from sessionStorage or default IDLE.
 */
export function getInterviewLifecycleState() {
  try {
    const val = sessionStorage.getItem(STORAGE_KEY_LIFECYCLE);
    if (val && Object.values(InterviewLifecycleState).includes(val)) {
      return val;
    }
  } catch (e) {
    console.warn("Storage access warning:", e);
  }
  return InterviewLifecycleState.IDLE;
}

/**
 * Sets lifecycle state in sessionStorage and dispatches a window event so all components update.
 */
export function setInterviewLifecycleState(state) {
  try {
    if (!Object.values(InterviewLifecycleState).includes(state)) {
      console.warn("Invalid interview lifecycle state:", state);
      return;
    }
    sessionStorage.setItem(STORAGE_KEY_LIFECYCLE, state);
    if (isStateProtected(state)) {
      sessionStorage.setItem(STORAGE_KEY_ACTIVE, "true");
    } else {
      sessionStorage.removeItem(STORAGE_KEY_ACTIVE);
    }
    // Notify all listeners across the window
    window.dispatchEvent(new CustomEvent("interviewLifecycleChange", { detail: { state } }));
  } catch (e) {
    console.warn("Storage write error:", e);
  }
}

/**
 * Returns true if navigation protection must be active.
 * Protected states: ACTIVE, PAUSED, SUBMITTING, FINALIZING, ENDING.
 * Unprotected states: IDLE, PREPARING, COMPLETED, ABORTED.
 */
export function isStateProtected(state) {
  return [
    InterviewLifecycleState.ACTIVE,
    InterviewLifecycleState.PAUSED,
    InterviewLifecycleState.SUBMITTING,
    InterviewLifecycleState.FINALIZING,
    InterviewLifecycleState.ENDING,
  ].includes(state);
}

/**
 * Convenience check: is an interview currently active and protected?
 */
export function isInterviewCurrentlyActive() {
  const state = getInterviewLifecycleState();
  return isStateProtected(state);
}

/**
 * Clears active interview protection state (called on complete or abort).
 */
export function clearInterviewActiveState() {
  try {
    sessionStorage.setItem(STORAGE_KEY_LIFECYCLE, InterviewLifecycleState.COMPLETED);
    sessionStorage.removeItem(STORAGE_KEY_ACTIVE);
    window.dispatchEvent(new CustomEvent("interviewLifecycleChange", {
      detail: { state: InterviewLifecycleState.COMPLETED }
    }));
  } catch (e) {
    console.warn("Error clearing interview state:", e);
  }
}
