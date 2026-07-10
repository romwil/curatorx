import { useState } from "react";

const STAR_VALUES = [1, 2, 3, 4, 5];

const DEFAULT_NEAR_COMPLETE_TEMPLATE =
  "{curator_name} noticed you're {pct}% through **{title}**. Quick rating while it's fresh?";

export function formatReviewPromptMessage(
  prompt,
  {
    curatorName = "Curator",
    template = DEFAULT_NEAR_COMPLETE_TEMPLATE,
    templateKey = "near_complete",
  } = {},
) {
  const pct = Math.round(prompt.completion_pct || 0);
  const resolvedTemplate =
    template ||
    DEFAULT_NEAR_COMPLETE_TEMPLATE;
  return resolvedTemplate
    .replaceAll("{curator_name}", curatorName)
    .replaceAll("{title}", prompt.title || "this title")
    .replaceAll("{pct}", String(pct))
    .replaceAll("{template_key}", templateKey);
}

export default function ReviewPromptCard({
  prompt,
  curatorName = "Curator",
  reviewPromptTemplates,
  sessionId,
  onSaved,
  onDismissed,
  disabled = false,
}) {
  const [stars, setStars] = useState(0);
  const [reviewText, setReviewText] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [plexConflict, setPlexConflict] = useState(null);

  const lead = formatReviewPromptMessage(prompt, {
    curatorName,
    template: reviewPromptTemplates?.near_complete,
  });

  async function handleSave(replacePlexRating = false) {
    if (!stars || saving || disabled) return;
    setSaving(true);
    setError("");
    try {
      await onSaved?.({
        prompt,
        stars,
        review_text: reviewText.trim(),
        session_id: sessionId,
        replace_plex_rating: replacePlexRating,
      });
      setPlexConflict(null);
      setSaving(false);
    } catch (err) {
      if (err?.code === "plex_rating_conflict") {
        setPlexConflict(err.conflict);
        setSaving(false);
        return;
      }
      setError(err?.message || "Could not save review");
      setSaving(false);
    }
  }

  async function handleKeepPlexRating() {
    setPlexConflict(null);
    setSaving(false);
    if (!String(prompt.id || "").startsWith("slash-rate-")) {
      await onDismissed?.(prompt);
    }
  }

  async function handleReplacePlexRating() {
    await handleSave(true);
  }

  async function handleSkip() {
    if (saving || disabled) return;
    setSaving(true);
    setError("");
    setPlexConflict(null);
    try {
      await onDismissed?.(prompt);
    } catch (err) {
      setError(err?.message || "Could not dismiss prompt");
      setSaving(false);
    }
  }

  return (
    <div className="review-prompt-card" data-testid="review-prompt-card">
      <p className="review-prompt-lead">{lead}</p>
      <div className="review-star-picker" role="group" aria-label={`Rate ${prompt.title}`}>
        {STAR_VALUES.map((value) => (
          <button
            key={value}
            type="button"
            className={`review-star-button ${stars >= value ? "selected" : ""}`}
            data-testid={`review-star-${value}`}
            aria-label={`${value} star${value === 1 ? "" : "s"}`}
            aria-pressed={stars >= value}
            disabled={saving || disabled}
            onClick={() => setStars(value)}
          >
            ★
          </button>
        ))}
      </div>
      <textarea
        className="review-prompt-text"
        data-testid="review-prompt-text"
        rows={2}
        placeholder="Optional: what landed or missed?"
        value={reviewText}
        disabled={saving || disabled}
        onChange={(event) => setReviewText(event.target.value)}
      />
      {plexConflict ? (
        <div className="review-plex-conflict" data-testid="review-plex-conflict">
          <p>
            Plex has {plexConflict.plex_stars}★ — keep or replace?
          </p>
          <div className="review-prompt-actions">
            <button
              type="button"
              className="ghost"
              data-testid="review-keep-plex-rating"
              disabled={saving || disabled}
              onClick={handleKeepPlexRating}
            >
              Keep Plex rating
            </button>
            <button
              type="button"
              className="primary"
              data-testid="review-replace-plex-rating"
              disabled={saving || disabled}
              onClick={handleReplacePlexRating}
            >
              Replace on Plex
            </button>
          </div>
        </div>
      ) : null}
      {error ? <p className="review-prompt-error">{error}</p> : null}
      {!plexConflict ? (
        <div className="review-prompt-actions">
          <button
            type="button"
            className="primary"
            data-testid="review-save-button"
            disabled={!stars || saving || disabled}
            onClick={() => handleSave(false)}
          >
            {saving ? "Saving…" : "Save review"}
          </button>
          <button
            type="button"
            className="ghost"
            data-testid="review-skip-button"
            disabled={saving || disabled}
            onClick={handleSkip}
          >
            Skip
          </button>
        </div>
      ) : null}
    </div>
  );
}

export function reviewPromptBlock(prompt) {
  return {
    type: "review_prompt",
    content: "",
    payload: { prompt },
  };
}
