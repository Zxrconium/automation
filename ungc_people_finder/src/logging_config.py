import logging
import sys
from rich.logging import RichHandler
from src.config import settings

def setup_logging():
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )
    # Silence noisy libs
    for noisy in ("httpx", "httpcore", "urllib3", "trafilatura"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

logger = logging.getLogger("ungc")
