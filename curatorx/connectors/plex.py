"""Plex API connector with rich library metadata."""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from curatorx.connectors.http import optional_int, parse_plex_guid, request_xml


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
    last_viewed_at: Optional[int] = None
    tmdb_id: Optional[str] = None
    tvdb_id: Optional[str] = None
    imdb_id: Optional[str] = None
    file_size: int = 0


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
        root = self._request_xml(f"/library/metadata/{rating_key}")
        video = root.find(".//Video") or root.find(".//Directory")
        if video is None:
            raise RuntimeError(f"No metadata for rating key {rating_key}")
        media_type = "show" if video.tag == "Directory" else "movie"
        return self._parse_video(video, media_type)

    def thumb_url(self, path: str) -> str:
        if not path:
            return ""
        if path.startswith("http"):
            return path
        separator = "&" if "?" in path else "?"
        return f"{self.base_url}{path}{separator}X-Plex-Token={urllib.parse.quote(self.token)}"

    def _fetch_items(self, section_key: str, media_type: str, plex_type: int) -> List[PlexLibraryItem]:
        root = self._request_xml(f"/library/sections/{section_key}/all?type={plex_type}")
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
                f"?type={plex_type}&X-Plex-Container-Start={start}"
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
        ids = parse_plex_guid(guid)
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
            last_viewed_at=optional_int(element.attrib.get("lastViewedAt")),
            tmdb_id=ids.get("tmdb_id"),
            tvdb_id=ids.get("tvdb_id"),
            imdb_id=ids.get("imdb_id"),
            file_size=file_size,
        )

    def _find_section_key(self, section_type: str) -> str:
        for section in self.list_sections():
            if section.type == section_type:
                return section.key
        raise RuntimeError(f"No Plex {section_type} library section found")

    def _request_xml(self, path: str):
        separator = "&" if "?" in path else "?"
        url = f"{self.base_url}{path}{separator}X-Plex-Token={urllib.parse.quote(self.token)}"
        return request_xml(url, headers={"Accept": "application/xml"}, timeout=self.timeout)
