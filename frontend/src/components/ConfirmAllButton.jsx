export default function ConfirmAllButton({ count, target, onClick, disabled = false, variant }) {
  if (count < 2) return null;

  const resolvedVariant = variant || (target ? target : "tokens");
  const label =
    resolvedVariant === "tokens"
      ? `Confirm all ${count} adds`
      : resolvedVariant === "seerr"
        ? `Confirm all ${count} in Seerr`
        : resolvedVariant === "sonarr"
          ? `Confirm all ${count} to Sonarr`
          : `Confirm all ${count} to Radarr`;

  return (
    <button
      type="button"
      className="confirm-all-button"
      data-testid={resolvedVariant === "tokens" ? "confirm-all-tokens" : `confirm-all-${resolvedVariant}`}
      onClick={onClick}
      disabled={disabled}
    >
      {label}
    </button>
  );
}
