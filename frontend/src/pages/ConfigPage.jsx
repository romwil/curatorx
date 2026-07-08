import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  createLens,
  getPersona,
  putPersona,
  putSystemConfig,
} from "../api/client";

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

const SERVICE_CARDS = [
  { id: "plex", label: "Plex", fields: ["plex_url", "plex_token"] },
  { id: "radarr", label: "Radarr", fields: ["radarr_url", "radarr_api_key"] },
  { id: "sonarr", label: "Sonarr", fields: ["sonarr_url", "sonarr_api_key"] },
  { id: "tmdb", label: "TMDB", fields: ["tmdb_api_key"] },
  { id: "tautulli", label: "Tautulli", fields: ["tautulli_url", "tautulli_api_key"] },
];

const PERSONA_FIELDS = [
  { key: "val_bro_prof", label: "Vocabulary", low: "Bro", high: "Professorial" },
  { key: "val_dipl_snark", label: "Interaction", low: "Diplomatic", high: "Snarky" },
  { key: "val_pass_auto", label: "Automation", low: "Passive", high: "Autonomous" },
];

function personaPreview(persona) {
  if (!persona) return "";
  const vocab = persona.val_bro_prof >= 0.6 ? "scholarly" : persona.val_bro_prof <= 0.4 ? "casual" : "balanced";
  const tone = persona.val_dipl_snark >= 0.6 ? "direct" : persona.val_dipl_snark <= 0.4 ? "diplomatic" : "measured";
  const auto = persona.val_pass_auto >= 0.6 ? "proactive" : persona.val_pass_auto <= 0.4 ? "advisory" : "collaborative";
  return `Hello, I'm ${persona.curator_name}. I'll curate your library with a ${vocab}, ${tone} voice and take a ${auto} approach to automation.`;
}

