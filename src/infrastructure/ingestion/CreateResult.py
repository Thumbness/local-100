import json
from ...domain.dto.result import Result
from ...config.LoggerConfig import LogConfig

logger = LogConfig.get_logger()

class Parser:
    def __init__(self):
        self.json_data = None

    def GetJsonDataFromFile(self, FilePath):
        self.json_data = FilePath
        with open(self.json_data, 'r') as file:
            self.json_data = json.load(file)
        logger.info(f"JSON data loaded from file: {FilePath}")
        return self.json_data

    def CreateResult(self, json_data):
        title = json_data.get('name')
        artist = json_data.get('album', {}).get('artists', [{}])[0].get('name')
        album = json_data.get('album', {}).get('name')
        album_artwork = json_data.get('album', {}).get('imageUrl')
        voters = json_data.get('voters', [])
        songRank = json_data.get('songRank')
        points = json_data.get('points')
        youtube_url = self.ReplaceWWWwithHTTPS(json_data.get('youtubeUrl'))

        return Result(title, artist, album, album_artwork, voters, songRank, points, youtube_url)

    def writeResultsToJsonFile(self, results, output_file):
        results_data = []
        for result in results:
            result_dict = {
                "title": result.get_title(),
                "artist": result.get_artist(),
                "album": result.get_album(),
                "album_artwork": result.get_album_artwork(),
                "voters": sorted(result.get_voters(), key=lambda x: x.get("position", float('inf'))),
                "rank": result.get_rank(),
                "points": result.get_points(),
                "youtube_url": result.get_youtube_url(),
                "video_file_location": str(result.get_video_file_location())
            }
            results_data.append(result_dict)

        with open(output_file, 'w') as file:
            json.dump({"results": results_data}, file, indent=4)
        logger.info(f"Results written to JSON file: {output_file}")

    def ReplaceWWWwithHTTPS(self, url):
        if not url:
            return ""
        url = url.strip()
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("http://"):
            return "https://" + url[len("http://"):]
        if not url.startswith("https://"):
            return "https://" + url.lstrip("/")
        return url
    