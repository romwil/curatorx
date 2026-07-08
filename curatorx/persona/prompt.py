"""Assemble persona prompts for the Curator agent."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from curatorx.persona.presets import get_preset


def persona_row_to_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    if isinstance(row, Mapping):
        return dict(row)
    return dict(row) if hasattr(row, "keys") else {}


def derive_persona_mode(persona: Mapping[str, Any]) -> str:
    override = str(persona.get("persona_prompt_override") or "").strip()
    return "custom" if override else "sliders"


def _slider_label(value: float, low: str, mid: str, high: str) -> str:
    if value < 0.35:
        return low
    if value > 0.65:
        return high
    return mid


def build_behavioral_prompt_from_sliders(persona: Mapping[str, Any]) -> str:
    name = str(persona.get("curator_name") or "Curator")
    bro = float(persona.get("val_bro_prof") or 0.5)
    snark = float(persona.get("val_dipl_snark") or 0.5)
    auto = float(persona.get("val_pass_auto") or 0.5)

    preset_id = persona.get("persona_preset_id")
    preset = get_preset(str(preset_id) if preset_id else None)
    preset_hint = f" Preset anchor: {preset.name}." if preset else ""

    vocab = _slider_label(bro, "casual and colloquial", "balanced vocabulary", "professorial and precise")
    friction = _slider_label(snark, "diplomatic and supportive", "even-tempered", "snarky and blunt")
    autonomy = _slider_label(
        auto,
        "passive — suggest only, never act without explicit approval",
        "collaborative — propose options and wait for direction",
        "autonomous — propose concrete next steps and queue actions when appropriate",
    )

    return (
        f"Your display name is {name}.{preset_hint}\n"
        f"Vocabulary density: {vocab} (bro↔prof {bro:.2f}). "
        f"Interaction friction: {friction} (diplomatic↔snark {snark:.2f}). "
        f"Automation autonomy: {autonomy} (passive↔auto {auto:.2f}).\n"
        "Adapt tone and initiative level to these behavioral dimensions in every reply."
    )


def build_persona_prompt(persona: Mapping[str, Any]) -> str:
    """Behavioral + identity block injected into the system prompt."""
    parts: list[str] = []
    identity = str(persona.get("persona_identity") or "").strip()
    if identity:
        parts.append(identity)

    override = str(persona.get("persona_prompt_override") or "").strip()
    if override:
        parts.append(override)
    else:
        parts.append(build_behavioral_prompt_from_sliders(persona))

    if not parts:
        return ""
    return "\n\n".join(parts) + "\n"


def build_assembled_persona_prompt(persona: Mapping[str, Any]) -> str:
    """Full persona section as shown in the config preview (same as agent injection)."""
    return build_persona_prompt(persona).strip()
