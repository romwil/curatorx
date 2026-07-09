"""Tests for library facet index."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from curatorx.library.db import Database
from curatorx.library.facets import library_facet_catalog, rebuild_library_facets
from curatorx.library.query import LibraryFilters, query_library


class LibraryFacetTests(unittest.TestCase):
    def test_rebuild_and_filter_by_director(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.db")
            db.upsert_library_item(
                {
                    "rating_key": "nolan-1",
                    "media_type": "movie",
                    "title": "Inception",
                    "year": 2010,
                    "genres": ["Sci-Fi"],
                    "directors": ["Christopher Nolan"],
                    "cast": ["Leonardo DiCaprio"],
                    "keywords": ["dream"],
                }
            )
            db.upsert_library_item(
                {
                    "rating_key": "other-1",
                    "media_type": "movie",
                    "title": "Jaws",
                    "year": 1975,
                    "genres": ["Thriller"],
                    "directors": ["Steven Spielberg"],
                }
            )
            count = rebuild_library_facets(db)
            self.assertGreaterEqual(count, 3)

            catalog = library_facet_catalog(db, "director", limit=10)
            self.assertEqual(catalog["facet_type"], "director")
            values = {entry["value"] for entry in catalog["facets"]}
            self.assertIn("Christopher Nolan", values)

            result = query_library(db, LibraryFilters(directors=["Nolan"], media_type="movie"))
            self.assertEqual(result["total_matched"], 1)
            self.assertEqual(result["items"][0]["title"], "Inception")

    def test_country_and_language_catalog_from_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.db")
            db.upsert_library_item(
                {
                    "rating_key": "intl",
                    "media_type": "movie",
                    "title": "Amelie",
                    "countries": ["France"],
                    "original_language": "fr",
                }
            )
            country_catalog = library_facet_catalog(db, "country", limit=10)
            language_catalog = library_facet_catalog(db, "language", limit=10)
            self.assertEqual(country_catalog["facets"][0]["value"], "France")
            self.assertEqual(language_catalog["facets"][0]["value"], "fr")

    def test_ensure_library_facet_index_backfills_country_language(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.db")
            db.upsert_library_item(
                {
                    "rating_key": "intl",
                    "media_type": "movie",
                    "title": "Amelie",
                    "countries": ["France"],
                    "original_language": "fr",
                }
            )
            from curatorx.library.facets import ensure_library_facet_index

            rebuilt = ensure_library_facet_index(db)
            self.assertGreater(rebuilt, 0)
            catalog = library_facet_catalog(db, "country", limit=10)
            self.assertEqual(catalog["facets"][0]["value"], "France")


if __name__ == "__main__":
    unittest.main()
