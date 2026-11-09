from app.logger import get_logger

logger = get_logger(__name__)

logger.debug("This is a debug message")
logger.info("Application started")
logger.warning("This is a warning")
logger.error("Something went wrong")
logger.critical("Critical failure")