export default function InlineAlert({ type, message, testId }) {
  if (!message || (type !== "success" && type !== "error")) return null;
  return (
    <div
      className={`inline-alert inline-alert-${type}`}
      role="alert"
      data-testid={testId || `inline-alert-${type}`}
    >
      {message}
    </div>
  );
}
