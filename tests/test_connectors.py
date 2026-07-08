"""Tests for HTTP helpers and TVDB client."""

import unittest

from mediacurator.connectors.http import parse_plex_guid
from mediacurator.connectors.tvdb import TVDBClient


class HttpHelperTests(unittest.TestCase):
    def test_parse_plex_guid(self) -> None:
        ids = parse_plex_guid("com.plexapp.agents.themoviedb://12345?lang=en")
        self.assertEqual(ids["tmdb_id"], "12345")


class TVDBClientTests(unittest.TestCase):
    def test_base_url(self) -> None:
        client = TVDBClient("test-key")
        self.assertEqual(client.base_url, "https://api4.thetvdb.com/v4")


if __name__ == "__main__":
    unittest.main()
