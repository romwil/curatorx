"""Tests for persona prompt assembly and presets."""

from __future__ import annotations

import importlib
import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from curatorx.library.db import Database
from curatorx.persona import (
    build_assembled_persona_prompt,
    build_behavioral_prompt_from_sliders,
    build_persona_prompt,
    derive_persona_mode,
    get_preset,
)
from curatorx.persona.presets import PERSONA_PRESETS


class PersonaPromptTests(unittest.TestCase):
    def test_derive_persona_mode_from_override(self) -> None:
        self.assertEqual(derive_persona_mode({"persona_prompt_override": "Custom tone"}), "custom")
        self.assertEqual(derive_persona_mode({"persona_prompt_override": ""}), "sliders")
        self.assertEqual(derive_persona_mode({}), "sliders")

    def test_build_persona_prompt_concatenates_identity_and_behavior(self) -> None:
        persona = {
            "curator_name": "Atlas",
            "persona_identity": "I am a noir obsessive.",
            "val_bro_prof": 0.5,
            "val_dipl_snark": 0.5,
            "val_pass_auto": 0.5,
        }
        prompt = build_persona_prompt(persona)
        self.assertIn("I am a noir obsessive.", prompt)
        self.assertIn("Atlas", prompt)
        self.assertIn("Vocabulary density", prompt)

    def test_override_replaces_slider_behavioral_text(self) -> None:
        persona = {
            "curator_name": "Atlas",
            "persona_identity": "Core identity stays.",
            "persona_prompt_override": "Always speak in haiku.",
            "val_bro_prof": 0.9,
            "val_dipl_snark": 0.1,
            "val_pass_auto": 0.5,
        }
        prompt = build_persona_prompt(persona)
        self.assertIn("Core identity stays.", prompt)
        self.assertIn("Always speak in haiku.", prompt)
        self.assertNotIn("Vocabulary density", prompt)

    def test_preset_values_exist(self) -> None:
        self.assertGreaterEqual(len(PERSONA_PRESETS), 8)
        scholar = get_preset("film-scholar")
        assert scholar is not None
        self.assertGreater(scholar.val_bro_prof, 0.7)

    def test_apply_preset_via_db(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.db")
            preset = get_preset("enthusiastic-friend")
            assert preset is not None
            row = db.upsert_persona(
                persona_preset_id=preset.id,
                val_bro_prof=preset.val_bro_prof,
                val_dipl_snark=preset.val_dipl_snark,
                val_pass_auto=preset.val_pass_auto,
                persona_identity=preset.identity_blurb,
            )
            self.assertEqual(float(row["val_bro_prof"]), preset.val_bro_prof)
            self.assertEqual(str(row["persona_preset_id"]), preset.id)

    def test_clear_override_regenerates_behavioral_prompt(self) -> None:
        persona = {
            "curator_name": "Curator",
            "persona_prompt_override": "Custom only.",
            "val_bro_prof": 0.2,
            "val_dipl_snark": 0.8,
            "val_pass_auto": 0.4,
        }
        cleared = {**persona, "persona_prompt_override": None}
        behavioral = build_behavioral_prompt_from_sliders(cleared)
        self.assertIn("casual", behavioral)
        self.assertIn("snarky", behavioral.lower())

    def test_assembled_prompt_matches_identity_plus_behavior(self) -> None:
        persona = {
            "curator_name": "Morgan",
            "persona_identity": "Line one.",
            "val_bro_prof": 0.5,
            "val_dipl_snark": 0.5,
            "val_pass_auto": 0.5,
        }
        assembled = build_assembled_persona_prompt(persona)
        self.assertTrue(assembled.startswith("Line one."))
        self.assertIn("Morgan", assembled)


class PersonaApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        os.environ["DATA_DIR"] = self._tmpdir.name
        os.environ["CURATORX_SKIP_DOTENV"] = "1"
        os.environ["LLM_PROVIDER"] = "ollama"
        import curatorx.web.jobs as jobs

        jobs._manager = None
        import curatorx.web.app as app_mod

        importlib.reload(app_mod)
        self.client = TestClient(app_mod.app)

    def tearDown(self) -> None:
        import curatorx.web.jobs as jobs

        jobs._manager = None
        os.environ.pop("CURATORX_SKIP_DOTENV", None)
        os.environ.pop("LLM_PROVIDER", None)
        self._tmpdir.cleanup()

    def test_persona_payload_includes_new_fields(self) -> None:
        resp = self.client.get("/api/persona")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        for key in (
            "persona_identity",
            "persona_preset_id",
            "persona_prompt_override",
            "persona_mode",
            "behavioral_prompt",
            "assembled_prompt",
        ):
            self.assertIn(key, body)
        self.assertEqual(body["persona_mode"], "sliders")

    def test_persona_presets_list(self) -> None:
        resp = self.client.get("/api/persona/presets")
        self.assertEqual(resp.status_code, 200)
        presets = resp.json()
        self.assertGreaterEqual(len(presets), 8)
        ids = {item["id"] for item in presets}
        self.assertIn("film-scholar", ids)
        self.assertIn("enthusiastic-friend", ids)

    def test_custom_override_blocks_slider_change_until_confirmed(self) -> None:
        put = self.client.put(
            "/api/persona",
            json={"persona_prompt_override": "Speak like a pirate."},
        )
        self.assertEqual(put.status_code, 200)
        self.assertEqual(put.json()["persona_mode"], "custom")

        conflict = self.client.put("/api/persona", json={"val_bro_prof": 0.9})
        self.assertEqual(conflict.status_code, 409)

        cleared = self.client.put(
            "/api/persona",
            json={"val_bro_prof": 0.9, "clear_persona_override": True},
        )
        self.assertEqual(cleared.status_code, 200)
        self.assertEqual(cleared.json()["persona_mode"], "sliders")
        self.assertIn("professorial", cleared.json()["behavioral_prompt"])

    def test_apply_preset_endpoint(self) -> None:
        resp = self.client.put("/api/persona", json={"apply_preset": "film-scholar"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["persona_preset_id"], "film-scholar")
        self.assertGreater(body["val_bro_prof"], 0.7)

    def test_persona_preview_endpoint(self) -> None:
        resp = self.client.get("/api/persona/preview", params={"persona_identity": "Preview identity"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("Preview identity", body["assembled_prompt"])


if __name__ == "__main__":
    unittest.main()
