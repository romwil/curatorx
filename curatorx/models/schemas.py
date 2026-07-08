"""Pydantic schemas for API and agent payloads."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


MediaType = Literal["movie", "show"]


class TitleCard(BaseModel):
    media_type: MediaType
    title: str
    year: Optional[int] = None
    tmdb_id: Optional[int] = None
    tvdb_id: Optional[int] = None
    rating_key: Optional[str] = None
    poster_url: str = ""
    backdrop_url: str = ""
    overview: str = ""
    rating: Optional[float] = None
    genres: List[str] = Field(default_factory=list)
    in_library: bool = False
    in_radarr: bool = False
    in_sonarr: bool = False
    recommendation_reason: str = ""
    runtime_minutes: Optional[int] = None


class TitleDetail(TitleCard):
    cast: List[str] = Field(default_factory=list)
    directors: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    file_size_bytes: int = 0
    view_count: int = 0
    last_viewed_at: Optional[int] = None
    arr_id: Optional[int] = None
    purge_score: Optional[float] = None
    purge_reason: str = ""


class ChatMessageBlock(BaseModel):
    type: Literal["text", "title_cards", "action_prompt"]
    content: str = ""
    items: List[TitleCard] = Field(default_factory=list)
    action: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    id: str
    role: Literal["user", "assistant", "system"]
    blocks: List[ChatMessageBlock] = Field(default_factory=list)
    created_at: float = 0
    lens_id: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    lens_id: Optional[str] = None


class ActionConfirmRequest(BaseModel):
    token: str
    confirmed: bool = True


class PreferenceSignal(BaseModel):
    signal_type: Literal["explicit", "positive", "negative", "add", "dismiss"]
    text: str = ""
    tmdb_id: Optional[int] = None
    tvdb_id: Optional[int] = None
    media_type: Optional[MediaType] = None
    lens_id: Optional[str] = None
    cluster_tag: Optional[str] = None
    weight: Optional[float] = None
    explicit_lock: Optional[bool] = None


class ViewportPayload(BaseModel):
    title: str = ""
    items: List[TitleCard] = Field(default_factory=list)


class Lens(BaseModel):
    lens_id: str
    lens_name: str
    description: str = ""
    created_at: Optional[str] = None


class LensCreate(BaseModel):
    lens_id: str = Field(..., min_length=1)
    lens_name: str = Field(..., min_length=1)
    description: str = ""


class LensUpdate(BaseModel):
    lens_name: Optional[str] = None
    description: Optional[str] = None


class ActiveLensPayload(BaseModel):
    lens_id: str


class PersonaPresetSummary(BaseModel):
    id: str
    name: str
    description: str
    val_bro_prof: float
    val_dipl_snark: float
    val_pass_auto: float
    identity_blurb: str = ""


class PersonaMetrics(BaseModel):
    metric_id: str = "current_profile"
    curator_name: str = "Curator"
    persona_identity: str = ""
    val_bro_prof: float = Field(default=0.5, ge=0.0, le=1.0)
    val_dipl_snark: float = Field(default=0.5, ge=0.0, le=1.0)
    val_pass_auto: float = Field(default=0.5, ge=0.0, le=1.0)
    persona_preset_id: Optional[str] = None
    persona_prompt_override: Optional[str] = None
    persona_mode: str = "sliders"
    behavioral_prompt: str = ""
    assembled_prompt: str = ""
    last_modified: Optional[str] = None


class PersonaMetricsUpdate(BaseModel):
    curator_name: Optional[str] = None
    persona_identity: Optional[str] = None
    val_bro_prof: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    val_dipl_snark: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    val_pass_auto: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    persona_preset_id: Optional[str] = None
    persona_prompt_override: Optional[str] = None
    clear_persona_override: bool = False
    apply_preset: Optional[str] = None


class PersonaPreviewResponse(BaseModel):
    persona_mode: str
    behavioral_prompt: str
    assembled_prompt: str


class SystemConfigEntry(BaseModel):
    config_key: str
    config_value: str


class SystemConfigUpdate(BaseModel):
    values: Dict[str, str] = Field(default_factory=dict)


class LensTasteEntry(BaseModel):
    lens_id: str
    cluster_tag: str
    weight: float = 1.0
    explicit_lock: bool = False
    last_updated: Optional[str] = None
