import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { formatApiError, getFeatures, loginWithPlex } from "../api/client";
import InlineAlert from "../components/InlineAlert";

export default function LoginPage() {
  const navigate = useNavigate();
  const [features, setFeatures] = useState(null);
  const [authToken, setAuthToken] = useState("");
  const [showTokenInput, setShowTokenInput] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getFeatures()
      .then((data) => {
        setFeatures(data);
        if (!data?.features?.multi_user_enabled) {
          navigate("/", { replace: true });
        }
      })
      .catch((fetchError) => setError(formatApiError(fetchError)));
  }, [navigate]);

  async function handleSignIn(event) {
    event.preventDefault();
    const token = authToken.trim();
    if (!token) {
      setError("Paste your Plex token to continue.");
      setShowTokenInput(true);
      return;
    }
    setLoading(true);
    setError("");
    try {
      await loginWithPlex(token);
      navigate("/", { replace: true });
    } catch (signInError) {
      setError(formatApiError(signInError));
    } finally {
      setLoading(false);
    }
  }

  const plexEnabled = features?.auth?.plex_login_enabled !== false;

  return (
    <div className="login-page" data-testid="login-page">
      <div className="login-card">
        <p className="eyebrow">CuratorX</p>
        <h1>Sign in</h1>
        <p className="login-lede">
          Multi-user mode is enabled. Sign in with your Plex account to access your conversations and watchlist.
        </p>

        {error ? <InlineAlert type="error" message={error} /> : null}

        {plexEnabled ? (
          <form className="login-form" onSubmit={handleSignIn}>
            {!showTokenInput ? (
              <button
                type="button"
                className="login-primary"
                data-testid="sign-in-with-plex"
                disabled={loading}
                onClick={() => setShowTokenInput(true)}
              >
                Sign in with Plex
              </button>
            ) : (
              <>
                <label className="login-token-field">
                  <span>Plex token</span>
                  <input
                    type="password"
                    data-testid="plex-token-input"
                    value={authToken}
                    onChange={(event) => setAuthToken(event.target.value)}
                    placeholder="Paste token from plex.tv/account"
                    autoComplete="off"
                    disabled={loading}
                  />
                </label>
                <p className="login-help">
                  Open{" "}
                  <a href="https://app.plex.tv/desktop/#!/settings/account" target="_blank" rel="noreferrer">
                    Plex account settings
                  </a>
                  , copy your token, and paste it here. CuratorX validates it with Plex and stores a signed session cookie.
                </p>
                <button type="submit" className="login-primary" data-testid="submit-plex-login" disabled={loading}>
                  {loading ? "Signing in…" : "Continue with Plex"}
                </button>
              </>
            )}
          </form>
        ) : (
          <InlineAlert type="error" message="Plex login is disabled in Configuration." />
        )}

        <p className="login-footer">
          Need to change auth settings? <Link to="/config">Open Configuration</Link>
        </p>
      </div>
    </div>
  );
}
