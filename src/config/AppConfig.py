import datetime
import pathlib as path

APP_HOME = path.Path(__file__).resolve().parents[2]

APP_PARAMS = {
    "COUNTDOWN.RAW.DATA.FILEPATH": path.Path.joinpath(APP_HOME, 'data', 'results', 'test-data.json'),
    "COUNTDOWN.RESULTS.DATA.FILEPATH": path.Path.joinpath(APP_HOME, 'data', 'results', 'results.json'),
    "COUNTDOWN.RESULTS.VIDEOS.DIRECTORY": path.Path.joinpath(APP_HOME, 'data', 'videos')
}
