"""Sonarr API client with read and write operations."""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from typing import Any, List, Mapping, Optional

from mediacurator.connectors.http import request_json


@dataclass
class SonarrSeries:
    id: int
    title: str
    year: Optional[int]
    tvdb_id: int
    tmdb_id: Optional[int]
    monitored: bool
    episode_file_count: int = 0
    total_file_size: int = 0


class SonarrClient:
    def __init__(self, base_url: str, api_key: str, timeout: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"X-Api-Key": self.api_key}

    def system_status(self) -> Mapping[str, Any]:
        return request_json(
            f"{self.base_url}/api/v3/system/status",
            headers=self._headers(),
            timeout=self.timeout,
        )

    def series_list(self) -> List[SonarrSeries]:
        payload = request_json(
            f"{self.base_url}/api/v3/series",
            headers=self._headers(),
            timeout=self.timeout,
        )
        series_items: List[SonarrSeries] = []
        if not isinstance(payload, list):
            return series_items
        for item in payload:
            stats = item.get("statistics") or {}
            series_items.append(
                SonarrSeries(
                    id=int(item["id"]),
                    title=str(item.get("title") or ""),
                    year=item.get("year"),
                    tvdb_id=int(item.get("tvdbId") or 0),
                    tmdb_id=item.get("tmdbId"),
                    monitored=bool(item.get("monitored")),
                    episode_file_count=int(stats.get("episodeFileCount") or 0),
                    total_file_size=int(stats.get("sizeOnDisk") or 0),
                )
            )
        return series_items

    def lookup(self, term: str) -> List[Mapping[str, Any]]:
        encoded = urllib.parse.quote(term)
        payload = request_json(
            f"{self.base_url}/api/v3/series/lookup?term={encoded}",
            headers=self._headers(),
            timeout=self.timeout,
        )
        return payload if isinstance(payload, list) else []

    def lookup_tvdb(self, tvdb_id: int) -> Optional[Mapping[str, Any]]:
        results = self.lookup(f"tvdb:{tvdb_id}")
        for item in results:
            if int(item.get("tvdbId") or 0) == tvdb_id:
                return item
        return results[0] if results else None

    def add_series(
        self,
        tvdb_id: int,
        *,
        root_folder: str,
        quality_profile_id: int,
        monitored: bool = True,
        search_for_missing: bool = True,
        season_folder: bool = True,
    ) -> Mapping[str, Any]:
        lookup = self.lookup_tvdb(tvdb_id)
        if not lookup:
            raise RuntimeError(f"Sonarr could not lookup TVDB id {tvdb_id}")
        lookup["rootFolderPath"] = root_folder
        lookup["qualityProfileId"] = quality_profile_id
        lookup["monitored"] = monitored
        lookup["seasonFolder"] = season_folder
        lookup["addOptions"] = {"searchForMissingEpisodes": search_for_missing}
        result = request_json(
            f"{self.base_url}/api/v3/series",
            method="POST",
            headers=self._headers(),
            body=lookup,
            timeout=self.timeout,
        )
        return result if isinstance(result, dict) else {}

    def delete_series(self, series_id: int, *, delete_files: bool = False) -> None:
        request_json(
            f"{self.base_url}/api/v3/series/{series_id}?deleteFiles={'true' if delete_files else 'false'}",
            method="DELETE",
            headers=self._headers(),
            timeout=self.timeout,
        )

    def quality_profiles(self) -> List[Mapping[str, Any]]:
        payload = request_json(
            f"{self.base_url}/api/v3/qualityprofile",
            headers=self._headers(),
            timeout=self.timeout,
        )
        return payload if isinstance(payload, list) else []

    def root_folders(self) -> List[Mapping[str, Any]]:
        payload = request_json(
            f"{self.base_url}/api/v3/rootfolder",
            headers=self._headers(),
            timeout=self.timeout,
        )
        return payload if isinstance(payload, list) else []
