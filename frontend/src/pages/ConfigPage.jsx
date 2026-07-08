import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  AUTO_CERTIFY_SERVICES,
  ANTHROPIC_MODEL_OPTIONS,
  LLM_MODEL_DEFAULTS,
  LLM_PROVIDER_DEFAULTS,
  LLM_PROVIDER_OPTIONS,
  WIZARD_STEPS,
  api,
  createLens,
  getPersona,
  getSettings,
  getWizardStatus,
  putPersona,
  putSystemConfig,
  resolveModelForProvider,
  saveSettings,
  testService,
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

function secretPlaceholder(settings, field, fallback = "") {
  if (settings?.[`${field}_source`] === "env") {
    return "Configured via environment (.env)";
  }
  if (settings?.[`${field}_set`]) {
    return "Configured (leave blank to keep)";
  }
  return fallback;
}

function SecretInput({
  field,
  settings,
  value,
  onChange,
  disabled = false,
  placeholder = "",
  visible = false,
  onToggleVisible,
}) {
  return (
    <div className="secret-field">
      <input
        type={visible ? "text" : "password"}
        value={value ?? ""}
        disabled={disabled}
        placeholder={placeholder || secretPlaceholder(settings, field)}
        onChange={onChange}
        autoComplete="off"
      />
      <button
        type="button"
        className="secret-toggle"
        aria-label={visible ? "Hide secret" : "Show secret"}
        aria-pressed={visible}
        disabled={disabled}
        onClick={onToggleVisible}
      >
        {visible ? "Hide" : "Show"}
      </button>
    </div>
  );
}

function InlineAlert({ type, message }) {
  if (!message || (type !== "success" && type !== "error")) return null;
  return (
    <div className={`inline-alert inline-alert-${type}`} role="alert">
      {message}
    </div>
  );
}

function CertifiedBadge({ certified, testing }) {
  if (testing) {
    return <span className="certified-badge certified-badge-testing">Testing…</span>;
  }
  if (certified) {
    return <span className="certified-badge certified-badge-ok">Certified ✓</span>;
  }
  return <span className="certified-badge certified-badge-pending">Uncertified</span>;
}

function serviceCredentialsPresent(service, settings) {
  if (!settings) return false;
  switch (service) {
    case "llm":
      return Boolean(
        settings.llm_model &&
          (settings.llm_provider === "ollama" || settings.llm_api_key_set),
      );
    case "plex":
      return Boolean(settings.plex_url && settings.plex_token_set);
    case "radarr":
      return Boolean(settings.radarr_url && settings.radarr_api_key_set);
    case "sonarr":
      return Boolean(settings.sonarr_url && settings.sonarr_api_key_set);
    case "tmdb":
      return Boolean(settings.tmdb_api_key_set);
    case "fanart":
      return Boolean(settings.fanart_api_key_set);
    case "tautulli":
      return Boolean(settings.tautulli_url && settings.tautulli_api_key_set);
    default:
      return false;
  }
}

function ProviderSelect({ value, onChange }) {
  return (
    <select value={value || "openai"} onChange={onChange}>
      {LLM_PROVIDER_OPTIONS.map(({ value: providerValue, label }) => (
        <option key={providerValue} value={providerValue}>
          {label}
        </option>
      ))}
    </select>
  );
}

const STEP_LABELS = {
  identity_llm: "Identity & LLM",
  media_core: "Media Core",
  automation: "Automation",
  persona: "Persona",
  optional_services: "Optional Services",
};

const PERSONA_FIELDS = [
  { key: "val_bro_prof", label: "Vocabulary", low: "Bro", high: "Professorial" },
  { key: "val_dipl_snark", label: "Interaction", low: "Diplomatic", high: "Snarky" },
  { key: "val_pass_auto", label: "Automation", low: "Passive", high: "Autonomous" },
];

