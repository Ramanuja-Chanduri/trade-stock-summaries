"""Logging module for TradeSummaryAI.

Provides a centralized logging configuration with file and console output.
"""

import logging
import os
from datetime import datetime

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, f"app_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# Enhanced format with module name for better traceability
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=DATE_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name.
    
    Args:
        name: The name for the logger (typically __name__).
        
    Returns:
        A configured logger instance.
    """
    return logging.getLogger(name)