function slugify(text) {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export default function ConfigPage() {
  const [settings, setSettings] = useState(null);
  const [persona, setPersona] = useState(null);
  const [lenses, setLenses] = useState([]);
  const [status, setStatus] = useState("");
  const [sections, setSections] = useState([]);
  const [testing, setTesting] = useState(null);
  const [testResults, setTestResults] = useState({});
  const [newLens, setNewLens] = useState({ lens_id: "", lens_name: "", description: "" });
  const [savingPersona, setSavingPersona] = useState(false);

  useEffect(() => {
    Promise.all([api("/settings"), getPersona(), api("/lenses")]).then(([settingsData, personaData, lensData]) => {
      setSettings(settingsData);
      setPersona(personaData);
      setLenses(lensData);
    });
  }, []);

  const preview = useMemo(() => personaPreview(persona), [persona]);

  const hiddenKeys = new Set([
    ...SECRET_FIELDS,
    "onboarding_complete",
    "plex_url",
    "radarr_url",
    "sonarr_url",
    "tmdb_api_key",
    "tautulli_url",
  ]);

  async function saveSettings() {
    await api("/settings", { method: "PUT", body: JSON.stringify({ ...settings, onboarding_complete: true }) });
    setStatus("Settings saved.");
  }

  async function savePersonaField(field, value) {
    setSavingPersona(true);
    try {
      const payload = { [field]: value };
      const updated = await putPersona(payload);
      setPersona(updated);
      if (field === "curator_name") {
        await putSystemConfig({ curator_name: String(value) });
      }
      setStatus("Persona updated.");
    } catch (error) {
      setStatus(error.message);
    } finally {
      setSavingPersona(false);
    }
  }

  async function test(service) {
    setTesting(service);
    setTestResults((prev) => ({ ...prev, [service]: { state: "loading" } }));
    try {
      const result = await api(`/setup/test/${service}`, {
        method: "POST",
        body: JSON.stringify(settings),
      });
      setTestResults((prev) => ({
        ...prev,
        [service]: { state: result.ok ? "success" : "error", message: result.message },
      }));
      setStatus(result.message);
      if (result.sections) setSections(result.sections);
    } catch (error) {
      setTestResults((prev) => ({
        ...prev,
        [service]: { state: "error", message: error.message },
      }));
      setStatus(error.message);
    } finally {
      setTesting(null);
    }
  }

  async function handleCreateLens(event) {
    event.preventDefault();
    const lensId = newLens.lens_id.trim() || slugify(newLens.lens_name);
    if (!lensId || !newLens.lens_name.trim()) {
      setStatus("Lens name is required.");
      return;
    }
    try {
      const created = await createLens({
        lens_id: lensId,
        lens_name: newLens.lens_name.trim(),
        description: newLens.description.trim(),
      });
      setLenses((prev) => [...prev, created]);
      setNewLens({ lens_id: "", lens_name: "", description: "" });
      setStatus(`Created lens "${created.lens_name}".`);
    } catch (error) {
      setStatus(error.message);
    }
  }

  if (!settings || !persona) return <p>Loading settings…</p>;

  return (
    <div className="config-page">
      <header className="topbar">
        <div>
          <p className="eyebrow">Configuration</p>
          <h1>Sovereign curator setup</h1>
        </div>
        <Link to="/" className="btn-link">
          Back to chat
        </Link>
      </header>

      <section className="config-section sovereign-section">
        <h2>Sovereign identity</h2>
        <label className="sovereign-field">
          <span>Curator name</span>
          <input
            type="text"
            value={persona.curator_name}
            disabled={savingPersona}
            onChange={(event) => setPersona({ ...persona, curator_name: event.target.value })}
            onBlur={(event) => savePersonaField("curator_name", event.target.value)}
          />
        </label>
        <p className="persona-preview">{preview}</p>
      </section>

      <section className="config-section">
        <h2>Behavioral tuning</h2>
        <div className="slider-grid">
          {PERSONA_FIELDS.map(({ key, label, low, high }) => (
            <label key={key} className="slider-field">
              <div className="slider-labels">
                <span>{label}</span>
                <span className="slider-value">{persona[key].toFixed(2)}</span>
              </div>
              <div className="slider-range-labels">
                <span>{low}</span>
                <span>{high}</span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={persona[key]}
                onChange={(event) =>
                  setPersona({ ...persona, [key]: Number(event.target.value) })
                }
                onMouseUp={(event) => savePersonaField(key, Number(event.target.value))}
                onTouchEnd={(event) => savePersonaField(key, Number(event.target.value))}
              />
            </label>
          ))}
        </div>
      </section>

      <section className="config-section">
        <h2>Service integrations</h2>
        <div className="service-cards">
          {SERVICE_CARDS.map(({ id, label, fields }) => {
            const result = testResults[id];
            const cardClass = [
              "service-card",
              result?.state === "success" ? "service-ok" : "",
              result?.state === "error" ? "service-error" : "",
              testing === id ? "service-loading" : "",
            ]
              .filter(Boolean)
              .join(" ");
            return (
              <div key={id} className={cardClass}>
                <div className="service-card-header">
                  <h3>{label}</h3>
                  <button type="button" onClick={() => test(id)} disabled={testing === id}>
                    {testing === id ? "Testing…" : "Test connection"}
                  </button>
                </div>
                <div className="service-fields">
                  {fields.map((field) => (
                    <label key={field}>
                      <span>{field}</span>
                      <input
                        type={SECRET_FIELDS.includes(field) ? "password" : "text"}
                        value={settings[field] ?? ""}
                        disabled={testing === id}
                        onChange={(event) =>
                          setSettings({ ...settings, [field]: event.target.value })
                        }
                      />
                    </label>
                  ))}
                </div>
                {result?.message ? <p className="service-message">{result.message}</p> : null}
              </div>
            );
          })}
        </div>
      </section>

      <section className="config-section">
        <h2>Curation lenses</h2>
        <ul className="lens-list">
          {lenses.map((lens) => (
            <li key={lens.lens_id}>
              <strong>{lens.lens_name}</strong>
              <span className="lens-id">{lens.lens_id}</span>
              {lens.description ? <p>{lens.description}</p> : null}
            </li>
          ))}
        </ul>
        <form className="lens-create-form" onSubmit={handleCreateLens}>
          <label>
            <span>Lens name</span>
            <input
              type="text"
              value={newLens.lens_name}
              onChange={(event) =>
                setNewLens({
                  ...newLens,
                  lens_name: event.target.value,
                  lens_id: newLens.lens_id || slugify(event.target.value),
                })
              }
              placeholder="Director Studies"
            />
          </label>
          <label>
            <span>Lens ID</span>
            <input
              type="text"
              value={newLens.lens_id}
              onChange={(event) => setNewLens({ ...newLens, lens_id: event.target.value })}
              placeholder="director-studies"
            />
          </label>
          <label>
            <span>Description</span>
            <input
              type="text"
              value={newLens.description}
              onChange={(event) => setNewLens({ ...newLens, description: event.target.value })}
              placeholder="Optional context for this lens"
            />
          </label>
          <button type="submit">Create lens</button>
        </form>
      </section>

      <section className="config-section">
        <h2>Advanced settings</h2>
        <div className="config-grid">
          {Object.entries(settings)
            .filter(([key]) => !key.endsWith("_set") && !hiddenKeys.has(key))
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
          <button type="button" onClick={saveSettings}>
            Save settings
          </button>
        </div>
      </section>

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
