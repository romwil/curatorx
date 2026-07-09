"""Plex API connector with rich library metadata."""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from curatorx.connectors.http import merge_plex_provider_ids, optional_int, request_xml


@dataclass
class PlexSection:
    key: str
    title: str
    type: str


@dataclass
class PlexLibraryItem:
    rating_key: str
    media_type: str  # movie | show
    title: str
    year: Optional[int]
    summary: str = ""
    thumb: str = ""
    art: str = ""
    guid: str = ""
    genres: List[str] = field(default_factory=list)
    directors: List[str] = field(default_factory=list)
    cast: List[str] = field(default_factory=list)
    content_rating: str = ""
    duration_ms: Optional[int] = None
    view_count: int = 0
    added_at: Optional[int] = None
    last_viewed_at: Optional[int] = None
    tmdb_id: Optional[str] = None
    tvdb_id: Optional[str] = None
    imdb_id: Optional[str] = None
    file_size: int = 0
    season_count: Optional[int] = None
    leaf_count: Optional[int] = None
    viewed_leaf_count: Optional[int] = None


@dataclass
class PlexSeason:
    rating_key: str
    season_number: Optional[int]
    title: str = ""
    leaf_count: int = 0
    viewed_leaf_count: int = 0


@dataclass
class PlexEpisode:
    rating_key: str
    title: str
    season_number: Optional[int] = None
    episode_number: Optional[int] = None
    runtime_minutes: Optional[int] = None
    view_count: int = 0
    last_viewed_at: Optional[int] = None
    file_size: int = 0
    aired_at: str = ""


