import os
import shutil
import tempfile
import time

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from ...config.LoggerConfig import LogConfig

logger = LogConfig.get_logger()

RETRY_DELAYS = [30, 60, 120]
PAUSE_BETWEEN_VIDEOS = 3
REQUEST_TIMEOUT = 30  # seconds; a stalled YouTube response fails instead of hanging

# Prefer mp4 video + m4a audio so ffmpeg can merge by copying, then fall back to whatever is best
VIDEO_FORMAT = "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b"

# Errors that retrying will not fix
PERMANENT_ERRORS = ("confirm your age", "private video", "video unavailable", "has been removed")


class YouTubeVideoDownloader:
    """Downloads countdown videos into one folder with yt-dlp. Implements the VideoDownloader port."""

    def __init__(self, videos_dir, cookies_file=None):
        self._output_dir = str(videos_dir)
        os.makedirs(self._output_dir, exist_ok=True)
        # Netscape-format cookies exported from a signed-in browser; needed for age-restricted videos
        self._cookies_file = str(cookies_file) if cookies_file else None

    def download(self, url: str, filename: str) -> None:
        final_path = os.path.join(self._output_dir, filename)
        if os.path.exists(final_path):
            logger.info(f"Already downloaded, skipping: {filename}")
            return

        logger.info(f"Starting download for URL: {url}")
        for attempt in range(len(RETRY_DELAYS) + 1):
            try:
                self._download(url, final_path)
                logger.success(f"Download completed: {filename}")
                time.sleep(PAUSE_BETWEEN_VIDEOS)
                return
            except Exception as e:
                if self._is_permanent(e):
                    logger.warning(f"Skipping video that cannot be downloaded: {url} ({self._short(e)})")
                    return
                if attempt == len(RETRY_DELAYS):
                    logger.exception(f"Download failed for URL: {url}")
                    return
                delay = RETRY_DELAYS[attempt]
                logger.warning(f"Attempt {attempt + 1} failed for {url} ({self._short(e)}), retrying in {delay}s")
                time.sleep(delay)

    def _download(self, url: str, final_path: str) -> None:
        # Download inside a temp folder so a failed download or merge never leaves a partial file behind
        with tempfile.TemporaryDirectory() as tmp:
            options = {
                "format": VIDEO_FORMAT,
                "merge_output_format": "mp4",
                "outtmpl": os.path.join(tmp, "video.%(ext)s"),
                "socket_timeout": REQUEST_TIMEOUT,
                "quiet": True,
                "no_warnings": True,
                "noprogress": True,
                "noplaylist": True,
            }
            if self._cookies_file and os.path.isfile(self._cookies_file):
                # yt-dlp rewrites its cookie file, so give it a copy and keep the original untouched
                cookies_copy = os.path.join(tmp, "cookies.txt")
                shutil.copyfile(self._cookies_file, cookies_copy)
                options["cookiefile"] = cookies_copy

            with YoutubeDL(options) as ydl:
                ydl.download([url])

            merged_file = os.path.join(tmp, "video.mp4")
            if not os.path.exists(merged_file):
                raise RuntimeError(f"yt-dlp produced no mp4 file for {url}")
            shutil.move(merged_file, final_path)

    @staticmethod
    def _short(error: Exception) -> str:
        return str(error).strip().splitlines()[-1] if str(error).strip() else repr(error)

    @staticmethod
    def _is_permanent(error: Exception) -> bool:
        return isinstance(error, DownloadError) and any(text in str(error).lower() for text in PERMANENT_ERRORS)
