"""Prints albums released in a given year by artists in your Spotify library (browser login).

Run from the project root: python -m src.cli.spotify_report [year]
"""
import os
import sys

from dotenv import load_dotenv
from spotipy.cache_handler import MemoryCacheHandler

from ..application.albums.find_albums import find_album_releases
from ..config.AppConfig import APP_HOME
from ..infrastructure.spotify.auth import build_oauth, client_for

DEFAULT_YEAR = 2016
DEFAULT_REDIRECT_URI = "http://127.0.0.1:8888/callback"


def main(argv=None):
    load_dotenv(APP_HOME / ".env")
    argv = sys.argv[1:] if argv is None else argv
    year = int(argv[0]) if argv else DEFAULT_YEAR

    auth = build_oauth(MemoryCacheHandler(), redirect_uri=os.getenv("REDIRECT_URI") or DEFAULT_REDIRECT_URI)
    spotify = client_for(auth)

    releases = find_album_releases(spotify, year, lambda message, done=None, total=None, details=None: None)
    print(f"\nAlbums released in {year} by artists you've listened to: {len(releases)}\n")
    for r in releases:
        print(f"  {r.artist:25s} – {r.album:40s} [{r.type}] [{r.release_date}]")


if __name__ == "__main__":
    main()
