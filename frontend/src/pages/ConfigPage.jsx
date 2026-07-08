import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";

const SECRET_FIELDS = [
  "plex_token",
  "radarr_api_key",
  "sonarr_api_key",
  "tmdb_api_key",
  "tvdb_api_key",
  "fanart_api_key",
  "tautulli_api_key",
  "llm_api_key",
];

export default function ConfigPage() {
  const [settings, setSettings] = useState(null);
  const [status, setStatus] = useState("");
  const [sections, setSections] = useState([]);

  useEffect(() => {
    api("/settings").then(setSettings);
  }, []);

  async function save() {
    await api("/settings", { method: "PUT", body: JSON.stringify({ ...settings, onboarding_complete: true }) });
    setStatus("Saved.");
  }

  async function test(service) {
    const payload = settings;
    const result = await api(`/setup/test/${service}`, { method: "POST", body: JSON.stringify(payload) });
    setStatus(result.message);
    if (result.sections) setSections(result.sections);
  }

  if (!settings) return <p>Loading settings…</p>;

  return (
    <div className="config-page">
      <header className="topbar">
        <div>
          <p className="eyebrow">Configuration</p>
          <h1>Connect your media stack</h1>
        </div>
        <Link to="/" className="btn-link">
          Back to chat
        </Link>
      </header>

      <div className="config-grid">
        {Object.entries(settings)
          .filter(([key]) => !key.endsWith("_set"))
          .map(([key, value]) => (
            <label key={key}>
              <span>{key}</span>
              <input
                type={SECRET_FIELDS.includes(key) ? "password" : "text"}
                value={typeof value === "boolean" ? String(value) : value ?? ""}
                onChange={(event) =>
                  setSettings({
                    ...settings,
                    [key]:
                      typeof value === "boolean"
                        ? event.target.value === "true"
                        : key.endsWith("_id") || key.endsWith("_hours") || key === "tv_page_size"
                          ? Number(event.target.value || 0)
                          : event.target.value,
                  })
                }
              />
            </label>
          ))}
      </div>

      <div className="config-actions">
        <button type="button" onClick={() => test("plex")}>
          Test Plex
        </button>
        <button type="button" onClick={() => test("radarr")}>
          Test Radarr
        </button>
        <button type="button" onClick={() => test("sonarr")}>
          Test Sonarr
        </button>
        <button type="button" onClick={() => test("tmdb")}>
          Test TMDB
        </button>
        <button type="button" onClick={() => test("tautulli")}>
          Test Tautulli
        </button>
        <button type="button" onClick={save}>
          Save settings
        </button>
      </div>

      {sections.length ? (
        <div className="plex-sections">
          <h3>Plex libraries</h3>
          {sections.map((section) => (
            <button
              key={section.key}
              type="button"
              onClick={() =>
                setSettings({
                  ...settings,
                  ...(section.type === "movie" ? { plex_movie_section: section.key } : {}),
                  ...(section.type === "show" ? { plex_tv_section: section.key } : {}),
                })
              }
            >
              Use {section.title} ({section.type}) — key {section.key}
            </button>
          ))}
        </div>
      ) : null}

      {status ? <p className="status">{status}</p> : null}
    </div>
  );
}
