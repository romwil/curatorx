const INTEGRATIONS = [
  { id: "plex", label: "Plex" },
  { id: "tmdb", label: "TMDB" },
  { id: "llm", label: "LLM" },
  { id: "radarr", label: "Radarr" },
  { id: "sonarr", label: "Sonarr" },
];

export default function IntegrationStatus({ checks }) {
  if (!checks) {
    return <p className="sidebar-muted">Loading integrations…</p>;
  }

  return (
    <ul className="integration-list" data-testid="integration-list">
      {INTEGRATIONS.map(({ id, label }) => {
        const check = checks[id];
        const ok = Boolean(check?.ok);
        return (
          <li key={id} className={`integration-item ${ok ? "ok" : "missing"}`}>
            <span className="integration-status-dot" aria-hidden="true" />
            <span className="integration-item-label">{label}</span>
            <span className="integration-item-state">{ok ? "Connected" : "Not set"}</span>
          </li>
        );
      })}
    </ul>
  );
}
