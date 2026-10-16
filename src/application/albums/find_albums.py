import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from ...domain.library.release import AlbumRelease, released_in_year
from ..ports import ProgressCallback, SpotifyGateway, SpotifyRateLimited

TIME_RANGES = ("short_term", "medium_term", "long_term")
ARTIST_CHECK_WORKERS = 4
RETRY_PAUSE_SECONDS = 2


def _artists_of_tracks(tracks) -> dict[str, str]:
    return {a["id"]: a["name"] for t in tracks for a in t.get("artists", []) if a.get("id")}


def _artists_named(artists) -> dict[str, str]:
    return {a["id"]: a["name"] for a in artists if a.get("id")}


def collect_artists(spotify: SpotifyGateway, progress: ProgressCallback):
    """Every artist tied to the user's library, plus where each came from.

    Returns (artists, sources, playlist_artists): artists is {id: name}; sources is {source name: {id: name}};
    playlist_artists is a list of (playlist name, {id: name}).
    """
    progress("Fetching saved tracks", None, None)
    saved_tracks = spotify.saved_tracks()

    progress("Fetching saved albums", None, None)
    saved_albums = spotify.saved_albums()

    progress("Fetching top tracks and artists", None, None)
    top_tracks, top_artists = [], []
    for time_range in TIME_RANGES:
        top_tracks.extend(spotify.top_tracks(time_range))
        top_artists.extend(spotify.top_artists(time_range))

    progress("Fetching followed artists", None, None)
    followed = spotify.followed_artists()

    progress("Fetching playlists", None, None)
    playlists = spotify.playlists(lambda done, total: progress("Fetching playlists", done, total))
    playlist_artists = [(p["name"], _artists_of_tracks(p["tracks"])) for p in playlists]

    sources = {
        "saved tracks": _artists_of_tracks(saved_tracks),
        "saved albums": _artists_named(a for album in saved_albums for a in album.get("artists", [])),
        "top": {**_artists_of_tracks(top_tracks), **_artists_named(top_artists)},
        "followed": _artists_named(followed),
        "playlists": {id_: name for _, found in playlist_artists for id_, name in found.items()},
    }
    artists = {}
    for found in sources.values():
        artists.update(found)
    return artists, sources, playlist_artists


def find_album_releases(spotify: SpotifyGateway, year: int, progress: ProgressCallback,
                        workers: int = ARTIST_CHECK_WORKERS) -> list[AlbumRelease]:
    """Albums and singles released in `year` by any artist in the user's library.

    Artists are checked `workers` at a time. The gateway's artist_albums must be thread-safe.
    """
    artists, sources, playlist_artists = collect_artists(spotify, progress)
    total = len(artists)
    message = f"Checking {total} artists"
    sections = [{
        "heading": "Where the artists came from",
        "rows": [[name.capitalize(), len(found)] for name, found in sources.items()],
    }]
    biggest = sorted(playlist_artists, key=lambda item: len(item[1]), reverse=True)[:5]
    if biggest:
        sections.append({
            "heading": f"Largest of {len(playlist_artists)} playlists",
            "rows": [[name, len(found)] for name, found in biggest],
        })
    progress(message, 0, total, details={"sections": sections})

    def in_year(artist_id: str) -> list[dict]:
        return [a for a in spotify.artist_albums(artist_id) if released_in_year(a.get("release_date"), year)]

    def as_releases(artist_id: str, albums: list[dict]) -> list[AlbumRelease]:
        return [AlbumRelease(artist=artists[artist_id], album=a["name"], type=a["album_type"],
                             release_date=a["release_date"], uri=a["uri"]) for a in albums]

    releases: list[AlbumRelease] = []
    failed: list[str] = []
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(in_year, artist_id): artist_id for artist_id in artists}
        for future in as_completed(futures):
            artist_id = futures[future]
            try:
                releases.extend(as_releases(artist_id, future.result()))
            except SpotifyRateLimited:
                # Waiting won't help: stop everything and let the caller tell the user
                pool.shutdown(wait=False, cancel_futures=True)
                raise
            except Exception:
                failed.append(artist_id)  # tried again below
            done += 1
            progress(message, done, total)

    if failed:
        # A single gentler pass for anything that errored, e.g. during a rate-limit burst
        progress(f"Retrying {len(failed)} artists that hit an error", None, None)
        time.sleep(RETRY_PAUSE_SECONDS)
        for artist_id in failed:
            try:
                releases.extend(as_releases(artist_id, in_year(artist_id)))
            except SpotifyRateLimited:
                raise
            except Exception:
                pass  # one artist failing shouldn't stop the whole search

    return sorted(releases, key=lambda r: (r.artist, r.release_date))
