"""Persistent settings for MediaCurator."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Mapping

ENV_TO_FIELD = {
    "PLEX_URL": "plex_url",
    "PLEX_TOKEN": "plex_token",
    "PLEX_MOVIE_SECTION": "plex_movie_section",
    "PLEX_TV_SECTION": "plex_tv_section",
    "RADARR_URL": "radarr_url",
    "RADARR_API_KEY": "radarr_api_key",
    "SONARR_URL": "sonarr_url",
    "SONARR_API_KEY": "sonarr_api_key",
    "MOVIES_ROOT": "movies_root",
    "TV_ROOT": "tv_root",
    "RADARR_ROOT_FOLDER": "radarr_root_folder",
    "SONARR_ROOT_FOLDER": "sonarr_root_folder",
    "RADARR_QUALITY_PROFILE_ID": "radarr_quality_profile_id",
    "SONARR_QUALITY_PROFILE_ID": "sonarr_quality_profile_id",
    "TMDB_API_KEY": "tmdb_api_key",
    "TVDB_API_KEY": "tvdb_api_key",
    "FANART_API_KEY": "fanart_api_key",
    "TAUTULLI_URL": "tautulli_url",
    "TAUTULLI_API_KEY": "tautulli_api_key",
    "LLM_PROVIDER": "llm_provider",
    "LLM_BASE_URL": "llm_base_url",
    "LLM_API_KEY": "llm_api_key",
    "LLM_MODEL": "llm_model",
    "LLM_EMBEDDING_MODEL": "llm_embedding_model",
    "LLM_EMBEDDING_BASE_URL": "llm_embedding_base_url",
}

FIELD_TO_ENV = {value: key for key, value in ENV_TO_FIELD.items()}


@dataclass
class Settings:
    plex_url: str = ""
    plex_token: str = ""
    plex_movie_section: str = ""
    plex_tv_section: str = ""
    radarr_url: str = ""
    radarr_api_key: str = ""
    sonarr_url: str = ""
    sonarr_api_key: str = ""
    movies_root: str = "/media/movies"
    tv_root: str = "/media/tv"
    radarr_root_folder: str = "/media/movies"
    sonarr_root_folder: str = "/media/tv"
    radarr_quality_profile_id: int = 1
    sonarr_quality_profile_id: int = 1
    tmdb_api_key: str = ""
    tvdb_api_key: str = ""
    fanart_api_key: str = ""
    tautulli_url: str = ""
    tautulli_api_key: str = ""
    llm_provider: str = "openai_compatible"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_embedding_model: str = "text-embedding-3-small"
    llm_embedding_base_url: str = ""
    onboarding_complete: bool = False
    setup_wizard_pending: bool = False
    library_sync_interval_hours: int = 24
    tv_page_size: int = 500

    def apply_to_environ(self) -> None:
        for env_name, field_name in ENV_TO_FIELD.items():
            value = getattr(self, field_name)
            if value is not None and value != "":
                os.environ[env_name] = str(value)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "Settings":
        known = {field.name for field in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered: Dict[str, Any] = {}
        for key in known:
            if key not in data:
                continue
            value = data[key]
            if key.endswith("_id") and value is not None:
                filtered[key] = int(value)
            elif key.endswith("_hours") or key == "tv_page_size":
                filtered[key] = int(value) if value is not None else value
            else:
                filtered[key] = value
        return cls(**filtered)

    @classmethod
    def from_env(cls) -> "Settings":
        values: Dict[str, Any] = {}
        for env_name, field_name in ENV_TO_FIELD.items():
            if env_name in os.environ:
                values[field_name] = os.environ[env_name]
        for int_field in (
            "radarr_quality_profile_id",
            "sonarr_quality_profile_id",
            "library_sync_interval_hours",
            "tv_page_size",
        ):
            env_key = FIELD_TO_ENV.get(int_field, "")
            if env_key in os.environ:
                values[int_field] = int(os.environ[env_key])
        return cls.from_mapping(values)

    @classmethod
    def load(cls, path: Path) -> "Settings":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_mapping(data)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_merged_settings(data_dir: Path) -> Settings:
    settings_path = data_dir / "settings.json"
    settings = Settings.load(settings_path)
    merged = asdict(settings)
    for env_name, field_name in ENV_TO_FIELD.items():
        if env_name not in os.environ:
            continue
        merged[field_name] = os.environ[env_name]
    for int_field in (
        "radarr_quality_profile_id",
        "sonarr_quality_profile_id",
        "library_sync_interval_hours",
        "tv_page_size",
    ):
        env_key = FIELD_TO_ENV.get(int_field, "")
        if env_key in os.environ:
            merged[int_field] = int(os.environ[env_key])
    return Settings.from_mapping(merged)


def save_settings(data_dir: Path, settings: Settings) -> Path:
    path = data_dir / "settings.json"
    settings.save(path)
    return path
