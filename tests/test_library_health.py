"""Tests for library health metrics."""

import tempfile
import unittest
from pathlib import Path

from curatorx.library.db import Database
from curatorx.library.health import compute_library_health


class LibraryHealthTests(unittest.TestCase):
    def test_compute_library_health_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.db")
            db.upsert_library_item(
                {
                    "rating_key": "1",
                    "media_type": "movie",
                    "title": "Unwatched",
                    "view_count": 0,
                    "added_at": 1,
                }
            )
            db.upsert_library_item(
                {
                    "rating_key": "2",
                    "media_type": "movie",
                    "title": "Watched",
                    "view_count": 2,
                }
            )
            health = compute_library_health(db)
            self.assertEqual(health["total"], 2)
            self.assertEqual(health["unwatched_count"], 1)
            self.assertEqual(health["unwatched_pct"], 50.0)
            self.assertEqual(health["watched_count"], 1)
            self.assertEqual(health["rating_coverage_pct"], 0.0)


if __name__ == "__main__":
    unittest.main()
