import sys

from loguru import logger

from app.config import get_settings


def setup_logging() -> None:
    """Replace the default loguru sink so the level comes from settings."""
    logger.remove()
    logger.add(
        sys.stderr,
        level=get_settings().log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )
