"""Wires the countdown use cases to their concrete adapters. Only the entry points (web, cli) call this."""
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from .application.auth.service import AuthService
from .application.auth.throttle import LoginThrottle
from .application.countdown.service import CountdownService
from .config.AppConfig import APP_HOME, APP_PARAMS
from .infrastructure.auth.passwords import WerkzeugPasswordHasher
from .infrastructure.auth.users_file import JsonUserDirectory
from .infrastructure.ingestion.raw_format import CountdownFileFormat
from .infrastructure.persistence.countdown_store import CountdownFileStore
from .infrastructure.youtube.downloader import YouTubeVideoDownloader

load_dotenv(APP_HOME / ".env")


def countdown_service(oauth_verifier=None) -> CountdownService:
    store = CountdownFileStore(
        raw_path=APP_PARAMS["COUNTDOWN.RAW.DATA.FILEPATH"],
        results_path=APP_PARAMS["COUNTDOWN.RESULTS.DATA.FILEPATH"],
        videos_dir=APP_PARAMS["COUNTDOWN.RESULTS.VIDEOS.DIRECTORY"],
    )
    downloader = YouTubeVideoDownloader(store.videos_dir, oauth_verifier=oauth_verifier)
    return CountdownService(store=store, downloader=downloader, source=CountdownFileFormat())


def user_directory() -> JsonUserDirectory:
    """The user list. Defaults to data/auth/users.json; AUTH_USERS_FILE overrides it."""
    path = os.getenv("AUTH_USERS_FILE") or APP_HOME / "data" / "auth" / "users.json"
    return JsonUserDirectory(Path(path))


@lru_cache(maxsize=1)
def auth_service() -> AuthService:
    # One shared instance: the login lockout counters live in it
    return AuthService(
        users=user_directory(),
        passwords=WerkzeugPasswordHasher(),
        ip_throttle=LoginThrottle(max_failures=5),
        user_throttle=LoginThrottle(max_failures=20),
    )
