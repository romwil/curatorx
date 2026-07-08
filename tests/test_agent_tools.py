"""Tests for agent tools."""

import json
import tempfile
import unittest
from pathlib import Path

from curatorx.agent.tools import TOOL_DEFINITIONS, ToolRegistry, build_system_prompt
from curatorx.config_store import Settings
from curatorx.library.db import DEFAULT_LENS_ID, Database


class ToolRegistryTests(unittest.IsolatedAsyncioTestCase):
    async def test_remember_preference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.db")
            registry = ToolRegistry(db, Settings(), DEFAULT_LENS_ID)
            result = await registry.execute("remember_preference", {"text": "loves 70s sci-fi"})
            self.assertIn("saved", result)
            self.assertIn("70s", build_system_prompt(db, lens_id=DEFAULT_LENS_ID))

    async def test_remember_preference_uses_agent_lens_not_active_lens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.db")
            db.create_lens("noir", "Noir Studies", "Hardboiled crime cinema")
            db.set_active_lens_id(DEFAULT_LENS_ID)

            registry = ToolRegistry(db, Settings(), "noir")
            result = await registry.execute("remember_preference", {"text": "loves neo-noir"})
            self.assertIn("saved", result)

            noir_taste = db.get_lens_taste_profile("noir")
            general_taste = db.get_lens_taste_profile(DEFAULT_LENS_ID)
            self.assertEqual(len(noir_taste), 1)
            self.assertIn("neo-noir", noir_taste[0]["cluster_tag"])
            self.assertEqual(len(general_taste), 0)
            self.assertIn("neo-noir", build_system_prompt(db, lens_id="noir"))

    async def test_analyze_watch_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.db")
            db.upsert_library_item(
                {
                    "rating_key": "1",
                    "media_type": "movie",
                    "title": "Test Movie",
                    "genres": ["Sci-Fi"],
                    "view_count": 0,
                }
            )
            registry = ToolRegistry(db, Settings(), DEFAULT_LENS_ID)
            result = await registry.execute("analyze_watch_patterns", {})
            payload = json.loads(result)
            self.assertEqual(payload["unwatched_count"], 1)

    def test_tool_definitions_include_new_tools(self) -> None:
        names = {tool["function"]["name"] for tool in TOOL_DEFINITIONS}
        for expected in (
            "get_title_detail",
            "explore_genre",
            "what_to_watch_tonight",
            "analyze_watch_patterns",
        ):
            self.assertIn(expected, names)

    def test_system_prompt_includes_persona_and_lens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.db")
            db.upsert_persona(curator_name="Atlas", val_bro_prof=0.9)
            db.create_lens("noir", "Noir Studies", "Hardboiled crime cinema")
            prompt = build_system_prompt(db, lens_id="noir")
            self.assertIn("Atlas", prompt)
            self.assertIn("Noir Studies", prompt)
            self.assertIn("Hardboiled", prompt)
            self.assertIn(DEFAULT_LENS_ID, build_system_prompt(db, lens_id=DEFAULT_LENS_ID) or "")


if __name__ == "__main__":
    unittest.main()
