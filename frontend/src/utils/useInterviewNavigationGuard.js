/**
 * frontend/src/utils/useInterviewNavigationGuard.js
 * 
 * Reusable hook to protect active interview routes against:
 * 1. Browser Back button (popstate event interception)
 * 2. Window / tab refresh and closure (beforeunload)
 * 3. In-app navigation links
 * 
 * Guarantees:
 * - When interview is ACTIVE, popstate is caught, preventing accidental exit.
 * - History state is managed idempotently without pushing hundreds of history entries.
 * - Shows an in-app confirmation modal.
 * - When COMPLETED, guards are removed automatically.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { InterviewLifecycleState, isStateProtected } from "./interviewLifecycle";

export function useInterviewNavigationGuard({
  lifecycleState,
  onEndInterview,
}) {
  const [showLeaveModal, setShowLeaveModal] = useState(false);
  const [leaveModalConfig, setLeaveModalConfig] = useState({
    title: "You're still in an active interview.",
    message: "Leaving now will interrupt your interview session.",
    confirmLabel: "End Interview",
    cancelLabel: "Stay in Interview",
    pendingAction: null,
  });

  const isProtected = isStateProtected(lifecycleState);
  const historyPushedRef = useRef(false);

  // 1. Browser Back Button Guard via HTML5 History & popstate
  useEffect(() => {
    if (!isProtected) {
      historyPushedRef.current = false;
      return;
    }

    // Push a single guard state to intercept the back button
    if (!historyPushedRef.current) {
      window.history.pushState({ interviewGuard: true }, "", window.location.href);
      historyPushedRef.current = true;
    }

    const handlePopState = (event) => {
      // User clicked Back button while interview is active!
      // Immediately restore history state to stay on the interview route
      window.history.pushState({ interviewGuard: true }, "", window.location.href);

      // Trigger in-app confirmation modal
      setLeaveModalConfig({
        title: "You're still in an active interview.",
        message: "Leaving now will interrupt your interview session.",
        confirmLabel: "End Interview",
        cancelLabel: "Stay in Interview",
        pendingAction: async () => {
          if (onEndInterview) {
            await onEndInterview();
          }
        },
      });
      setShowLeaveModal(true);
    };

    window.addEventListener("popstate", handlePopState);
    return () => {
      window.removeEventListener("popstate", handlePopState);
    };
  }, [isProtected, onEndInterview]);

  // 2. BeforeUnload Listener for Tab Close / Refresh
  useEffect(() => {
    if (!isProtected) return;

    const handleBeforeUnload = (e) => {
      // Standard browser leave-page warning
      e.preventDefault();
      e.returnValue = "Your interview session is active. Are you sure you want to leave?";
      return e.returnValue;
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, [isProtected]);

  // Handlers for modal
  const handleStay = useCallback(() => {
    setShowLeaveModal(false);
  }, []);

  const handleConfirmLeave = useCallback(async () => {
    setShowLeaveModal(false);
    if (leaveModalConfig.pendingAction) {
      await leaveModalConfig.pendingAction();
    } else if (onEndInterview) {
      await onEndInterview();
    }
  }, [leaveModalConfig, onEndInterview]);

  // Function for external links (e.g. Navbar) to request navigation confirmation
  const requestNavigation = useCallback((action, customMessage) => {
    if (!isProtected) {
      action();
      return;
    }
    setLeaveModalConfig({
      title: customMessage?.title || "Your interview is still in progress.",
      message: customMessage?.message || "Leave the interview and end this session?",
      confirmLabel: customMessage?.confirmLabel || "End Interview",
      cancelLabel: customMessage?.cancelLabel || "Stay",
      pendingAction: action,
    });
    setShowLeaveModal(true);
  }, [isProtected]);

  return {
    showLeaveModal,
    leaveModalConfig,
    handleStay,
    handleConfirmLeave,
    requestNavigation,
  };
}
