"""Imports the raw countdown file from the command line and downloads its videos.

Run from the project root: python -m src.cli.setup
"""
import json

from ..composition import countdown_service
from ..config.AppConfig import APP_PARAMS


def main():
    with open(APP_PARAMS["COUNTDOWN.RAW.DATA.FILEPATH"], encoding="utf-8") as f:
        raw = json.load(f)

    service = countdown_service()
    problem = service.check_raw(raw)
    if problem:
        raise SystemExit(problem)

    report = service.import_raw(raw, lambda message, done=None, total=None: print(message))
    print(report["message"])


if __name__ == "__main__":
    main()
