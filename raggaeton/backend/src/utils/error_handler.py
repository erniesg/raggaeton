import logging
from fastapi.responses import JSONResponse
from contextlib import contextmanager


# Define custom exceptions
class CustomException(Exception):
    """Base class for custom exceptions"""

    pass


class InitializationError(CustomException):
    """Raised when initialization fails"""

    pass


class ConfigurationError(CustomException):
    """Raised when there is a configuration error"""

    pass


class DataError(CustomException):
    """Raised when there is an error with data processing"""

    pass


class PromptError(CustomException):
    """Raised when there is an error with prompt generation"""

    pass


class LLMError(CustomException):
    """Raised when there is an error with LLM call"""

    pass


# Function to handle exceptions
def handle_exception(exc: Exception):
    logger = logging.getLogger(__name__)
    if isinstance(exc, CustomException):
        logger.error(f"Custom exception occurred: {exc}")
        return JSONResponse(status_code=400, content={"error": str(exc)})
    else:
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": "Internal server error"})


# Context manager for error handling
@contextmanager
def error_handling_context():
    try:
        yield
    except Exception as exc:
        handle_exception(exc)
        raise
