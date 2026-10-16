"""Wires the countdown use cases to their concrete adapters. Only the entry points (web, cli) call this."""
from dotenv import load_dotenv

from .application.countdown.service import CountdownService
from .config.AppConfig import APP_HOME, APP_PARAMS
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
