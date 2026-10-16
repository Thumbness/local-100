import json
from pathlib import Path

from ...domain.countdown.entry import CountdownDataError, CountdownEntry, Voter


class CountdownFileStore:
    """Keeps the raw import, results.json and the videos folder on disk."""

    def __init__(self, raw_path, results_path, videos_dir):
        self._raw_path = Path(raw_path)
        self._results_path = Path(results_path)
        self.videos_dir = Path(videos_dir)

    def save_raw(self, raw) -> None:
        self._raw_path.parent.mkdir(parents=True, exist_ok=True)
        self._raw_path.write_text(json.dumps(raw, indent=4), encoding="utf-8")

    def save_entries(self, entries: list[CountdownEntry]) -> None:
        rows = [{
            "title": e.title,
            "artist": e.artist,
            "voters": [{"name": v.name, "position": v.position}
                       for v in sorted(e.voters, key=lambda v: v.position)],
            "rank": e.rank,
            "points": e.points,
            "youtube_url": e.youtube_url,
            "video_file_location": str(self.videos_dir / self.video_filename(e)),
        } for e in entries]
        self._results_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._results_path, "w", encoding="utf-8") as f:
            json.dump({"results": rows}, f, indent=4)

    def load_entries(self) -> list[CountdownEntry]:
        if not self._results_path.is_file():
            raise CountdownDataError("No countdown data yet. Upload a countdown file first.")
        try:
            with open(self._results_path, encoding="utf-8") as f:
                rows = json.load(f)["results"]
            entries = [
                CountdownEntry(
                    title=r["title"],
                    artist=r["artist"],
                    rank=r["rank"],
                    points=r["points"],
                    youtube_url=r["youtube_url"],
                    voters=tuple(Voter(name=v["name"], position=v["position"]) for v in r["voters"]),
                )
                for r in rows
            ]
        except (ValueError, KeyError, TypeError) as e:
            raise CountdownDataError("results.json is unreadable. Upload the countdown file again.") from e
        if not entries:
            raise CountdownDataError("The countdown has no entries. Upload the countdown file again.")
        return entries

    def video_filename(self, entry: CountdownEntry) -> str:
        return f"{entry.video_key}.mp4"

    def has_video(self, filename: str) -> bool:
        return (self.videos_dir / filename).is_file()

    def video_path(self, filename: str) -> Path | None:
        # Only plain file names: nothing can reach outside the videos folder
        if Path(filename).name != filename:
            return None
        path = self.videos_dir / filename
        return path if path.is_file() else None

    def video_files(self) -> set[str]:
        if not self.videos_dir.is_dir():
            return set()
        return {p.name for p in self.videos_dir.glob("*.mp4")}
