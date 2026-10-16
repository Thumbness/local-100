import os

import spotipy
from spotipy.cache_handler import MemoryCacheHandler
from spotipy.oauth2 import SpotifyOAuth

from .client import SpotifyClient
from .session import build_session

SCOPE = " ".join([
    "user-library-read",
    "user-top-read",
    "user-follow-read",
    "playlist-read-private",
    "playlist-read-collaborative",
])
DEFAULT_REDIRECT_URI = "http://127.0.0.1:5000/library/callback"


def configured_redirect_uri() -> str:
    """Where Spotify sends users back after login. It must match a Redirect URI in the Spotify app settings."""
    return os.getenv("LIBRARY_REDIRECT_URI") or os.getenv("REDIRECT_URI") or DEFAULT_REDIRECT_URI


def build_oauth(cache_handler, redirect_uri: str | None = None) -> SpotifyOAuth:
    return SpotifyOAuth(
        client_id=os.getenv("CLIENT_ID"),
        client_secret=os.getenv("CLIENT_SECRET"),
        redirect_uri=redirect_uri or configured_redirect_uri(),
        scope=SCOPE,
        cache_handler=cache_handler,
        show_dialog=False,
    )


def client_for(auth: SpotifyOAuth) -> SpotifyClient:
    """A client that retries short rate limits and raises SpotifyRateLimited on long ones."""
    sp = spotipy.Spotify(auth_manager=auth, requests_session=build_session(), requests_timeout=15)
    return SpotifyClient(sp)


def client_from_token(token_info: dict) -> SpotifyClient:
    """A client for a user whose tokens are already known. Refreshes the token itself if needed."""
    return client_for(build_oauth(MemoryCacheHandler(token_info=token_info)))
