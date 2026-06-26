"""
日志工具
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

from config.settings import LOG_CONFIG


class Logger:
    """日志管理器"""

    _instance: Optional["Logger"] = None
    _logger: Optional[logging.Logger] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._logger is not None:
            return

        self._logger = logging.getLogger("clash-agent")
        self._logger.setLevel(getattr(logging, LOG_CONFIG["level"]))

        # 避免重复添加handler
        if self._logger.handlers:
            return

        # 控制台handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(console_formatter)

        # 文件handler
        log_file = Path(LOG_CONFIG["file"])
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            LOG_CONFIG["file"],
            maxBytes=LOG_CONFIG["max_bytes"],
            backupCount=LOG_CONFIG["backup_count"],
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)

        self._logger.addHandler(console_handler)
        self._logger.addHandler(file_handler)

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    def debug(self, msg: str):
        self._logger.debug(msg)

    def info(self, msg: str):
        self._logger.info(msg)

    def warning(self, msg: str):
        self._logger.warning(msg)

    def error(self, msg: str):
        self._logger.error(msg)

    def critical(self, msg: str):
        self._logger.critical(msg)


def get_logger() -> Logger:
    """获取日志实例"""
    return Logger()
