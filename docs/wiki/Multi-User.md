# Multi-User

CuratorX 1.0 is a **single-owner** app by default — no login screen.

## Enabling household mode

In Configuration (or `settings.json`):

```json
{
  "features": {
    "multi_user_enabled": true
  },
  "auth": {
    "mode": "plex",
    "plex_login_enabled": true
  }
}
```

When enabled:

- Visitors must sign in with **Plex**
- The first linked account becomes the **owner**
- Members get scoped chat/reviews; library sync and destructive *arr actions stay owner-gated

## Not in 1.0

- OIDC / SSO
- Local username + password accounts

Those flags may appear in settings schemas as placeholders — do not expect them to authenticate users yet.

## Owner tasks

- Start library sync from **Config**
- Manage feature flags and service credentials
- Approve / perform fleet-changing Radarr/Sonarr actions as designed by role checks

See [../CONFIGURATION.md](../CONFIGURATION.md#feature-flags-optional-off-by-default) and [Seerr](Seerr.md).
