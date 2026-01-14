"""
Prometheus metrics for Expense Tracker API
"""

import time

from fastapi import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Request metrics
http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)

# Active connections
http_connections_active = Gauge("http_connections_active", "Number of active HTTP connections")

# Database metrics
db_queries_total = Counter("db_queries_total", "Total database queries", ["operation", "table"])

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds", "Database query duration in seconds", ["operation", "table"]
)

# Cache metrics
cache_hits_total = Counter("cache_hits_total", "Total cache hits", ["cache_type"])

cache_misses_total = Counter("cache_misses_total", "Total cache misses", ["cache_type"])

# Business metrics
transactions_created_total = Counter("transactions_created_total", "Total transactions created")

users_registered_total = Counter("users_registered_total", "Total users registered")


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics"""

    async def dispatch(self, request: Request, call_next):
        # Track active connections
        http_connections_active.inc()

        start_time = time.time()

        try:
            response = await call_next(request)

            # Record metrics
            method = request.method
            endpoint = request.url.path
            status = response.status_code

            http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()

            duration = time.time() - start_time
            http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)

            return response

        finally:
            http_connections_active.dec()


def metrics_endpoint():
    """FastAPI endpoint for Prometheus metrics"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