class PlexClient:
    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        movie_section: Optional[str] = None,
        tv_section: Optional[str] = None,
        timeout: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.movie_section = movie_section
        self.tv_section = tv_section
        self.timeout = timeout

    def list_sections(self) -> List[PlexSection]:
        root = self._request_xml("/library/sections")
        sections: List[PlexSection] = []
        for directory in root.findall(".//Directory"):
            key = directory.attrib.get("key")
            if not key:
                continue
            sections.append(
                PlexSection(
                    key=key,
                    title=str(directory.attrib.get("title") or ""),
                    type=str(directory.attrib.get("type") or ""),
                )
            )
        return sections

    def movie_items(self) -> List[PlexLibraryItem]:
        section_key = self.movie_section or self._find_section_key("movie")
        return self._fetch_items(section_key, media_type="movie", plex_type=1)

    def show_items(
        self,
        page_size: int = 500,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> List[PlexLibraryItem]:
        section_key = self.tv_section or self._find_section_key("show")
        return self._fetch_items_paged(
            section_key,
            media_type="show",
            plex_type=2,
            page_size=page_size,
            progress_callback=progress_callback,
        )

    def get_metadata(self, rating_key: str) -> PlexLibraryItem:
        root = self._request_xml(f"/library/metadata/{rating_key}?includeGuids=1")
        video = root.find(".//Video") or root.find(".//Directory")
        if video is None:
            raise RuntimeError(f"No metadata for rating key {rating_key}")
        media_type = "show" if video.tag == "Directory" else "movie"
        return self._parse_video(video, media_type)

    def show_seasons(self, show_rating_key: str) -> List[PlexSeason]:
        key = str(show_rating_key or "").strip()
        if not key:
            raise ValueError("show_rating_key is required")
        # excludeAllLeaves drops Plex's virtual "All episodes" folder (no ratingKey).
        root = self._request_xml(f"/library/metadata/{key}/children?excludeAllLeaves=1")
        seasons: List[PlexSeason] = []
        for element in self._container_children(root, "Directory"):
            season_key = str(element.attrib.get("ratingKey") or "").strip()
            if not season_key:
                continue
            seasons.append(
                PlexSeason(
                    rating_key=season_key,
                    season_number=optional_int(element.attrib.get("index")),
                    title=str(element.attrib.get("title") or ""),
                    leaf_count=int(element.attrib.get("leafCount") or 0),
                    viewed_leaf_count=int(element.attrib.get("viewedLeafCount") or 0),
                )
            )
        return seasons

    def show_all_episodes(self, show_rating_key: str) -> List[PlexEpisode]:
        """Return every episode under a show (works when Plex hides/flattens seasons)."""
        key = str(show_rating_key or "").strip()
        if not key:
            raise ValueError("show_rating_key is required")
        root = self._request_xml(f"/library/metadata/{key}/allLeaves")
        return self._parse_episode_elements(self._container_children(root, "Video"))

    def season_episodes(self, season_rating_key: str) -> List[PlexEpisode]:
        key = str(season_rating_key or "").strip()
        if not key:
            raise ValueError("season_rating_key is required")
        root = self._request_xml(f"/library/metadata/{key}/children")
        return self._parse_episode_elements(self._container_children(root, "Video"))

    def thumb_url(self, path: str) -> str:
        if not path:
            return ""
        if path.startswith("http"):
            return path
        separator = "&" if "?" in path else "?"
        return f"{self.base_url}{path}{separator}X-Plex-Token={urllib.parse.quote(self.token)}"

    def _fetch_items(self, section_key: str, media_type: str, plex_type: int) -> List[PlexLibraryItem]:
        root = self._request_xml(
            f"/library/sections/{section_key}/all?type={plex_type}&includeGuids=1"
        )
        items: List[PlexLibraryItem] = []
        tag = "Video" if media_type == "movie" else "Directory"
        for element in root.findall(f".//{tag}"):
            items.append(self._parse_video(element, media_type))
        return items

    def _fetch_items_paged(
        self,
        section_key: str,
        media_type: str,
        plex_type: int,
        page_size: int,
        progress_callback: Optional[Callable[[int, int, str], None]],
    ) -> List[PlexLibraryItem]:
        items: List[PlexLibraryItem] = []
        start = 0
        total_size: Optional[int] = None
        tag = "Video" if media_type == "movie" else "Directory"

        while True:
            root = self._request_xml(
                f"/library/sections/{section_key}/all"
                f"?type={plex_type}&includeGuids=1"
                f"&X-Plex-Container-Start={start}"
                f"&X-Plex-Container-Size={page_size}"
            )
            container = root.find(".//MediaContainer") or root
            if total_size is None:
                total_size = optional_int(container.attrib.get("totalSize"))
            elements = root.findall(f".//{tag}")
            if not elements:
                break
            for element in elements:
                items.append(self._parse_video(element, media_type))
            start += len(elements)
            if progress_callback:
                total = total_size if total_size is not None else start
                progress_callback(start, max(total, 1), "scanning_plex")
            if len(elements) < page_size:
                break
        return items

    def _parse_video(self, element, media_type: str) -> PlexLibraryItem:
        guid = str(element.attrib.get("guid") or "")
        child_guids = [
            str(child.attrib.get("id") or "")
            for child in element.findall("Guid")
            if child.attrib.get("id")
        ]
        ids = merge_plex_provider_ids(guid, *child_guids)
        genres = [g.attrib.get("tag", "") for g in element.findall(".//Genre")]
        directors = [d.attrib.get("tag", "") for d in element.findall(".//Director")]
        cast = [r.attrib.get("tag", "") for r in element.findall(".//Role")][:8]
        file_size = 0
        for part in element.findall(".//Part"):
            file_size += int(part.attrib.get("size") or 0)
        return PlexLibraryItem(
            rating_key=str(element.attrib.get("ratingKey") or ""),
            media_type=media_type,
            title=str(element.attrib.get("title") or ""),
            year=optional_int(element.attrib.get("year")),
            summary=str(element.attrib.get("summary") or ""),
            thumb=str(element.attrib.get("thumb") or ""),
            art=str(element.attrib.get("art") or ""),
            guid=guid,
            genres=[g for g in genres if g],
            directors=[d for d in directors if d],
            cast=[c for c in cast if c],
            content_rating=str(element.attrib.get("contentRating") or ""),
            duration_ms=optional_int(element.attrib.get("duration")),
            view_count=int(element.attrib.get("viewCount") or 0),
            added_at=optional_int(element.attrib.get("addedAt")),
            last_viewed_at=optional_int(element.attrib.get("lastViewedAt")),
            tmdb_id=ids.get("tmdb_id"),
            tvdb_id=ids.get("tvdb_id"),
            imdb_id=ids.get("imdb_id"),
            file_size=file_size,
            season_count=optional_int(element.attrib.get("childCount")) if media_type == "show" else None,
            leaf_count=optional_int(element.attrib.get("leafCount")) if media_type == "show" else None,
            viewed_leaf_count=optional_int(element.attrib.get("viewedLeafCount")) if media_type == "show" else None,
        )

    def _container_children(self, root, tag: str):
        container = root if root.tag == "MediaContainer" else root.find("MediaContainer")
        if container is None:
            container = root
        return container.findall(tag)

    def _parse_episode_elements(self, elements) -> List[PlexEpisode]:
        episodes: List[PlexEpisode] = []
        for element in elements:
            duration_ms = optional_int(element.attrib.get("duration"))
            runtime_minutes = int(duration_ms / 60000) if duration_ms else None
            file_size = 0
            for part in element.findall(".//Part"):
                file_size += int(part.attrib.get("size") or 0)
            aired = str(element.attrib.get("originallyAvailableAt") or "")
            episodes.append(
                PlexEpisode(
                    rating_key=str(element.attrib.get("ratingKey") or ""),
                    title=str(element.attrib.get("title") or ""),
                    season_number=optional_int(element.attrib.get("parentIndex")),
                    episode_number=optional_int(element.attrib.get("index")),
                    runtime_minutes=runtime_minutes,
                    view_count=int(element.attrib.get("viewCount") or 0),
                    last_viewed_at=optional_int(element.attrib.get("lastViewedAt")),
                    file_size=file_size,
                    aired_at=aired,
                )
            )
        return episodes

    def _find_section_key(self, section_type: str) -> str:
        for section in self.list_sections():
            if section.type == section_type:
                return section.key
        raise RuntimeError(f"No Plex {section_type} library section found")

    def _request_xml(self, path: str):
        separator = "&" if "?" in path else "?"
        url = f"{self.base_url}{path}{separator}X-Plex-Token={urllib.parse.quote(self.token)}"
        return request_xml(url, headers={"Accept": "application/xml"}, timeout=self.timeout)
