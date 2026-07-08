"""Radarr API client with read and write operations."""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from typing import Any, List, Mapping, Optional

from curatorx.connectors.http import request_json


@dataclass
class RadarrMovie:
    id: int
    title: str
    year: Optional[int]
    tmdb_id: int
    monitored: bool
    has_file: bool
    file_path: str = ""
    file_size: int = 0


class RadarrClient:
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

    def movies(self) -> List[RadarrMovie]:
        payload = request_json(
            f"{self.base_url}/api/v3/movie",
            headers=self._headers(),
            timeout=self.timeout,
        )
        movies: List[RadarrMovie] = []
        if not isinstance(payload, list):
            return movies
        for item in payload:
            movie_file = item.get("movieFile") or {}
            movies.append(
                RadarrMovie(
                    id=int(item["id"]),
                    title=str(item.get("title") or ""),
                    year=item.get("year"),
                    tmdb_id=int(item.get("tmdbId") or 0),
                    monitored=bool(item.get("monitored")),
                    has_file=bool(movie_file),
                    file_path=str(movie_file.get("path") or item.get("path") or ""),
                    file_size=int(movie_file.get("size") or 0),
                )
            )
        return movies

    def lookup(self, term: str) -> List[Mapping[str, Any]]:
        encoded = urllib.parse.quote(term)
        payload = request_json(
            f"{self.base_url}/api/v3/movie/lookup?term={encoded}",
            headers=self._headers(),
            timeout=self.timeout,
        )
        return payload if isinstance(payload, list) else []

    def lookup_tmdb(self, tmdb_id: int) -> Optional[Mapping[str, Any]]:
        payload = request_json(
            f"{self.base_url}/api/v3/movie/lookup/tmdb?tmdbId={tmdb_id}",
            headers=self._headers(),
            timeout=self.timeout,
        )
        return payload if isinstance(payload, dict) else None

    def add_movie(
        self,
        tmdb_id: int,
        *,
        root_folder: str,
        quality_profile_id: int,
        monitored: bool = True,
        search_for_movie: bool = True,
    ) -> Mapping[str, Any]:
        lookup = self.lookup_tmdb(tmdb_id)
        if not lookup:
            raise RuntimeError(f"Radarr could not lookup TMDB id {tmdb_id}")
        lookup["rootFolderPath"] = root_folder
        lookup["qualityProfileId"] = quality_profile_id
        lookup["monitored"] = monitored
        lookup["addOptions"] = {"searchForMovie": search_for_movie}
        result = request_json(
            f"{self.base_url}/api/v3/movie",
            method="POST",
            headers=self._headers(),
            body=lookup,
            timeout=self.timeout,
        )
        return result if isinstance(result, dict) else {}

    def delete_movie(self, movie_id: int, *, delete_files: bool = False) -> None:
        request_json(
            f"{self.base_url}/api/v3/movie/{movie_id}?deleteFiles={'true' if delete_files else 'false'}",
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
