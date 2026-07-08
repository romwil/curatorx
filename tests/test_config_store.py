"""Tests for config store."""

import tempfile
import unittest
from pathlib import Path

from mediacurator.config_store import Settings, load_merged_settings, save_settings


class ConfigStoreTests(unittest.TestCase):
    def test_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            settings = Settings(plex_url="http://plex", tmdb_api_key="secret")
            save_settings(data_dir, settings)
            loaded = load_merged_settings(data_dir)
            self.assertEqual(loaded.plex_url, "http://plex")
            self.assertEqual(loaded.tmdb_api_key, "secret")

    def test_from_mapping_ignores_unknown(self) -> None:
        settings = Settings.from_mapping({"plex_url": "x", "unknown": "y"})
        self.assertEqual(settings.plex_url, "x")


if __name__ == "__main__":
    unittest.main()
