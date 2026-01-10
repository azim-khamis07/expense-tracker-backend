import logging
import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID to each request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or extract request ID from headers
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Add request ID to request state
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to measure request processing time."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Record start time
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate processing time
        process_time = time.time() - start_time

        # Add timing header
        response.headers["X-Process-Time"] = str(process_time)

        # Add to request state for logging
        request.state.process_time = process_time

        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get request ID if available
        request_id = getattr(request.state, "request_id", None)

        # Log request start
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={"request_id": request_id, "method": request.method, "path": request.url.path},
        )

        # Process request
        start_time = time.time()
        try:
            response = await call_next(request)
            status_code = response.status_code
            process_time = time.time() - start_time

            # Log successful request
            logger.info(
                f"Request completed: {request.method} {request.url.path} - {status_code}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "process_time": process_time,
                },
            )

            return response

        except Exception as e:
            process_time = time.time() - start_time

            # Log failed request
            logger.error(
                f"Request failed: {request.method} {request.url.path} - {str(e)}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "process_time": process_time,
                    "error": str(e),
                },
                exc_info=True,
            )

            raise
