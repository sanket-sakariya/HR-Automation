from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config.logger_config import log_central
from app.exception.baseapp_exception import BaseAppException


def _make_serializable(obj):
    """
    Recursively convert non-serializable objects to serializable format.
    
    Args:
        obj: Object to make serializable (dict, Exception, etc.)
        
    Returns:
        Serializable version of the object
    """
    if isinstance(obj, dict):
        return {key: _make_serializable(value) for key, value in obj.items()}
    if isinstance(obj, Exception):
        return str(obj)
    if isinstance(obj, (list, tuple)):
        return [_make_serializable(item) for item in obj]
    if isinstance(obj, bytes):
        return obj.decode('utf-8', errors='ignore')
    return obj


def setup_error_handlers(app):
    """
    Set up custom error handlers for the FastAPI app.
    This is the standard way to organize error handling in enterprise applications.
    """
    
    @app.exception_handler(BaseAppException)
    async def app_exception_handler(_: Request, exc: BaseAppException) -> JSONResponse:
        """Handle custom application exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "data": {},
                "error_message": exc.detail,
                "errors": []
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
        """Handle HTTP exceptions (400, 401, 403, 404, etc.)."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "data": {},
                "error_message": exc.detail,
                "errors": []
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle Pydantic validation errors."""
        # Convert errors to a serializable format
        errors = []
        for error in exc.errors():
            # Ensure all values in the error are serializable
            serializable_error = {}
            for key, value in error.items():
                if isinstance(value, bytes):
                    serializable_error[key] = value.decode('utf-8', errors='ignore')
                elif isinstance(value, Exception):
                    # Convert exception objects to string representation
                    serializable_error[key] = str(value)
                elif isinstance(value, dict):
                    # Recursively handle nested dictionaries (like 'ctx' field)
                    serializable_error[key] = _make_serializable(value)
                elif isinstance(value, (list, tuple)):
                    # Handle lists/tuples that might contain non-serializable objects
                    serializable_error[key] = [_make_serializable(item) if isinstance(item, (dict, Exception)) else item for item in value]
                else:
                    serializable_error[key] = value
            errors.append(serializable_error)
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "data": {},
                "error_message": "Validation failed",
                "errors": errors
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions with proper logging."""
        # Log the unexpected exception
        log_central(
            message=f"Unhandled exception: {exc}",
            level="error",
            exc_info=True
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "data": {},
                "error_message": "Internal Server Error",
                "errors": []
            },
        )