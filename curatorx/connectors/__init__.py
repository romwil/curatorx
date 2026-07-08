"""Connector clients for external services."""

from curatorx.connectors.fanart import FanartClient
from curatorx.connectors.http import optional_int, parse_plex_guid, request_json, request_xml
from curatorx.connectors.plex import PlexClient, PlexLibraryItem, PlexSection
from curatorx.connectors.radarr import RadarrClient
from curatorx.connectors.sonarr import SonarrClient
from curatorx.connectors.tautulli import TautulliClient
from curatorx.connectors.tmdb import TMDBClient
from curatorx.connectors.tvdb import TVDBClient

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
