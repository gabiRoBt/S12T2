import logging
import sys
from pathlib import Path
from datetime import datetime

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / f"bot_{datetime.now().strftime('%Y-%m-%d')}.log"


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("chatbot")
    logger.setLevel(logging.DEBUG)

    # Format
    fmt = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)-8s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler - INFO and above
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)

    # File handler - DEBUG and above (everything)
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    logger.addHandler(console)
    logger.addHandler(file_handler)

    return logger


# Global logger instance
log = setup_logger()