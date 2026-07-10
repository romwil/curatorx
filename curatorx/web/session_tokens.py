"""Signed session cookies for optional multi-user auth."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Optional

SESSION_COOKIE_NAME = "curatorx_session"
DEFAULT_TTL_SECONDS = 30 * 86400


def _secret() -> bytes:
    raw = os.environ.get("CURATORX_SESSION_SECRET", "curatorx-dev-session-secret")
    return raw.encode("utf-8")


def create_session_token(user_id: str, *, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    payload = {"uid": user_id, "exp": time.time() + ttl_seconds}
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()
    sig = hmac.new(_secret(), body.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def parse_session_token(token: str) -> Optional[str]:
    if not token or "." not in token:
        return None
    body, sig = token.rsplit(".", 1)
    expected = hmac.new(_secret(), body.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(body.encode("utf-8")).decode("utf-8"))
    except (json.JSONDecodeError, ValueError):
        return None
    user_id = payload.get("uid")
    exp = payload.get("exp")
    if not user_id or not isinstance(exp, (int, float)) or float(exp) < time.time():
        return None
    return str(user_id)
