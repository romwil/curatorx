"""Persona presets and prompt assembly."""

from curatorx.persona.presets import PERSONA_PRESETS, get_preset, list_presets
from curatorx.persona.prompt import (
    CURATOR_NAME_PLACEHOLDER,
    build_assembled_persona_prompt,
    build_behavioral_prompt_from_sliders,
    build_persona_prompt,
    build_rendered_behavioral_prompt,
    derive_persona_mode,
    persona_row_to_dict,
    slider_band,
    substitute_curator_name,
)

__all__ = [
    "PERSONA_PRESETS",
    "CURATOR_NAME_PLACEHOLDER",
    "build_assembled_persona_prompt",
    "build_behavioral_prompt_from_sliders",
    "build_persona_prompt",
    "build_rendered_behavioral_prompt",
    "derive_persona_mode",
    "get_preset",
    "list_presets",
    "persona_row_to_dict",
    "slider_band",
    "substitute_curator_name",
]
