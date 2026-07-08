"""Tests for library database."""

import tempfile
import unittest
from pathlib import Path

from curatorx.library.db import DEFAULT_LENS_ID, Database


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

    def test_prd_schema_tables_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.db")
            expected = {
                "curator_system_config",
                "service_integrations",
                "curator_persona_metrics",
                "curation_lenses",
                "lens_taste_profile",
                "interaction_telemetry",
                "agent_blueprints",
            }
            with db.connect() as conn:
                rows = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
                names = {str(r["name"]) for r in rows}
            self.assertTrue(expected.issubset(names))

    def test_persona_and_general_lens_seeded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.db")
            lens = db.get_lens(DEFAULT_LENS_ID)
            self.assertIsNotNone(lens)
            self.assertEqual(lens["lens_name"], "General")
            persona = db.get_persona()
            self.assertIsNotNone(persona)
            self.assertEqual(persona["metric_id"], "current_profile")
            self.assertEqual(db.get_active_lens_id(), DEFAULT_LENS_ID)

    def test_lens_chat_isolation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.db")
            db.create_lens("directors", "Director Studies", "Focus on directors")
            session = "session-a"
            db.ensure_chat_session(session, DEFAULT_LENS_ID)
            db.save_chat_message(
                session,
                "m1",
                "user",
                [{"type": "text", "content": "general hello"}],
                lens_id=DEFAULT_LENS_ID,
            )
            db.save_chat_message(
                session,
                "m2",
                "user",
                [{"type": "text", "content": "director hello"}],
                lens_id="directors",
            )
            general = db.chat_history(session, lens_id=DEFAULT_LENS_ID)
            directors = db.chat_history(session, lens_id="directors")
            self.assertEqual(len(general), 1)
            self.assertEqual(general[0]["blocks"][0]["content"], "general hello")
            self.assertEqual(len(directors), 1)
            self.assertEqual(directors[0]["blocks"][0]["content"], "director hello")

    def test_lens_taste_explicit_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.db")
            db.set_lens_taste_weight(DEFAULT_LENS_ID, "70s-sci-fi", 2.0, explicit_lock=True)
            db.set_lens_taste_weight(DEFAULT_LENS_ID, "70s-sci-fi", 0.1, respect_lock=True)
            rows = db.get_lens_taste_profile(DEFAULT_LENS_ID)
            self.assertEqual(len(rows), 1)
            self.assertEqual(float(rows[0]["weight"]), 2.0)
            self.assertEqual(int(rows[0]["explicit_lock"]), 1)


if __name__ == "__main__":
    unittest.main()
