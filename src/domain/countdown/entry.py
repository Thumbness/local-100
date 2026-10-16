from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse


class CountdownDataError(Exception):
    """The saved countdown data is missing or unusable."""


def youtube_video_id(url: str) -> str | None:
    parsed = urlparse(url or "")
    video_id = parse_qs(parsed.query).get("v", [None])[0]
    if not video_id and parsed.netloc.lower() in {"youtu.be", "www.youtu.be"}:
        video_id = parsed.path.strip("/").split("/")[0]
    return video_id


@dataclass(frozen=True)
class Voter:
    name: str
    position: int


@dataclass(frozen=True)
class CountdownEntry:
    title: str
    artist: str
    rank: int
    points: int
    youtube_url: str
    voters: tuple[Voter, ...] = ()

    @property
    def video_key(self) -> str:
        """Filesystem-safe name for this entry's video, based on its YouTube ID."""
        video_id = youtube_video_id(self.youtube_url)
        safe = "".join(c for c in (video_id or self.title) if c.isalnum() or c in "-_")
        return safe or "video"
