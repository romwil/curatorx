"""Shared HTTP helpers for connectors."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Mapping, Optional


def request_json(
    url: str,
    *,
    method: str = "GET",
    headers: Optional[Mapping[str, str]] = None,
    body: Optional[Mapping[str, Any]] = None,
    timeout: int = 30,
) -> Any:
    data = None
    req_headers = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=data, method=method, headers=req_headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            if not raw.strip():
                return None
            return json.loads(raw)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code} from {url}: {detail}") from error


def request_xml(url: str, *, headers: Optional[Mapping[str, str]] = None, timeout: int = 30) -> ET.Element:
    request = urllib.request.Request(url, headers=dict(headers or {}))
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return ET.fromstring(response.read())


def optional_int(value: Optional[str]) -> Optional[int]:
    if value is None or value == "":
        return None
    return int(value)


def parse_plex_guid(guid: str) -> dict[str, str]:
    """Extract provider IDs from Plex GUID strings."""
    result: dict[str, str] = {}
    if not guid:
        return result
    if "themoviedb://" in guid:
        result["tmdb_id"] = guid.split("themoviedb://")[-1].split("?")[0]
    if "tvdb://" in guid:
        result["tvdb_id"] = guid.split("tvdb://")[-1].split("?")[0]
    if "imdb://" in guid or "com.plexapp.agents.imdb://" in guid:
        parts = guid.replace("com.plexapp.agents.imdb://", "imdb://")
        result["imdb_id"] = parts.split("imdb://")[-1].split("?")[0]
    return result
