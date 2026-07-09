"""Shared helpers for Radarr/Sonarr validation errors."""

from __future__ import annotations

import json
from typing import Optional


class ArrTitleExistsError(RuntimeError):
    """Raised when a title is already present in Radarr or Sonarr."""

    def __init__(
        self,
        service: str,
        *,
        title: str = "",
        external_id: int = 0,
        arr_id: Optional[int] = None,
    ) -> None:
        self.service = service
        self.title = title
        self.external_id = external_id
        self.arr_id = arr_id
        label = title or f"ID {external_id}" if external_id else "This title"
        super().__init__(f'"{label}" is already in {service}')


def _extract_http_error_body(error: Exception) -> str:
    message = str(error)
    if ": " in message:
        return message.split(": ", 1)[-1]
    return message


def arr_exists_error_code(body: str, *, movie: bool = True) -> bool:
    code = "MovieExistsValidator" if movie else "SeriesExistsValidator"
    if code in body:
        return True
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return False
    if isinstance(data, list):
        return any(
            isinstance(item, dict) and item.get("errorCode") == code for item in data
        )
    if isinstance(data, dict):
        return data.get("errorCode") == code
    return False


def is_arr_exists_error(error: Exception, *, movie: bool = True) -> bool:
    if isinstance(error, ArrTitleExistsError):
        return True
    return arr_exists_error_code(_extract_http_error_body(error), movie=movie)
