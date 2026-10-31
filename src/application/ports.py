from dataclasses import dataclass
from typing import Callable, Protocol

from ..domain.countdown.entry import CountdownEntry

# progress(message, done=None, total=None, details=None). done and total are None when the step has no
# countable size. details, when given, is {"sections": [{"heading": str, "rows": [[label, value], ...]}]}
# for the UI to show alongside the progress bar; later calls without details keep the last one.
ProgressCallback = Callable[..., None]


class SpotifyRateLimited(Exception):
    """Spotify told us to wait too long to be worth waiting. Raised instead of sleeping."""

    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = retry_after_seconds
        if retry_after_seconds >= 3600:
            wait = f"{retry_after_seconds / 3600:.1f} hours"
        else:
            wait = f"{max(1, round(retry_after_seconds / 60))} minutes"
        super().__init__(f"Spotify is rate limiting this app. Try again in about {wait}.")


class SpotifyGateway(Protocol):
    def saved_tracks(self) -> list[dict]: ...
    def saved_albums(self) -> list[dict]: ...
    def top_tracks(self, time_range: str) -> list[dict]: ...
    def top_artists(self, time_range: str) -> list[dict]: ...
    def followed_artists(self) -> list[dict]: ...
    def playlists(self, on_progress: Callable[[int, int], None] | None = None) -> list[dict]:
        """Playlists the user owns or collaborates on: [{"name": str, "tracks": [track dicts]}]."""
        ...
    def artist_albums(self, artist_id: str) -> list[dict]: ...


class CountdownStore(Protocol):
    videos_dir: object

    def save_raw(self, raw) -> None: ...
    def save_entries(self, entries: list[CountdownEntry]) -> None: ...
    def load_entries(self) -> list[CountdownEntry]: ...
    def video_filename(self, entry: CountdownEntry) -> str: ...
    def has_video(self, filename: str) -> bool: ...
    def video_path(self, filename: str): ...
    def video_files(self) -> set[str]: ...


class VideoDownloader(Protocol):
    def download(self, url: str, filename: str) -> None: ...


@dataclass(frozen=True)
class StoredUser:
    username: str
    password_hash: str
    is_admin: bool


class UserDirectory(Protocol):
    def find(self, username: str) -> StoredUser | None: ...
    def any_users(self) -> bool: ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...
    def verify(self, password_hash: str, password: str) -> bool: ...
    def burn(self, password: str) -> None:
        """Do the same work as verify() against a dummy hash, so unknown users take as long as known ones."""
        ...


class RawCountdownFormat(Protocol):
    def check(self, raw) -> str | None: ...
    def parse(self, raw) -> list[CountdownEntry]: ...
