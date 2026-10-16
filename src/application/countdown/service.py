from dataclasses import dataclass

from ...domain.countdown.entry import CountdownDataError, CountdownEntry
from ..ports import CountdownStore, ProgressCallback, RawCountdownFormat, VideoDownloader


@dataclass(frozen=True)
class PlayableEntry:
    entry: CountdownEntry
    filename: str


class CountdownService:
    def __init__(self, store: CountdownStore, downloader: VideoDownloader, source: RawCountdownFormat):
        self._store = store
        self._downloader = downloader
        self._source = source

    @property
    def videos_dir(self):
        return self._store.videos_dir

    def check_raw(self, raw) -> str | None:
        """Return a problem description if the raw file can't be imported, otherwise None."""
        return self._source.check(raw)

    def import_raw(self, raw, progress: ProgressCallback) -> dict:
        """Save the countdown, download every video, then validate. Returns the validation report."""
        entries = self._source.parse(raw)
        self._store.save_raw(raw)
        self._store.save_entries(entries)

        total = len(entries)
        for i, entry in enumerate(entries, start=1):
            # Titles stay out of progress messages so the countdown isn't spoiled
            progress("Downloading video", i - 1, total)
            self._downloader.download(entry.youtube_url, self._store.video_filename(entry))
            progress(f"Processed {i} of {total}", i, total)
        return self.validate()

    def validate(self) -> dict:
        """Check that the saved countdown and the videos folder agree.

        Missing videos block the countdown. Extra video files are reported but don't block it.
        """
        try:
            entries = self._store.load_entries()
        except CountdownDataError as e:
            return {"ok": False, "message": str(e), "count": 0, "missing": [], "unused": []}

        names = [self._store.video_filename(e) for e in entries]
        missing = [name for name in names if not self._store.has_video(name)]
        if missing:
            return {
                "ok": False,
                "message": (
                    f"{len(missing)} of {len(names)} videos are missing, starting with {missing[0]}. "
                    "Upload the countdown file again to download them."
                ),
                "count": len(names),
                "missing": missing,
                "unused": [],
            }

        unused = sorted(self._store.video_files() - set(names))
        message = f"{len(names)} videos ready."
        if unused:
            message += f" {len(unused)} video file(s) in the folder aren't in the countdown."
        return {"ok": True, "message": message, "count": len(names), "missing": [], "unused": unused}

    def playable_entries(self) -> list[PlayableEntry]:
        """Entries with a video, highest rank number first (the order the countdown plays them)."""
        entries = sorted(self._store.load_entries(), key=lambda e: e.rank, reverse=True)
        playable = []
        for entry in entries:
            filename = self._store.video_filename(entry)
            if self._store.has_video(filename):
                playable.append(PlayableEntry(entry=entry, filename=filename))
        return playable

    def video_path(self, filename: str):
        return self._store.video_path(filename)
