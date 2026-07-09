"""Shared HTTP helpers for connectors."""

from __future__ import annotations

import json
import logging
import socket
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Mapping, Optional

from curatorx.logging_config import sanitize_log_message, sanitize_url

logger = logging.getLogger(__name__)


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
    safe_url = sanitize_url(url)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            if not raw.strip():
                return None
            return json.loads(raw)
    except urllib.error.HTTPError as error:
        detail = sanitize_log_message(error.read().decode("utf-8", errors="replace"))
        logger.warning("HTTP %s %s from %s: %s", method, error.code, safe_url, detail[:500])
        raise RuntimeError(f"HTTP {error.code} from {safe_url}: {detail}") from error
    except urllib.error.URLError as error:
        reason = error.reason
        if isinstance(reason, socket.timeout):
            logger.warning("Timeout %s %s (timeout=%ss)", method, safe_url, timeout)
        else:
            logger.warning("Request failed %s %s: %s", method, safe_url, reason)
        raise RuntimeError(f"Request failed for {safe_url}: {reason}") from error
    except TimeoutError as error:
        logger.warning("Timeout %s %s (timeout=%ss)", method, safe_url, timeout)
        raise RuntimeError(f"Timeout requesting {safe_url}") from error


def request_xml(url: str, *, headers: Optional[Mapping[str, str]] = None, timeout: int = 30) -> ET.Element:
    request = urllib.request.Request(url, headers=dict(headers or {}))
    safe_url = sanitize_url(url)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return ET.fromstring(response.read())
    except urllib.error.HTTPError as error:
        detail = sanitize_log_message(error.read().decode("utf-8", errors="replace"))
        logger.warning("HTTP GET %s from %s: %s", error.code, safe_url, detail[:500])
        raise RuntimeError(f"HTTP {error.code} from {safe_url}: {detail}") from error
    except urllib.error.URLError as error:
        reason = error.reason
        if isinstance(reason, socket.timeout):
            logger.warning("Timeout GET %s (timeout=%ss)", safe_url, timeout)
        else:
            logger.warning("Request failed GET %s: %s", safe_url, reason)
        raise RuntimeError(f"Request failed for {safe_url}: {reason}") from error
    except TimeoutError as error:
        logger.warning("Timeout GET %s (timeout=%ss)", safe_url, timeout)
        raise RuntimeError(f"Timeout requesting {safe_url}") from error


def optional_int(value: Optional[str]) -> Optional[int]:
    if value is None or value == "":
        return None
    return int(value)


def _provider_id_from_guid(guid: str, marker: str, key: str, result: dict[str, str]) -> None:
    if key in result or marker not in guid:
        return
    result[key] = guid.split(marker, 1)[-1].split("?")[0]


def parse_plex_guid(guid: str) -> dict[str, str]:
    """Extract provider IDs from Plex GUID strings."""
    result: dict[str, str] = {}
    if not guid:
        return result
    _provider_id_from_guid(guid, "themoviedb://", "tmdb_id", result)
    _provider_id_from_guid(guid, "tmdb://", "tmdb_id", result)
    _provider_id_from_guid(guid, "tvdb://", "tvdb_id", result)
    if "imdb://" in guid or "com.plexapp.agents.imdb://" in guid:
        parts = guid.replace("com.plexapp.agents.imdb://", "imdb://")
        result["imdb_id"] = parts.split("imdb://", 1)[-1].split("?")[0]
    return result


def merge_plex_provider_ids(*guids: str) -> dict[str, str]:
    """Merge provider IDs from Plex primary guid and Guid child entries."""
    merged: dict[str, str] = {}
    for guid in guids:
        for key, value in parse_plex_guid(guid).items():
            merged.setdefault(key, value)
    return merged
