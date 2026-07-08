"""Tests for library database."""

import tempfile
import unittest
from pathlib import Path

from mediacurator.library.db import Database


class DatabaseTests(unittest.TestCase):
    def test_upsert_and_search(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.db")
            item_id = db.upsert_library_item(
                {
                    "rating_key": "1",
                    "media_type": "movie",
                    "title": "Blade Runner",
                    "year": 1982,
                    "summary": "Sci-fi noir",
                    "genres": ["Sci-Fi"],
                    "cast": [],
                    "directors": [],
                    "keywords": ["dystopia"],
                    "tmdb_id": 78,
                }
            )
            self.assertGreater(item_id, 0)
            rows = db.search_keyword("blade")
            self.assertEqual(len(rows), 1)
            self.assertIn(78, db.owned_tmdb_ids("movie"))

    def test_pending_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.db")
            db.save_pending_action("token1", "add_radarr", {"tmdb_id": 123})
            payload = db.pop_pending_action("token1")
            self.assertEqual(payload["tmdb_id"], 123)
            self.assertIsNone(db.pop_pending_action("token1"))


if __name__ == "__main__":
    unittest.main()
