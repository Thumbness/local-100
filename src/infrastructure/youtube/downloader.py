import os
import shutil
import subprocess
import tempfile
import time

from pytubefix import YouTube
from pytubefix.cli import on_progress
from pytubefix.exceptions import AgeRestrictedError
from ...config.LoggerConfig import LogConfig

logger = LogConfig.get_logger()

RETRY_DELAYS = [30, 60, 120]
PAUSE_BETWEEN_VIDEOS = 3
# (pytubefix client, use_oauth) in fallback order; TV needs OAuth so it goes last
CLIENTS = [("VISION_OS", False), ("ANDROID_VR", False), ("MWEB", False), ("TV", True)]


class YouTubeVideoDownloader:
    """Downloads countdown videos into one folder. Implements the VideoDownloader port."""

    def __init__(self, videos_dir, oauth_verifier=None):
        self._output_dir = str(videos_dir)
        os.makedirs(self._output_dir, exist_ok=True)
        # Called with (verification_url, user_code) when YouTube sign-in is needed.
        # When None, pytubefix prints the code and waits for Enter in the terminal.
        self._oauth_verifier = oauth_verifier

    def download(self, url: str, filename: str) -> None:
        final_path = os.path.join(self._output_dir, filename)
        if os.path.exists(final_path):
            logger.info(f"Already downloaded, skipping: {filename}")
            return

        logger.info(f"Starting download for URL: {url}")
        for attempt in range(len(RETRY_DELAYS) + 1):
            try:
                if self._download(url, filename):
                    logger.success(f"Download completed: {filename}")
                time.sleep(PAUSE_BETWEEN_VIDEOS)
                return
            except AgeRestrictedError:
                logger.warning(f"Skipping age-restricted video (needs a logged-in account): {url}")
                return
            except Exception:
                if attempt == len(RETRY_DELAYS):
                    logger.exception(f"Download failed for URL: {url}")
                    return
                delay = RETRY_DELAYS[attempt]
                logger.warning(f"Attempt {attempt + 1} failed for {url}, retrying in {delay}s")
                time.sleep(delay)

    def _open_video(self, url: str) -> YouTube:
        """Try each client in order and return the first that yields video metadata."""
        last_error = None
        for client, use_oauth in CLIENTS:
            # OAuth token is cached so login is only prompted once, and only if a client needs it
            extra = {"oauth_verifier": self._oauth_verifier} if use_oauth and self._oauth_verifier else {}
            try:
                yt = YouTube(
                    url,
                    client=client,
                    on_progress_callback=on_progress,
                    use_oauth=use_oauth,
                    allow_oauth_cache=True,
                    **extra,
                )
                logger.debug(f"Client {client}: title={yt.title!r}, length={yt.length}s")
                return yt
            except Exception as e:
                logger.debug(f"Client {client} failed for {url}: {e!r}")
                last_error = e
        raise last_error

    def _download(self, url: str, filename: str) -> bool:
        yt = self._open_video(url)

        video_stream = yt.streams.filter(
            adaptive=True,
            file_extension="mp4",
            only_video=True
        ).order_by("resolution").desc().first()

        audio_stream = yt.streams.filter(
            adaptive=True,
            file_extension="mp4",
            only_audio=True
        ).order_by("abr").desc().first()

        if video_stream is None or audio_stream is None:
            logger.error(f"No suitable adaptive streams for URL: {url}")
            return False

        logger.debug(
            f"Video: itag={video_stream.itag}, res={video_stream.resolution} | "
            f"Audio: itag={audio_stream.itag}, abr={audio_stream.abr}"
        )

        with tempfile.TemporaryDirectory() as tmp:
            video_file = os.path.join(tmp, "video.mp4")
            audio_file = os.path.join(tmp, "audio.mp4")

            video_stream.download(output_path=tmp, filename="video.mp4")
            audio_stream.download(output_path=tmp, filename="audio.mp4")

            # Merge with ffmpeg inside the temp folder so a failed merge never leaves a partial file behind
            merged_file = os.path.join(tmp, "merged.mp4")
            cmd = [
                "ffmpeg", "-y",
                "-i", video_file,
                "-i", audio_file,
                "-c", "copy",
                merged_file
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            shutil.move(merged_file, os.path.join(self._output_dir, filename))

        return True
