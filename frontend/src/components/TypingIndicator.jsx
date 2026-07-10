import { useMemo } from "react";

export default function TypingIndicator({ label = "Curator is thinking" }) {
  const displayLabel = useMemo(() => label, [label]);

  return (
    <div className="typing-indicator" aria-live="polite" data-testid="typing-indicator">
      <span className="typing-indicator-label">{displayLabel}</span>
      <span className="typing-indicator-dots" aria-hidden="true">
        <span className="typing-dot" />
        <span className="typing-dot" />
        <span className="typing-dot" />
      </span>
    </div>
  );
}
