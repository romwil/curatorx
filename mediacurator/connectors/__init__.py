"""Connector clients for external services."""

from mediacurator.connectors.fanart import FanartClient
from mediacurator.connectors.http import optional_int, parse_plex_guid, request_json, request_xml
from mediacurator.connectors.plex import PlexClient, PlexLibraryItem, PlexSection
from mediacurator.connectors.radarr import RadarrClient
from mediacurator.connectors.sonarr import SonarrClient
from mediacurator.connectors.tautulli import TautulliClient
from mediacurator.connectors.tmdb import TMDBClient
from mediacurator.connectors.tvdb import TVDBClient

__all__ = [
    "FanartClient",
    "PlexClient",
    "PlexLibraryItem",
    "PlexSection",
    "RadarrClient",
    "SonarrClient",
    "TMDBClient",
    "TVDBClient",
    "TautulliClient",
    "optional_int",
    "parse_plex_guid",
    "request_json",
    "request_xml",
]
