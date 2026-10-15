from ..infrastructure.youtube.MP4Downloader import DownloadService
from ..infrastructure.ingestion.CreateResult import Parser
from ..config.AppConfig import APP_PARAMS
from ..config.LoggerConfig import LogConfig
from pathlib import Path


logger = LogConfig.get_logger()
results = []
parser = Parser()
json_data = parser.GetJsonDataFromFile(APP_PARAMS["COUNTDOWN.RAW.DATA.FILEPATH"])

for item in json_data['results']['countdownResults']:
    result = parser.CreateResult(item)
    results.append(result)

logger.info(f"Parsed {len(results)} results from JSON data.")
parser.writeResultsToJsonFile(results, str(APP_PARAMS["COUNTDOWN.RESULTS.DATA.FILEPATH"]))

download_service = DownloadService()

for result in results:
    download_service.download_video(
        url=result.get_youtube_url(),
        output_path=APP_PARAMS["COUNTDOWN.RESULTS.VIDEOS.DIRECTORY"],
        filename=Path(result.get_video_file_location()).name
    )