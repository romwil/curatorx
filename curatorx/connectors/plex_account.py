"""Plex account validation for household login."""

from __future__ import annotations

from typing import Any, Dict

from curatorx.connectors.http import request_json


def fetch_plex_account(auth_token: str, *, timeout: int = 20) -> Dict[str, Any]:
    payload = request_json(
        "https://plex.tv/api/v2/user",
        headers={
            "Accept": "application/json",
            "X-Plex-Token": auth_token.strip(),
        },
        timeout=timeout,
    )
    if not isinstance(payload, dict):
        raise RuntimeError("Unexpected Plex account response")
    return payload
