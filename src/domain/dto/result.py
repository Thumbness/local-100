from urllib.parse import parse_qs, urlparse

from ...config.AppConfig import APP_PARAMS

class Result:
    def __init__(self, title: str, 
                artist: str, 
                album: str,
                album_artwork: str, 
                voters: list, 
                rank: int, 
                points: int,
                youtube_url: str):
        self.title = title
        self.artist = artist
        self.album = album
        self.album_artwork = album_artwork
        self.voters = voters
        self.youtube_url = youtube_url
        self.video_file_location = self.set_video_file_location()
        self.rank = rank
        self.points = points

    def get_title(self):
        return self.title

    def get_artist(self):
        return self.artist

    def get_album(self):
        return self.album

    def get_album_artwork(self):
        return self.album_artwork

    def get_voters(self):
        return self.voters

    def get_rank(self):
        return self.rank

    def get_points(self):
        return self.points

    def get_youtube_url(self):
        return self.youtube_url

    def set_video_file_location(self):
        parsed_url = urlparse(self.youtube_url)
        video_id = parse_qs(parsed_url.query).get("v", [None])[0]
        if not video_id and parsed_url.netloc.lower() in {"youtu.be", "www.youtu.be"}:
            video_id = parsed_url.path.strip("/").split("/")[0]
        safe_video_id = "".join(
            character for character in (video_id or self.title) if character.isalnum() or character in "-_"
        )
        filename = f"{safe_video_id or 'video'}.mp4"
        return APP_PARAMS["COUNTDOWN.RESULTS.VIDEOS.DIRECTORY"] / filename

    def get_video_file_location(self):
        return self.video_file_location