import sys
import pathlib as path
import datetime
from loguru import logger
from .AppConfig import APP_HOME

LOGURU = {
    "LOG_PATH": APP_HOME / "logs" / f"app_{datetime.datetime.now().strftime('%Y-%m-%d')}.log",
    "LOG_LEVEL": "INFO",
    "LOG_FORMAT": "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{process.name}:{process.id}</cyan> | <cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>"
}

logger.level("DEBUG", color="<blue>")
logger.level("INFO", color="<white>")
logger.level("WARNING", color="<yellow>")
logger.level("ERROR", color="<red>")
logger.level("SUCCESS", color="<green>")

class LogConfig:
    _logger = None

    @staticmethod
    def get_logger():
        if LogConfig._logger is None:
            logger.remove()
            logger.add(sys.stdout, level=LOGURU["LOG_LEVEL"], format=LOGURU["LOG_FORMAT"], colorize=True)
            logger.add(LOGURU["LOG_PATH"], level=LOGURU["LOG_LEVEL"], format=LOGURU["LOG_FORMAT"], rotation="1 MB", compression="zip")
            LogConfig._logger = logger
        return LogConfig._logger