const OPTIONAL_SERVICES = [
  { id: "tmdb", label: "TMDB", fields: ["tmdb_api_key"] },
  { id: "fanart", label: "Fanart.tv", fields: ["fanart_api_key"] },
  { id: "tautulli", label: "Tautulli", fields: ["tautulli_url", "tautulli_api_key"] },
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

function stepUnlocked(stepIndex, verification) {
  if (stepIndex === 0) return true;
  if (stepIndex === 1) return verification.llm;
  if (stepIndex === 2) return verification.llm && verification.plex && verification.sections;
  if (stepIndex === 3) return verification.llm && verification.plex && verification.sections && verification.radarr && verification.sonarr;
  if (stepIndex === 4) return verification.llm && verification.plex && verification.sections && verification.radarr && verification.sonarr;
  return false;
}

function canAdvance(stepIndex, verification) {
  if (stepIndex === 0) return verification.llm;
  if (stepIndex === 1) return verification.plex && verification.sections;
  if (stepIndex === 2) return verification.radarr && verification.sonarr;
  if (stepIndex === 3) return true;
  if (stepIndex === 4) return true;
  return false;
}

export default function ConfigPage() {
  const navigate = useNavigate();
  const [settings, setSettings] = useState(null);
  const [persona, setPersona] = useState(null);
  const [lenses, setLenses] = useState([]);
  const [wizard, setWizard] = useState(null);
  const [status, setStatus] = useState("");
  const [actionAlert, setActionAlert] = useState(null);
  const [footerAlert, setFooterAlert] = useState(null);
  const [sections, setSections] = useState([]);
  const [testing, setTesting] = useState(null);
  const [testResults, setTestResults] = useState({});
  const [certifications, setCertifications] = useState({});
  const [autoCertifying, setAutoCertifying] = useState(false);
  const [autoCertifyDone, setAutoCertifyDone] = useState(false);
  const [verification, setVerification] = useState({
    llm: false,
    plex: false,
    sections: false,
    radarr: false,
    sonarr: false,
  });
  const [stepIndex, setStepIndex] = useState(0);
  const [showWizard, setShowWizard] = useState(true);
  const [onboardingHints, setOnboardingHints] = useState([]);
  const [newLens, setNewLens] = useState({ lens_id: "", lens_name: "", description: "" });
  const [savingPersona, setSavingPersona] = useState(false);
  const [plexCollapsed, setPlexCollapsed] = useState(false);
  const [visibleSecrets, setVisibleSecrets] = useState({});

  const preview = useMemo(() => personaPreview(persona), [persona]);
  const movieSections = useMemo(() => sections.filter((s) => s.type === "movie"), [sections]);
  const tvSections = useMemo(() => sections.filter((s) => s.type === "show"), [sections]);

  function applyCertifications(certMap) {
    setCertifications(certMap || {});
    const initialResults = {};
    for (const [service, cert] of Object.entries(certMap || {})) {
      if (cert?.certified) {
        initialResults[service] = { state: "success", message: "Certified" };
      }
    }
    if (Object.keys(initialResults).length) {
      setTestResults((prev) => ({ ...initialResults, ...prev }));
    }
    setVerification((prev) => ({
      ...prev,
      llm: certMap?.llm?.certified || prev.llm,
      plex: certMap?.plex?.certified || prev.plex,
      radarr: certMap?.radarr?.certified || prev.radarr,
      sonarr: certMap?.sonarr?.certified || prev.sonarr,
    }));
  }

  async function refreshWizard() {
    const wizardData = await getWizardStatus();
    setWizard(wizardData);
    if (wizardData.certifications) {
      applyCertifications(wizardData.certifications);
    }
    if (wizardData.onboarding_complete) {
      setShowWizard(false);
    }
    setVerification((prev) => ({
      ...prev,
      llm: wizardData.steps.identity_llm.llm_verified || prev.llm,
      plex: wizardData.steps.media_core.plex_verified || prev.plex,
      sections: wizardData.steps.media_core.sections_set || prev.sections,
      radarr: wizardData.steps.automation.radarr_verified || prev.radarr,
      sonarr: wizardData.steps.automation.sonarr_verified || prev.sonarr,
    }));
    if (!wizardData.onboarding_complete && wizardData.current_step >= 0) {
      setStepIndex(Math.min(wizardData.current_step, WIZARD_STEPS.length - 1));
    }
  }

  useEffect(() => {
    Promise.all([getSettings(), getPersona(), api("/lenses"), getWizardStatus()]).then(
      ([settingsData, personaData, lensData, wizardData]) => {
        const normalizedModel = resolveModelForProvider(
          settingsData.llm_provider,
          settingsData.llm_model,
        );
        setSettings(
          normalizedModel === settingsData.llm_model
            ? settingsData
            : { ...settingsData, llm_model: normalizedModel },
        );
        setPersona(personaData);
        setLenses(lensData);
        setWizard(wizardData);
        setShowWizard(!wizardData.onboarding_complete);
        if (wizardData.certifications) {
          applyCertifications(wizardData.certifications);
        }
        setVerification({
          llm: wizardData.certifications?.llm?.certified || wizardData.steps.identity_llm.llm_verified,
          plex: wizardData.certifications?.plex?.certified || wizardData.steps.media_core.plex_verified,
          sections: wizardData.steps.media_core.sections_set,
          radarr: wizardData.certifications?.radarr?.certified || wizardData.steps.automation.radarr_verified,
          sonarr: wizardData.certifications?.sonarr?.certified || wizardData.steps.automation.sonarr_verified,
        });
        if (!wizardData.onboarding_complete) {
          setStepIndex(Math.min(wizardData.current_step, WIZARD_STEPS.length - 1));
        }
      },
    );
  }, []);

  useEffect(() => {
    if (!settings || autoCertifyDone || autoCertifying) return;

    const pending = AUTO_CERTIFY_SERVICES.filter(
      (service) =>
        !certifications[service]?.certified && serviceCredentialsPresent(service, settings),
    );
    if (!pending.length) {
      setAutoCertifyDone(true);
      return;
    }

    let cancelled = false;

    async function autoCertify() {
      setAutoCertifying(true);
      for (const service of pending) {
        if (cancelled) break;
        await runTest(service, { silent: true });
        await new Promise((resolve) => setTimeout(resolve, 300));
      }
      if (!cancelled) {
        setAutoCertifyDone(true);
        setAutoCertifying(false);
      }
    }

    autoCertify();
    return () => {
      cancelled = true;
    };
  }, [settings, certifications, autoCertifyDone, autoCertifying]);

  useEffect(() => {
    if (!settings) return;
    const sectionsSet = Boolean(settings.plex_movie_section && settings.plex_tv_section);
    setVerification((prev) => ({ ...prev, sections: sectionsSet || prev.sections }));
  }, [settings?.plex_movie_section, settings?.plex_tv_section]);

  function updateSettings(patch) {
    setSettings((prev) => ({ ...prev, ...patch }));
  }

  function toggleSecretVisibility(field) {
    setVisibleSecrets((prev) => ({ ...prev, [field]: !prev[field] }));
  }

  function renderSecretInput(field, options = {}) {
    return (
      <SecretInput
        field={field}
        settings={settings}
        value={settings[field] ?? ""}
        disabled={options.disabled}
        placeholder={options.placeholder}
        visible={Boolean(visibleSecrets[field])}
        onToggleVisible={() => toggleSecretVisibility(field)}
        onChange={(event) => updateSettings({ [field]: event.target.value })}
      />
    );
  }

  function setActionFeedback(area, type, message) {
    setActionAlert({ area, type, message });
    setStatus(message);
  }

  function clearActionFeedback(area) {
    setActionAlert((prev) => (prev?.area === area ? null : prev));
  }

  function handleProviderChange(provider) {
    const defaultUrl = LLM_PROVIDER_DEFAULTS[provider] ?? "";
    const nextModel = resolveModelForProvider(provider, settings.llm_model);
    updateSettings({
      llm_provider: provider,
      llm_base_url: defaultUrl,
      llm_model: nextModel,
    });
    clearActionFeedback("llm");
  }

  async function persistSettings(patch = {}, options = {}) {
    const payload = { ...settings, ...patch };
    const saved = await saveSettings(payload);
    setSettings({ ...payload, ...saved });
    if (options.refreshWizard) await refreshWizard();
    return saved;
  }

  async function savePersonaField(field, value) {
    setSavingPersona(true);
    try {
      const updated = await putPersona({ [field]: value });
      setPersona(updated);
      if (field === "curator_name") {
        await putSystemConfig({ curator_name: String(value) });
      }
      setActionFeedback("persona", "success", "Persona updated.");
    } catch (error) {
      setActionFeedback("persona", "error", error.message);
    } finally {
      setSavingPersona(false);
    }
  }

  async function runTest(service, options = {}) {
    const { silent = false } = options;
    setTesting(service);
    setTestResults((prev) => ({ ...prev, [service]: { state: "loading" } }));
    if (!silent) clearActionFeedback(service);
    try {
      const result = await testService(service, settings);
      setTestResults((prev) => ({
        ...prev,
        [service]: {
          state: result.ok ? "success" : "error",
          message: result.message,
          version: result.version,
          movie_count: result.movie_count,
          series_count: result.series_count,
        },
      }));
      if (!silent) {
        setActionFeedback(service, result.ok ? "success" : "error", result.message);
      }
      if (result.sections) {
        setSections(result.sections);
        setPlexCollapsed(true);
      }
      if (result.hints) setOnboardingHints(result.hints);
      else if (result.hint) setOnboardingHints([result.hint]);

      setCertifications((prev) => ({
        ...prev,
        [service]: {
          ...(prev[service] || {}),
          certified: Boolean(result.ok),
          connection_status: result.ok ? "verified" : "failed",
        },
      }));

      if (result.ok) {
        const keyMap = {
          llm: "llm",
          plex: "plex",
          radarr: "radarr",
          sonarr: "sonarr",
        };
        if (keyMap[service]) {
          setVerification((prev) => ({ ...prev, [keyMap[service]]: true }));
        }
        await refreshWizard();
      }
    } catch (error) {
      setTestResults((prev) => ({
        ...prev,
        [service]: { state: "error", message: error.message },
      }));
      if (!silent) {
        setActionFeedback(service, "error", error.message);
      }
      setCertifications((prev) => ({
        ...prev,
        [service]: {
          ...(prev[service] || {}),
          certified: false,
          connection_status: "failed",
        },
      }));
    } finally {
      setTesting(null);
    }
  }

  async function handleNext() {
    setFooterAlert(null);
    try {
      await persistSettings({}, { refreshWizard: true });
      if (stepIndex < WIZARD_STEPS.length - 1) {
        setStepIndex((prev) => prev + 1);
      }
      setFooterAlert({ type: "success", message: "Step saved." });
      setStatus("Step saved.");
    } catch (error) {
      setFooterAlert({ type: "error", message: error.message });
      setStatus(error.message);
    }
  }

  async function handleFinish() {
    setFooterAlert(null);
    try {
      await persistSettings({ onboarding_complete: true });
      setShowWizard(false);
      const message = "Onboarding complete. Welcome to CuratorX.";
      setFooterAlert({ type: "success", message });
      setStatus(message);
      navigate("/");
    } catch (error) {
      setFooterAlert({ type: "error", message: error.message });
      setStatus(error.message);
    }
  }

  async function handleCreateLens(event) {
    event.preventDefault();
    const lensId = newLens.lens_id.trim() || slugify(newLens.lens_name);
    if (!lensId || !newLens.lens_name.trim()) {
      setActionFeedback("lens", "error", "Lens name is required.");
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
      setActionFeedback("lens", "success", `Created lens "${created.lens_name}".`);
    } catch (error) {
      setActionFeedback("lens", "error", error.message);
    }
  }

  async function handleSaveSettings() {
    clearActionFeedback("save");
    try {
      await persistSettings();
      setActionFeedback("save", "success", "Settings saved.");
    } catch (error) {
      setActionFeedback("save", "error", error.message);
    }
  }

  if (!settings || !persona || !wizard) return <p>Loading settings…</p>;

  const currentStep = WIZARD_STEPS[stepIndex];

  function renderWizardStep() {
    if (currentStep === "identity_llm") {
      const llmResult = testResults.llm;
      return (
        <section className="wizard-panel">
          <h2>Step 1 — Sovereign identity &amp; LLM engine</h2>
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

          <div className="wizard-fields">
            <label>
              <span>LLM provider</span>
              <ProviderSelect
                value={settings.llm_provider}
                onChange={(event) => handleProviderChange(event.target.value)}
              />
            </label>
            <label>
              <span>Base URL</span>
              <input
                type="text"
                value={settings.llm_base_url ?? ""}
                onChange={(event) => updateSettings({ llm_base_url: event.target.value })}
                placeholder={LLM_PROVIDER_DEFAULTS[settings.llm_provider] || "https://api.openai.com/v1"}
              />
            </label>
            <label>
              <span>API key</span>
              {renderSecretInput("llm_api_key", {
                placeholder: secretPlaceholder(
                  settings,
                  "llm_api_key",
                  "Required except for Ollama",
                ),
              })}
            </label>
            <label>
              <span>Model</span>
              <input
                type="text"
                list={settings.llm_provider === "anthropic" ? "anthropic-model-options" : undefined}
                value={settings.llm_model ?? ""}
                onChange={(event) => updateSettings({ llm_model: event.target.value })}
                placeholder={LLM_MODEL_DEFAULTS[settings.llm_provider] || "gpt-4o-mini, claude-sonnet-4-6"}
              />
              {settings.llm_provider === "anthropic" ? (
                <datalist id="anthropic-model-options">
                  {ANTHROPIC_MODEL_OPTIONS.map((model) => (
                    <option key={model} value={model} />
                  ))}
                </datalist>
              ) : null}
            </label>
          </div>

          <div className="wizard-actions">
            <button type="button" onClick={() => runTest("llm")} disabled={testing === "llm"}>
              {testing === "llm" ? "Verifying…" : "Verify LLM connection"}
            </button>
            <CertifiedBadge certified={certifications.llm?.certified} testing={testing === "llm"} />
          </div>
          <InlineAlert
            type={actionAlert?.area === "llm" ? actionAlert.type : llmResult?.state}
            message={actionAlert?.area === "llm" ? actionAlert.message : llmResult?.message}
          />

          {onboardingHints.length ? (
            <div className="onboarding-assistant">
              <h3>Onboarding assistant</h3>
              <div className="onboarding-hints">
                {onboardingHints.map((hint) => (
                  <p key={hint}>{hint}</p>
                ))}
              </div>
            </div>
          ) : null}
        </section>
      );
    }

    if (currentStep === "media_core") {
      const plexResult = testResults.plex;
      return (
        <section className="wizard-panel">
          <h2>Step 2 — Media infrastructure (Plex)</h2>
          {!plexCollapsed ? (
            <div className="wizard-fields">
              <label>
                <span>Plex URL</span>
                <input
                  type="text"
                  value={settings.plex_url ?? ""}
                  onChange={(event) => updateSettings({ plex_url: event.target.value })}
                />
              </label>
              <label>
                <span>Plex token</span>
                {renderSecretInput("plex_token")}
              </label>
            </div>
          ) : (
            <button type="button" className="ghost" onClick={() => setPlexCollapsed(false)}>
              Edit Plex credentials
            </button>
          )}
          <div className="wizard-actions">
            <button type="button" onClick={() => runTest("plex")} disabled={testing === "plex"}>
              {testing === "plex" ? "Verifying…" : "Verify integration"}
            </button>
            <CertifiedBadge certified={certifications.plex?.certified} testing={testing === "plex"} />
          </div>
          <InlineAlert
            type={actionAlert?.area === "plex" ? actionAlert.type : plexResult?.state}
            message={actionAlert?.area === "plex" ? actionAlert.message : plexResult?.message}
          />

          {verification.plex && sections.length ? (
            <div className="section-dropdowns">
              <label>
                <span>Movie section</span>
                <select
                  value={settings.plex_movie_section ?? ""}
                  onChange={(event) => updateSettings({ plex_movie_section: event.target.value })}
                >
                  <option value="">Select a movie library</option>
                  {movieSections.map((section) => (
                    <option key={section.key} value={section.key}>
                      {section.title}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>TV section</span>
                <select
                  value={settings.plex_tv_section ?? ""}
                  onChange={(event) => updateSettings({ plex_tv_section: event.target.value })}
                >
                  <option value="">Select a TV library</option>
                  {tvSections.map((section) => (
                    <option key={section.key} value={section.key}>
                      {section.title}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          ) : null}
        </section>
      );
    }

    if (currentStep === "automation") {
      return (
        <section className="wizard-panel">
          <h2>Step 3 — Automation framework (Radarr &amp; Sonarr)</h2>
          <div className="service-cards">
            {[
              { id: "radarr", label: "Radarr", fields: ["radarr_url", "radarr_api_key"] },
              { id: "sonarr", label: "Sonarr", fields: ["sonarr_url", "sonarr_api_key"] },
            ].map(({ id, label, fields }) => {
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
                    <div className="service-card-title">
                      <h3>{label}</h3>
                      <CertifiedBadge
                        certified={certifications[id]?.certified}
                        testing={testing === id}
                      />
                    </div>
                    <button type="button" onClick={() => runTest(id)} disabled={testing === id}>
                      {testing === id ? "Testing…" : "Verify"}
                    </button>
                  </div>
                  <div className="service-fields">
                    {fields.map((field) => (
                      <label key={field}>
                        <span>{field}</span>
                        {SECRET_FIELDS.includes(field) ? (
                          renderSecretInput(field, { disabled: testing === id })
                        ) : (
                          <input
                            type="text"
                            value={settings[field] ?? ""}
                            disabled={testing === id}
                            onChange={(event) => updateSettings({ [field]: event.target.value })}
                          />
                        )}
                      </label>
                    ))}
                  </div>
                  {result?.message ? (
                    <InlineAlert
                      type={actionAlert?.area === id ? actionAlert.type : result.state}
                      message={actionAlert?.area === id ? actionAlert.message : result.message}
                    />
                  ) : null}
                </div>
              );
            })}
          </div>
        </section>
      );
    }

    if (currentStep === "persona") {
      return (
        <section className="wizard-panel">
          <h2>Step 4 — Persona tuning</h2>
          <p className="wizard-summary">
            Curator: <strong>{persona.curator_name}</strong>{" "}
            <button type="button" className="ghost inline-link" onClick={() => setStepIndex(0)}>
              edit
            </button>
          </p>
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
                  onChange={(event) => setPersona({ ...persona, [key]: Number(event.target.value) })}
                  onMouseUp={(event) => savePersonaField(key, Number(event.target.value))}
                  onTouchEnd={(event) => savePersonaField(key, Number(event.target.value))}
                />
              </label>
            ))}
          </div>
          <p className="persona-preview">{preview}</p>
          <InlineAlert type={actionAlert?.area === "persona" ? actionAlert.type : null} message={actionAlert?.area === "persona" ? actionAlert.message : null} />
        </section>
      );
    }

    return (
      <section className="wizard-panel">
        <h2>Step 5 — Optional metadata services</h2>
        <p className="wizard-note">These improve discovery and artwork. You can skip and configure later.</p>
        <div className="service-cards">
          {OPTIONAL_SERVICES.map(({ id, label, fields }) => {
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
                  <div className="service-card-title">
                    <h3>{label}</h3>
                    <CertifiedBadge
                      certified={certifications[id]?.certified}
                      testing={testing === id}
                    />
                  </div>
                  <button type="button" onClick={() => runTest(id)} disabled={testing === id}>
                    {testing === id ? "Testing…" : "Test"}
                  </button>
                </div>
                <div className="service-fields">
                  {fields.map((field) => (
                    <label key={field}>
                      <span>{field}</span>
                      {SECRET_FIELDS.includes(field) ? (
                        renderSecretInput(field, { disabled: testing === id })
                      ) : (
                        <input
                          type="text"
                          value={settings[field] ?? ""}
                          disabled={testing === id}
                          onChange={(event) => updateSettings({ [field]: event.target.value })}
                        />
                      )}
                    </label>
                  ))}
                </div>
                {result?.message ? (
                  <InlineAlert
                    type={actionAlert?.area === id ? actionAlert.type : result.state}
                    message={actionAlert?.area === id ? actionAlert.message : result.message}
                  />
                ) : null}
              </div>
            );
          })}
        </div>
      </section>
    );
  }

  function renderMaintenanceDashboard() {
    return (
      <>
        <section className="config-section">
          <div className="dashboard-header">
            <h2>Maintenance dashboard</h2>
            <button type="button" className="ghost" onClick={() => setShowWizard(true)}>
              Re-run onboarding wizard
            </button>
          </div>
          <p>Integrations, persona, lenses, and advanced settings.</p>
        </section>

        <section className="config-section">
          <h2>LLM engine</h2>
          <div className="wizard-fields">
            <label>
              <span>Provider</span>
              <ProviderSelect
                value={settings.llm_provider}
                onChange={(event) => handleProviderChange(event.target.value)}
              />
            </label>
            <label>
              <span>Base URL</span>
              <input
                type="text"
                value={settings.llm_base_url ?? ""}
                onChange={(event) => updateSettings({ llm_base_url: event.target.value })}
              />
            </label>
            <label>
              <span>API key</span>
              {renderSecretInput("llm_api_key")}
            </label>
            <label>
              <span>Model</span>
              <input
                type="text"
                list={settings.llm_provider === "anthropic" ? "anthropic-model-options-maintenance" : undefined}
                value={settings.llm_model ?? ""}
                onChange={(event) => updateSettings({ llm_model: event.target.value })}
                placeholder={LLM_MODEL_DEFAULTS[settings.llm_provider] || "claude-sonnet-4-6"}
              />
              {settings.llm_provider === "anthropic" ? (
                <datalist id="anthropic-model-options-maintenance">
                  {ANTHROPIC_MODEL_OPTIONS.map((model) => (
                    <option key={model} value={model} />
                  ))}
                </datalist>
              ) : null}
            </label>
          </div>
          <button type="button" onClick={() => runTest("llm")} disabled={testing === "llm"}>
            Test LLM
          </button>
          <CertifiedBadge certified={certifications.llm?.certified} testing={testing === "llm"} />
          <InlineAlert
            type={actionAlert?.area === "llm" ? actionAlert.type : testResults.llm?.state}
            message={actionAlert?.area === "llm" ? actionAlert.message : testResults.llm?.message}
          />
        </section>

        <section className="config-section">
          <h2>Service integrations</h2>
          <div className="service-cards">
            {[
              { id: "plex", label: "Plex", fields: ["plex_url", "plex_token"] },
              { id: "radarr", label: "Radarr", fields: ["radarr_url", "radarr_api_key"] },
              { id: "sonarr", label: "Sonarr", fields: ["sonarr_url", "sonarr_api_key"] },
              ...OPTIONAL_SERVICES,
            ].map(({ id, label, fields }) => {
              const result = testResults[id];
              return (
                <div key={id} className={`service-card ${result?.state === "success" ? "service-ok" : ""} ${testing === id ? "service-loading" : ""} ${result?.state === "error" ? "service-error" : ""}`}>
                  <div className="service-card-header">
                    <div className="service-card-title">
                      <h3>{label}</h3>
                      <CertifiedBadge
                        certified={certifications[id]?.certified}
                        testing={testing === id}
                      />
                    </div>
                    <button type="button" onClick={() => runTest(id)} disabled={testing === id}>
                      {testing === id ? "Testing…" : "Test"}
                    </button>
                  </div>
                  <div className="service-fields">
                    {fields.map((field) => (
                      <label key={field}>
                        <span>{field}</span>
                        {SECRET_FIELDS.includes(field) ? (
                          renderSecretInput(field)
                        ) : (
                          <input
                            type="text"
                            value={settings[field] ?? ""}
                            onChange={(event) => updateSettings({ [field]: event.target.value })}
                          />
                        )}
                      </label>
                    ))}
                  </div>
                  {result?.message ? (
                    <InlineAlert
                      type={actionAlert?.area === id ? actionAlert.type : result.state}
                      message={actionAlert?.area === id ? actionAlert.message : result.message}
                    />
                  ) : null}
                </div>
              );
            })}
          </div>
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
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={persona[key]}
                  onChange={(event) => setPersona({ ...persona, [key]: Number(event.target.value) })}
                  onMouseUp={(event) => savePersonaField(key, Number(event.target.value))}
                  onTouchEnd={(event) => savePersonaField(key, Number(event.target.value))}
                />
                <div className="slider-range-labels">
                  <span>{low}</span>
                  <span>{high}</span>
                </div>
              </label>
            ))}
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
              />
            </label>
            <label>
              <span>Lens ID</span>
              <input
                type="text"
                value={newLens.lens_id}
                onChange={(event) => setNewLens({ ...newLens, lens_id: event.target.value })}
              />
            </label>
            <label>
              <span>Description</span>
              <input
                type="text"
                value={newLens.description}
                onChange={(event) => setNewLens({ ...newLens, description: event.target.value })}
              />
            </label>
            <button type="submit">Create lens</button>
          </form>
          <InlineAlert type={actionAlert?.area === "lens" ? actionAlert.type : null} message={actionAlert?.area === "lens" ? actionAlert.message : null} />
        </section>

        <section className="config-section">
          <h2>Advanced settings</h2>
          <div className="config-grid">
            {[
              "movies_root",
              "tv_root",
              "radarr_root_folder",
              "sonarr_root_folder",
              "library_sync_interval_hours",
              "tv_page_size",
            ].map((key) => (
              <label key={key}>
                <span>{key}</span>
                <input
                  type="text"
                  value={settings[key] ?? ""}
                  onChange={(event) =>
                    updateSettings({
                      [key]:
                        key.endsWith("_hours") || key === "tv_page_size"
                          ? Number(event.target.value || 0)
                          : event.target.value,
                    })
                  }
                />
              </label>
            ))}
          </div>
          <div className="config-actions">
            <button type="button" onClick={handleSaveSettings}>
              Save settings
            </button>
          </div>
          <InlineAlert type={actionAlert?.area === "save" ? actionAlert.type : null} message={actionAlert?.area === "save" ? actionAlert.message : null} />
        </section>
      </>
    );
  }

  return (
    <div className="config-page">
      <header className="topbar">
        <div>
          <p className="eyebrow">Configuration</p>
          <h1>{showWizard ? "Onboarding wizard" : "Curator maintenance"}</h1>
        </div>
        <Link to="/" className="btn-link">
          Back to chat
        </Link>
      </header>

      {showWizard ? (
        <>
          <nav className="wizard-nav" aria-label="Onboarding steps">
            {WIZARD_STEPS.map((step, index) => {
              const unlocked = stepUnlocked(index, verification);
              const active = index === stepIndex;
              const complete =
                (wizard.steps[step]?.complete ?? false) ||
                (index === 0 && verification.llm) ||
                (index === 1 && verification.plex && verification.sections) ||
                (index === 2 && verification.radarr && verification.sonarr);
              return (
                <button
                  key={step}
                  type="button"
                  className={[
                    "wizard-step",
                    active ? "wizard-step-active" : "",
                    complete ? "wizard-step-complete" : "",
                    !unlocked ? "wizard-step-locked" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  disabled={!unlocked}
                  onClick={() => unlocked && setStepIndex(index)}
                >
                  <span className="wizard-step-num">{index + 1}</span>
                  {STEP_LABELS[step]}
                </button>
              );
            })}
          </nav>

          {renderWizardStep()}

          <div className="wizard-footer">
            {stepIndex > 0 ? (
              <button type="button" className="ghost" onClick={() => setStepIndex((prev) => prev - 1)}>
                Back
              </button>
            ) : (
              <span />
            )}
            <div className="wizard-footer-actions">
              {stepIndex < WIZARD_STEPS.length - 1 ? (
                <button type="button" onClick={handleNext} disabled={!canAdvance(stepIndex, verification)}>
                  Next
                </button>
              ) : (
                <div className="wizard-finish-actions">
                  <button type="button" className="ghost" onClick={handleFinish}>
                    Skip optional &amp; finish
                  </button>
                  <button type="button" onClick={handleFinish}>
                    Finish onboarding
                  </button>
                </div>
              )}
              <InlineAlert type={footerAlert?.type} message={footerAlert?.message} />
            </div>
          </div>
        </>
      ) : (
        renderMaintenanceDashboard()
      )}

      {status ? <p className="status status-secondary">{status}</p> : null}
    </div>
  );
}
