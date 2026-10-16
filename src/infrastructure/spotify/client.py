import threading
import time

# Artist lookups start at most this far apart, however many threads call at once (about 4 per second).
# Unthrottled parallel calls got the app rate limited for ~22 hours.
ARTIST_ALBUMS_MIN_INTERVAL = 0.25


class _MinInterval:
    """Hands out start times at least `seconds` apart, shared by all threads."""

    def __init__(self, seconds: float):
        self._seconds = seconds
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self):
        with self._lock:
            now = time.monotonic()
            slot = max(now, self._next)
            self._next = slot + self._seconds
        if slot > now:
            time.sleep(slot - now)


class SpotifyClient:
    """Spotify Web API adapter. Returns plain track, album and artist dicts.

    Safe to call from several threads at once (artist_albums is used that way).
    """

    def __init__(self, sp, artist_albums_interval: float = ARTIST_ALBUMS_MIN_INTERVAL):
        self._sp = sp
        self._artist_albums_limit = _MinInterval(artist_albums_interval)

    def saved_tracks(self) -> list[dict]:
        return [item["track"] for item in self._all(self._sp.current_user_saved_tracks(limit=50))
                if item.get("track")]

    def saved_albums(self) -> list[dict]:
        return [item["album"] for item in self._all(self._sp.current_user_saved_albums(limit=50))
                if item.get("album")]

    def top_tracks(self, time_range: str) -> list[dict]:
        return self._sp.current_user_top_tracks(limit=50, time_range=time_range)["items"]

    def top_artists(self, time_range: str) -> list[dict]:
        return self._sp.current_user_top_artists(limit=50, time_range=time_range)["items"]

    def followed_artists(self) -> list[dict]:
        # This endpoint wraps its page in "artists" and pages with a cursor
        page = self._sp.current_user_followed_artists(limit=50)["artists"]
        items = list(page["items"])
        while page["next"]:
            page = self._sp.next(page)["artists"]
            items.extend(page["items"])
        return items

    def playlists(self, on_progress=None) -> list[dict]:
        # Only playlists the user owns or collaborates on; playlists merely followed from others are skipped
        user_id = self._sp.current_user()["id"]
        wanted = [
            p for p in self._all(self._sp.current_user_playlists(limit=50))
            if p["owner"]["id"] == user_id or p.get("collaborative")
        ]
        result = []
        for done, playlist in enumerate(wanted, start=1):
            # Skips episodes and unavailable tracks
            tracks = [item["track"] for item in self._all(self._sp.playlist_tracks(playlist["id"], limit=100))
                      if item.get("track")]
            result.append({"name": playlist["name"], "tracks": tracks})
            if on_progress:
                on_progress(done, len(wanted))
        return result

    def artist_albums(self, artist_id: str) -> list[dict]:
        self._artist_albums_limit.wait()
        return self._all(self._sp.artist_albums(artist_id, album_type="album,single", limit=50))

    def _all(self, page) -> list[dict]:
        items = list(page["items"])
        while page["next"]:
            page = self._sp.next(page)
            items.extend(page["items"])
        return items
