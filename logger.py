import logging
import os
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Set up file and console logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "kisaanvaani.log", mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("kisaanvaani")

def get_logger(name: str):
    return logging.getLogger(name)
