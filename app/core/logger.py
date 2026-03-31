import os
import sys
from loguru import logger

def setup_logging():
    # Make logs directory if not exists
    os.makedirs("logs", exist_ok=True)
    
    # Remove default handler
    logger.remove()
    
    # Console handler
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    # Rotating file handler
    logger.add(
        "logs/gensigllm.log",
        rotation="00:00", # Daily rotation at midnight
        retention="30 days", # Keep for 30 days
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        enqueue=True, # Thread-safe async logging
    )

setup_logging()
