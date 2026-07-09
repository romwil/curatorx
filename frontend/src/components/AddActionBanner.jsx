export default function AddActionBanner({
  pendingAdd,
  pendingBulk,
  pendingTokens,
  inProgress,
  progress,
  onConfirm,
  onCancel,
}) {
  if (pendingBulk) {
    const { items, target } = pendingBulk;
    const service = target === "sonarr" ? "Sonarr" : "Radarr";
    const count = items.length;
    const progressLabel =
      inProgress && progress?.total
        ? `Adding ${Math.min(progress.current, progress.total)} of ${progress.total}…`
        : null;

    return (
      <div className="add-action-banner" data-testid="bulk-add-banner" role="alertdialog" aria-modal="true">
        <p data-testid="bulk-add-prompt">
          Add all <strong>{count}</strong> titles to {service}?
        </p>
        {progressLabel ? <p className="bulk-add-progress">{progressLabel}</p> : null}
        <div className="add-action-buttons">
          <button type="button" data-testid="bulk-add-confirm" onClick={onConfirm} disabled={inProgress}>
            {inProgress ? "Adding…" : `Confirm all ${count}`}
          </button>
          <button type="button" className="ghost" data-testid="bulk-add-cancel" onClick={onCancel} disabled={inProgress}>
            Cancel
          </button>
        </div>
      </div>
    );
  }

  if (pendingTokens?.length) {
    const count = pendingTokens.length;
    const progressLabel =
      inProgress && progress?.total
        ? `Confirming ${Math.min(progress.current, progress.total)} of ${progress.total}…`
        : null;

    return (
      <div className="add-action-banner" data-testid="token-confirm-banner" role="alertdialog" aria-modal="true">
        <p data-testid="token-confirm-prompt">
          Confirm all <strong>{count}</strong> proposed adds?
        </p>
        {progressLabel ? <p className="bulk-add-progress">{progressLabel}</p> : null}
        <div className="add-action-buttons">
          <button type="button" data-testid="token-confirm-all" onClick={onConfirm} disabled={inProgress}>
            {inProgress ? "Confirming…" : `Confirm all ${count}`}
          </button>
          <button type="button" className="ghost" data-testid="token-confirm-cancel" onClick={onCancel} disabled={inProgress}>
            Cancel
          </button>
        </div>
      </div>
    );
  }

  if (!pendingAdd) return null;

  const { item, target } = pendingAdd;
  const label = item.title || "this title";
  const service = target === "sonarr" ? "Sonarr" : "Radarr";

  return (
    <div className="add-action-banner" data-testid="add-action-banner" role="alertdialog" aria-modal="true">
      <p data-testid="add-action-prompt">
        Add <strong>{label}</strong> to {service}?
      </p>
      <div className="add-action-buttons">
        <button
          type="button"
          data-testid="add-action-confirm"
          onClick={onConfirm}
          disabled={inProgress}
        >
          {inProgress ? "Adding…" : `Add to ${service}`}
        </button>
        <button type="button" className="ghost" data-testid="add-action-cancel" onClick={onCancel} disabled={inProgress}>
          Cancel
        </button>
      </div>
    </div>
  );
}
