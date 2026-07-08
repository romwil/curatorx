"""Tests for agent tools."""

import json
import tempfile
import unittest
from pathlib import Path

from mediacurator.agent.tools import TOOL_DEFINITIONS, ToolRegistry, build_system_prompt
from mediacurator.config_store import Settings
from mediacurator.library.db import Database


class ToolRegistryTests(unittest.IsolatedAsyncioTestCase):
    async def test_remember_preference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.db")
            registry = ToolRegistry(db, Settings())
            result = await registry.execute("remember_preference", {"text": "loves 70s sci-fi"})
            self.assertIn("saved", result)
            self.assertIn("70s", build_system_prompt(db))

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
            registry = ToolRegistry(db, Settings())
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


if __name__ == "__main__":
    unittest.main()
