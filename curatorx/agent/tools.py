"""Agent tool definitions and execution."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Callable, Dict, List, Mapping, Optional

from curatorx.config_store import Settings
from curatorx.connectors.radarr import RadarrClient
from curatorx.connectors.sonarr import SonarrClient
from curatorx.connectors.tmdb import TMDBClient
from curatorx.library.db import Database
from curatorx.library.search import row_to_title_card, search_library
from curatorx.library.titles import get_title_detail
from curatorx.models.schemas import TitleCard
from curatorx.preferences.purge import suggest_purge_candidates
from curatorx.preferences.store import preference_context, remember_preference


TOOL_DEFINITIONS: List[Mapping[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_library",
            "description": "Search the user's Plex library by theme, genre, title, or mood.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "media_type": {"type": "string", "enum": ["movie", "show"]},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_collection_gaps",
            "description": "Find movies or shows missing from the library for a genre/decade/theme query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "media_type": {"type": "string", "enum": ["movie", "show"]},
                    "year_from": {"type": "integer"},
                    "year_to": {"type": "integer"},
                    "genres": {"type": "string", "description": "Comma-separated genre names"},
                    "keywords": {"type": "string", "description": "Theme keywords"},
                },
                "required": ["media_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_hidden_gems",
            "description": "Recommend highly rated titles not in the library, filtered by taste.",
            "parameters": {
                "type": "object",
                "properties": {
                    "media_type": {"type": "string", "enum": ["movie", "show"]},
                    "query": {"type": "string"},
                },
                "required": ["media_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_purge_candidates",
            "description": "Find library items wasting drive space that are unlikely to be watched.",
            "parameters": {"type": "object", "properties": {"limit": {"type": "integer"}}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember_preference",
            "description": "Store an explicit user taste preference for future recommendations.",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_radarr",
            "description": "Propose adding a movie to Radarr. Returns a confirmation token.",
            "parameters": {
                "type": "object",
                "properties": {"tmdb_id": {"type": "integer"}, "title": {"type": "string"}},
                "required": ["tmdb_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_sonarr",
            "description": "Propose adding a TV show to Sonarr. Returns a confirmation token.",
            "parameters": {
                "type": "object",
                "properties": {"tvdb_id": {"type": "integer"}, "title": {"type": "string"}},
                "required": ["tvdb_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remove_from_arr",
            "description": "Propose removing a title from Radarr/Sonarr. Returns a confirmation token.",
            "parameters": {
                "type": "object",
                "properties": {
                    "media_type": {"type": "string", "enum": ["movie", "show"]},
                    "arr_id": {"type": "integer"},
                    "title": {"type": "string"},
                    "delete_files": {"type": "boolean"},
                },
                "required": ["media_type", "arr_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_title_detail",
            "description": "Get rich metadata for a specific title by TMDB/TVDB id or Plex rating key.",
            "parameters": {
                "type": "object",
                "properties": {
                    "media_type": {"type": "string", "enum": ["movie", "show"]},
                    "tmdb_id": {"type": "integer"},
                    "tvdb_id": {"type": "integer"},
                    "rating_key": {"type": "string"},
                },
                "required": ["media_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "explore_genre",
            "description": "Browse the user's library and TMDB for titles in a genre or theme.",
            "parameters": {
                "type": "object",
                "properties": {
                    "genre": {"type": "string"},
                    "media_type": {"type": "string", "enum": ["movie", "show"]},
                    "include_missing": {"type": "boolean", "description": "Include TMDB titles not in library"},
                },
                "required": ["genre", "media_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "what_to_watch_tonight",
            "description": "Suggest unwatched or under-watched library titles for tonight.",
            "parameters": {
                "type": "object",
                "properties": {
                    "media_type": {"type": "string", "enum": ["movie", "show"]},
                    "limit": {"type": "integer"},
                    "mood": {"type": "string", "description": "Optional mood or theme filter"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_watch_patterns",
            "description": "Summarize viewing habits: top genres, stale titles, binge patterns.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def _tmdb_card(item: Mapping[str, Any], media_type: str, tmdb: TMDBClient, *, reason: str = "") -> TitleCard:
    poster = tmdb.poster_url(item.get("poster_path"))
    backdrop = tmdb.backdrop_url(item.get("backdrop_path"))
    title = item.get("title") or item.get("name") or ""
    year = None
    date = item.get("release_date") or item.get("first_air_date") or ""
    if date:
        year = int(str(date)[:4])
    tvdb_id = None
    if media_type == "show":
        external = item.get("external_ids") or {}
        if external.get("tvdb_id"):
            tvdb_id = int(external["tvdb_id"])
    return TitleCard(
        media_type=media_type,  # type: ignore[arg-type]
        title=str(title),
        year=year,
        tmdb_id=int(item.get("id") or 0),
        tvdb_id=tvdb_id,
        poster_url=poster,
        backdrop_url=backdrop,
        overview=str(item.get("overview") or ""),
        rating=float(item.get("vote_average") or 0) or None,
        recommendation_reason=reason,
        in_library=False,
    )


class ToolRegistry:
    def __init__(self, db: Database, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self._cards: List[TitleCard] = []
        self._pending_tokens: List[str] = []

    @property
    def cards(self) -> List[TitleCard]:
        return list(self._cards)

    @property
    def pending_tokens(self) -> List[str]:
        return list(self._pending_tokens)

    async def execute(self, name: str, arguments: Mapping[str, Any]) -> str:
        handler: Optional[Callable] = getattr(self, f"_tool_{name}", None)
        if handler is None:
            return json.dumps({"error": f"Unknown tool {name}"})
        return await handler(arguments)

    async def _tool_search_library(self, args: Mapping[str, Any]) -> str:
        cards = await search_library(
            self.db,
            self.settings,
            str(args.get("query") or ""),
            media_type=args.get("media_type"),
        )
        self._cards.extend(cards)
        return json.dumps({"count": len(cards), "titles": [c.title for c in cards]})

    async def _tool_find_collection_gaps(self, args: Mapping[str, Any]) -> str:
        media_type = str(args.get("media_type") or "movie")
        if not self.settings.tmdb_api_key:
            return json.dumps({"error": "TMDB API key not configured"})
        tmdb = TMDBClient(self.settings.tmdb_api_key)
        owned = self.db.owned_tmdb_ids(media_type)
        genres = str(args.get("genres") or "")
        genre_ids = ""
        if genres:
            genre_list = tmdb.genre_list_movies() if media_type == "movie" else tmdb.genre_list_tv()
            wanted = {g.strip().lower() for g in genres.split(",") if g.strip()}
            matched = [str(g["id"]) for g in genre_list if g.get("name", "").lower() in wanted]
            genre_ids = ",".join(matched)

        if media_type == "movie":
            results = tmdb.discover_movies(
                year_from=args.get("year_from"),
                year_to=args.get("year_to"),
                with_genres=genre_ids or None,
                with_keywords=str(args.get("keywords") or "") or None,
            )
        else:
            results = tmdb.discover_tv(
                year_from=args.get("year_from"),
                year_to=args.get("year_to"),
                with_genres=genre_ids or None,
            )

        cards: List[TitleCard] = []
        for item in results:
            tmdb_id = int(item.get("id") or 0)
            if tmdb_id in owned:
                continue
            card = _tmdb_card(item, media_type, tmdb, reason="Missing from your collection")
            cards.append(card)
            if len(cards) >= 12:
                break
        self._cards.extend(cards)
        return json.dumps({"missing_count": len(cards), "titles": [c.title for c in cards]})

    async def _tool_recommend_hidden_gems(self, args: Mapping[str, Any]) -> str:
        media_type = str(args.get("media_type") or "movie")
        if not self.settings.tmdb_api_key:
            return json.dumps({"error": "TMDB API key not configured"})
        tmdb = TMDBClient(self.settings.tmdb_api_key)
        query = str(args.get("query") or "")
        if media_type == "movie":
            results = tmdb.discover_movies(sort_by="vote_average.desc", page=1)
            if query:
                results = tmdb.search_movie(query)
        else:
            results = tmdb.discover_tv(sort_by="vote_average.desc", page=1)
            if query:
                results = tmdb.search_tv(query)
        owned = self.db.owned_tmdb_ids(media_type)
        cards = []
        for item in results:
            tmdb_id = int(item.get("id") or 0)
            if tmdb_id in owned:
                continue
            rating = float(item.get("vote_average") or 0)
            if rating < 7.0:
                continue
            cards.append(_tmdb_card(item, media_type, tmdb, reason=f"Hidden gem ({rating:.1f}/10)"))
            if len(cards) >= 10:
                break
        self._cards.extend(cards)
        return json.dumps({"count": len(cards)})

    async def _tool_suggest_purge_candidates(self, args: Mapping[str, Any]) -> str:
        cards = suggest_purge_candidates(self.db, self.settings, limit=int(args.get("limit") or 12))
        self._cards.extend(cards)
        return json.dumps({"count": len(cards), "titles": [c.title for c in cards]})

    async def _tool_remember_preference(self, args: Mapping[str, Any]) -> str:
        from curatorx.models.schemas import PreferenceSignal

        remember_preference(
            self.db,
            PreferenceSignal(signal_type="explicit", text=str(args.get("text") or "")),
        )
        return json.dumps({"saved": True})

    async def _tool_add_to_radarr(self, args: Mapping[str, Any]) -> str:
        token = uuid.uuid4().hex
        payload = {
            "action": "add_radarr",
            "tmdb_id": int(args["tmdb_id"]),
            "title": str(args.get("title") or ""),
        }
        self.db.save_pending_action(token, "add_radarr", payload)
        self._pending_tokens.append(token)
        return json.dumps({"confirmation_token": token, "message": "Awaiting user confirmation to add to Radarr"})

    async def _tool_add_to_sonarr(self, args: Mapping[str, Any]) -> str:
        token = uuid.uuid4().hex
        payload = {
            "action": "add_sonarr",
            "tvdb_id": int(args["tvdb_id"]),
            "title": str(args.get("title") or ""),
        }
        self.db.save_pending_action(token, "add_sonarr", payload)
        self._pending_tokens.append(token)
        return json.dumps({"confirmation_token": token, "message": "Awaiting user confirmation to add to Sonarr"})

    async def _tool_remove_from_arr(self, args: Mapping[str, Any]) -> str:
        token = uuid.uuid4().hex
        payload = {
            "action": "remove_arr",
            "media_type": str(args.get("media_type") or "movie"),
            "arr_id": int(args["arr_id"]),
            "title": str(args.get("title") or ""),
            "delete_files": bool(args.get("delete_files")),
        }
        self.db.save_pending_action(token, "remove_arr", payload)
        self._pending_tokens.append(token)
        return json.dumps({"confirmation_token": token, "message": "Awaiting user confirmation to remove"})

    async def _tool_get_title_detail(self, args: Mapping[str, Any]) -> str:
        media_type = str(args.get("media_type") or "movie")
        kwargs: Dict[str, Any] = {"media_type": media_type}
        if args.get("rating_key"):
            kwargs["rating_key"] = str(args["rating_key"])
        elif args.get("tvdb_id"):
            kwargs["tvdb_id"] = int(args["tvdb_id"])
        elif args.get("tmdb_id"):
            kwargs["tmdb_id"] = int(args["tmdb_id"])
        else:
            return json.dumps({"error": "Provide tmdb_id, tvdb_id, or rating_key"})
        detail = get_title_detail(self.db, self.settings, **kwargs)
        card = TitleCard.model_validate(detail.model_dump())
        self._cards.append(card)
        return json.dumps({"title": detail.title, "in_library": detail.in_library, "overview": detail.overview[:200]})

    async def _tool_explore_genre(self, args: Mapping[str, Any]) -> str:
        genre = str(args.get("genre") or "").lower()
        media_type = str(args.get("media_type") or "movie")
        include_missing = bool(args.get("include_missing", True))
        cards: List[TitleCard] = []
        for row in self.db.all_library_items():
            if row["media_type"] != media_type:
                continue
            genres = json.loads(row["genres"]) if row["genres"] else []
            if any(genre in g.lower() for g in genres):
                cards.append(row_to_title_card(row, reason=f"In library · {genre.title()}"))
        if include_missing and self.settings.tmdb_api_key:
            tmdb = TMDBClient(self.settings.tmdb_api_key)
            owned = self.db.owned_tmdb_ids(media_type)
            genre_list = tmdb.genre_list_movies() if media_type == "movie" else tmdb.genre_list_tv()
            genre_ids = [str(g["id"]) for g in genre_list if genre in str(g.get("name", "")).lower()]
            if genre_ids:
                if media_type == "movie":
                    results = tmdb.discover_movies(with_genres=",".join(genre_ids))
                else:
                    results = tmdb.discover_tv(with_genres=",".join(genre_ids))
                for item in results:
                    tmdb_id = int(item.get("id") or 0)
                    if tmdb_id in owned:
                        continue
                    if media_type == "show" and not item.get("external_ids"):
                        try:
                            details = tmdb.tv_details(tmdb_id)
                            item = {**item, "external_ids": details.get("external_ids") or {}}
                        except RuntimeError:
                            pass
                    cards.append(_tmdb_card(item, media_type, tmdb, reason=f"Not in library · {genre.title()}"))
                    if len(cards) >= 16:
                        break
        self._cards.extend(cards[:16])
        return json.dumps({"count": len(cards[:16]), "genre": genre, "titles": [c.title for c in cards[:16]]})

    async def _tool_what_to_watch_tonight(self, args: Mapping[str, Any]) -> str:
        media_type = args.get("media_type")
        mood = str(args.get("mood") or "").lower()
        limit = int(args.get("limit") or 8)
        if mood:
            cards = await search_library(self.db, self.settings, mood, media_type=media_type, limit=limit * 2)
        else:
            candidates: List[tuple[int, TitleCard]] = []
            for row in self.db.all_library_items():
                if media_type and row["media_type"] != media_type:
                    continue
                view_count = int(row["view_count"] or 0)
                if view_count > 2:
                    continue
                score = (3 - view_count) * 10
                if row["last_viewed_at"]:
                    score -= 2
                candidates.append((score, row_to_title_card(row, reason="Good pick for tonight")))
            candidates.sort(key=lambda item: item[0], reverse=True)
            cards = [card for _, card in candidates[:limit]]
        self._cards.extend(cards[:limit])
        return json.dumps({"count": len(cards[:limit]), "titles": [c.title for c in cards[:limit]]})

    async def _tool_analyze_watch_patterns(self, args: Mapping[str, Any]) -> str:
        del args
        genre_counts: Dict[str, int] = {}
        total_views = 0
        unwatched = 0
        stale = 0
        now = time.time()
        for row in self.db.all_library_items():
            views = int(row["view_count"] or 0)
            total_views += views
            if views == 0:
                unwatched += 1
            last = row["last_viewed_at"]
            if last and (now - int(last)) > 365 * 24 * 3600:
                stale += 1
            for genre in json.loads(row["genres"]) if row["genres"] else []:
                genre_counts[genre] = genre_counts.get(genre, 0) + max(views, 1)
        top_genres = sorted(genre_counts.items(), key=lambda item: item[1], reverse=True)[:8]
        summary = {
            "total_items": len(self.db.all_library_items()),
            "total_plays": total_views,
            "unwatched_count": unwatched,
            "stale_count": stale,
            "top_genres": [{"genre": g, "weight": c} for g, c in top_genres],
        }
        return json.dumps(summary)


async def execute_confirmed_action(db: Database, settings: Settings, token: str) -> dict:
    payload = db.pop_pending_action(token)
    if not payload:
        raise RuntimeError("Invalid or expired confirmation token")
    action = payload.get("action")
    if action == "add_radarr":
        if not settings.radarr_url or not settings.radarr_api_key:
            raise RuntimeError("Radarr is not configured")
        client = RadarrClient(settings.radarr_url, settings.radarr_api_key)
        result = client.add_movie(
            int(payload["tmdb_id"]),
            root_folder=settings.radarr_root_folder,
            quality_profile_id=settings.radarr_quality_profile_id,
        )
        return {"action": action, "result": result}
    if action == "add_sonarr":
        if not settings.sonarr_url or not settings.sonarr_api_key:
            raise RuntimeError("Sonarr is not configured")
        client = SonarrClient(settings.sonarr_url, settings.sonarr_api_key)
        result = client.add_series(
            int(payload["tvdb_id"]),
            root_folder=settings.sonarr_root_folder,
            quality_profile_id=settings.sonarr_quality_profile_id,
        )
        return {"action": action, "result": result}
    if action == "remove_arr":
        delete_files = bool(payload.get("delete_files"))
        if payload.get("media_type") == "movie":
            RadarrClient(settings.radarr_url, settings.radarr_api_key).delete_movie(
                int(payload["arr_id"]), delete_files=delete_files
            )
        else:
            SonarrClient(settings.sonarr_url, settings.sonarr_api_key).delete_series(
                int(payload["arr_id"]), delete_files=delete_files
            )
        return {"action": action, "removed": True}
    raise RuntimeError(f"Unknown action {action}")


def _persona_prompt_block(db: Database) -> str:
    persona = db.get_persona()
    if not persona:
        return ""
    name = str(persona["curator_name"] or "Curator")
    bro = float(persona["val_bro_prof"] or 0.5)
    snark = float(persona["val_dipl_snark"] or 0.5)
    auto = float(persona["val_pass_auto"] or 0.5)
    vocab = "casual and colloquial" if bro < 0.35 else ("professorial and precise" if bro > 0.65 else "balanced")
    friction = "diplomatic and supportive" if snark < 0.35 else ("snarky and blunt" if snark > 0.65 else "even-tempered")
    autonomy = "passive — suggest only" if auto < 0.35 else ("autonomous — propose concrete next steps" if auto > 0.65 else "collaborative")
    return (
        f"Your name is {name}. "
        f"Vocabulary density: {vocab} ({bro:.2f}). "
        f"Interaction friction: {friction} ({snark:.2f}). "
        f"Automation autonomy: {autonomy} ({auto:.2f}).\n"
    )


def build_system_prompt(db: Database, lens_id: Optional[str] = None) -> str:
    from curatorx.library.db import DEFAULT_LENS_ID

    resolved = lens_id or db.get_active_lens_id() or DEFAULT_LENS_ID
    lens = db.get_lens(resolved)
    lens_name = str(lens["lens_name"]) if lens else resolved
    lens_desc = str(lens["description"] or "").strip() if lens else ""
    lens_block = f"Active curation lens: {lens_name} ({resolved})."
    if lens_desc:
        lens_block += f" Focus: {lens_desc}"
    persona = db.get_persona()
    curator_name = str(persona["curator_name"]) if persona else "Curator"
    return (
        f"You are {curator_name}, an expert movie and TV collection curator for CuratorX. "
        "You know the user's Plex library and help them discover what to add, what to watch tonight, "
        "and what to purge to save drive space. Use tools to ground recommendations in their actual library. "
        "Explain why each recommendation fits their taste. Never add or remove titles without confirmation tokens.\n"
        f"{_persona_prompt_block(db)}"
        f"{lens_block}\n\n"
        + preference_context(db, lens_id=resolved)
    )
