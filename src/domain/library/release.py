from dataclasses import dataclass


@dataclass(frozen=True)
class AlbumRelease:
    artist: str
    album: str
    type: str
    release_date: str
    uri: str


def released_in_year(release_date: str | None, year: int) -> bool:
    return bool(release_date) and release_date.startswith(str(year))
