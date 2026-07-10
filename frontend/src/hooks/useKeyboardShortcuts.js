import { useEffect } from "react";

function isEditableTarget(target) {
  if (!target) return false;
  const tag = target.tagName?.toLowerCase();
  return tag === "input" || tag === "textarea" || target.isContentEditable;
}

export default function useKeyboardShortcuts({
  composerRef,
  onNewThread,
  onCloseOverlay,
  onShowHelp,
  overlayOpen = false,
}) {
  useEffect(() => {
    function handleKeyDown(event) {
      const target = event.target;
      const inEditable = isEditableTarget(target);
      const key = event.key;

      if (key === "Escape" && overlayOpen) {
        event.preventDefault();
        onCloseOverlay?.();
        return;
      }

      if (key === "?" && !inEditable && !event.metaKey && !event.ctrlKey && !event.altKey) {
        event.preventDefault();
        onShowHelp?.();
        return;
      }

      if ((event.metaKey || event.ctrlKey) && key.toLowerCase() === "n") {
        event.preventDefault();
        onNewThread?.();
        return;
      }

      if (key === "/" && !inEditable && !event.metaKey && !event.ctrlKey && !event.altKey) {
        event.preventDefault();
        composerRef?.current?.focus();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [composerRef, onNewThread, onCloseOverlay, onShowHelp, overlayOpen]);
}
