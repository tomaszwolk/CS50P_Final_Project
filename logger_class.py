"""Custom login module. Contain only Logger Class."""

from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler

FILENAME: str = "logs/app.log"
LEVEL: str | int = 10  # 10 - DEBUG
CONSOLE_LEVEL: str | int = 10  # 10 - DEBUG
FILE_LEVEL: str | int = 20  # 20 - INFO


class Logger:
    """Custom logging class

    Class atributes:
        - FILENAME (str): path to where logs are  
        - LEVEL (str | int): Level on which logs will be shown  
        - CONSOLE_LEVEL (str | int): Level on which logs will be shown in console  
        - FILE_LEVEL (str | int): Level on which logs will be appended to file  

    Logging Levels:
        1. DEBUG (10): Detailed information for programmer.  
        2. INFO (20): Information that program works as expected.  
        3. WARNING (30): Something happend, but software still works.  
        4. ERROR (40): Serious problem.  
        5. CRITICAL (50): Probably program won't be able to run.  

    Usage:
        Import Logger class from logger_class  
        Call class Looger() and use provided method.  
        In methods use only args or only kwargs.  
    
    Example:
        from logger_class import Logger  
        >>> Logger().debug(kwargs=dict)  
        >>> Logger().info("Info message")  
        >>> Logger().warning(__name__, "Warning message")  
        >>> Logger().error("Error message")  
        >>> Logger().critical("Critical message")  
    """

    folder_path = Path(__file__).parent.resolve()
    log_file_path = folder_path / FILENAME
    if not log_file_path.exists():
        raise FileNotFoundError(f"Configuration file not found at {log_file_path}")

    logger = logging.getLogger()
    logger.setLevel(LEVEL)

    # configuring log format with timestamp in ISO8601
    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03dZ - %(levelname)s: %(message)s",
        style="%",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(CONSOLE_LEVEL)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # create a rotating file handler with a max size of 10MB and a backup count of 5
    file_handler = RotatingFileHandler(
        log_file_path, maxBytes=1024 * 1024 * 10, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(FILE_LEVEL)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    @classmethod
    def debug(cls, *text: str, **kwargs: dict) -> None:
        """Log debug method"""
        if kwargs:
            cls.logger.debug(kwargs.get("kwargs", kwargs))
        elif text:
            log_text = " ".join(text).strip()
            cls.logger.debug(log_text)
        else:
            cls.logger.debug("Debug level log")

    @classmethod
    def info(cls, *text: str, **kwargs: dict) -> None:
        """Log info method"""
        if kwargs:
            cls.logger.info(kwargs.get("kwargs", kwargs))
        else:
            log_text = " ".join(text).strip()
            cls.logger.info(log_text)

    @classmethod
    def warning(cls, *text: str, **kwargs: dict) -> None:
        """Log warning method"""
        if kwargs:
            cls.logger.warning(kwargs.get("kwargs", kwargs))
        else:
            log_text = " ".join(text).strip()
            cls.logger.warning(log_text)

    @classmethod
    def error(cls, *text: str, **kwargs: dict) -> None:
        """Log error method"""
        if kwargs:
            cls.logger.error(kwargs.get("kwargs", kwargs))
        else:
            log_text = " ".join(text).strip()
            cls.logger.error(log_text, exc_info=True)

    @classmethod
    def critical(cls, *text: str, **kwargs: dict) -> None:
        """Log critical method"""
        if kwargs:
            cls.logger.critical(kwargs.get("kwargs", kwargs))
        else:
            log_text = " ".join(text).strip()
            cls.logger.critical(log_text)
