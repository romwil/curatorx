"""Pydantic schemas for API and agent payloads."""

from __future__ import annotations

from typing import Any, List, Literal, Optional, Union

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


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ActionConfirmRequest(BaseModel):
    token: str
    confirmed: bool = True


class PreferenceSignal(BaseModel):
    signal_type: Literal["explicit", "positive", "negative", "add", "dismiss"]
    text: str = ""
    tmdb_id: Optional[int] = None
    tvdb_id: Optional[int] = None
    media_type: Optional[MediaType] = None


class ViewportPayload(BaseModel):
    title: str = ""
    items: List[TitleCard] = Field(default_factory=list)
