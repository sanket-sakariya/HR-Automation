"""Custom APIRoute that adds Redis caching for GET and invalidation for mutations.

Cache key namespace: {service_name}:{endpoint}:{user_id}:{params}
Example: demo-service:/demo/read/{demo_id}/:user-123:demo_id=456
"""

from __future__ import annotations

import json
from typing import Optional

from fastapi import Request
from fastapi.responses import JSONResponse, Response  # pylint: disable=import-error
from fastapi.routing import APIRoute  # pylint: disable=import-error

from app.helper.redis_helper import get_redis_helper
from app.config.baseapp_config import get_base_config
from app.config.logger_config import logger


def _extract_user_id_from_headers(request: Request) -> Optional[str]:
    """Extract user_id from headers (supports both user-id/x-user-id).

    Returns string form to avoid UUID parsing exceptions in middleware layer.
    """
    headers = request.headers
    user_id = headers.get("user-id") or headers.get("x-user-id")
    return user_id


def _build_params_string(request: Request) -> str:
    """Build a string representation of path params and query params for cache key.

    Example: "demo_id=123&limit=10&offset=0"
    """
    parts = []

    # Add path parameters
    if hasattr(request, "path_params") and request.path_params:
        for key, value in sorted(request.path_params.items()):
            parts.append(f"{key}={value}")

    # Add query parameters
    if request.query_params:
        for key, value in sorted(request.query_params.items()):
            parts.append(f"{key}={value}")

    return "&".join(parts) if parts else "no-params"


class RedisCachedRoute(APIRoute):
    """APIRoute that wraps the route handler with Redis caching logic."""

    def get_route_handler(self):  # type: ignore[override]  # pylint: disable=too-many-statements
        """
        Custom route handler with Redis caching for GET requests
        and cache invalidation for mutations.
        """
        original_route_handler = super().get_route_handler()
        base_config = get_base_config()
        service_name = base_config.SERVICE_NAME
        ttl = base_config.REDIS_CACHE_TTL
        cache_enabled = base_config.IS_REDIS_CACHE_ENABLED
        endpoint_path = self.path  # e.g., "/demo/read/{demo_id}/"

        async def custom_route_handler(request: Request) -> Response:  # pylint: disable=too-many-return-statements,too-many-branches
            method = request.method.upper()
            redis_helper = get_redis_helper()

            # If cache disabled or no Redis, fall back
            if not cache_enabled or not redis_helper.is_connected():
                return await original_route_handler(request)

            user_id = _extract_user_id_from_headers(request)
            params_str = _build_params_string(request)
            cache_key = (
                f"{service_name}:{endpoint_path}:{user_id or 'none'}:{params_str}"
            )

            # GET: attempt to serve from cache
            if method == "GET":
                cached = await redis_helper.get(cache_key)
                if cached is not None:
                    logger.debug(f"Cache HIT: {cache_key}")
                    return JSONResponse(
                        content=cached, headers={"X-Cache-Status": "HIT"}
                    )
                logger.debug(f"Cache MISS: {cache_key}")

                # Run original handler
                response = await original_route_handler(request)

                # Only cache successful JSON responses
                try:
                    content_type = response.headers.get("content-type", "")
                except Exception:  # pylint: disable=broad-exception-caught
                    content_type = ""

                if (
                    200 <= response.status_code < 300
                    and "application/json" in content_type
                ):
                    # Handle JSONResponse directly
                    if isinstance(response, JSONResponse):
                        # JSONResponse has the body readily available
                        body_bytes = response.body
                        try:
                            payload = (
                                json.loads(body_bytes.decode("utf-8"))
                                if body_bytes
                                else None
                            )
                            if payload is not None:
                                await redis_helper.set(cache_key, payload, ttl=ttl)
                                logger.debug(f"Cache SET: {cache_key}")
                        except (json.JSONDecodeError, AttributeError):
                            pass
                        # Add cache status header - need to create new response
                        return JSONResponse(
                            content=payload if payload else {},
                            status_code=response.status_code,
                            headers={"X-Cache-Status": "MISS"},
                            media_type=response.media_type,
                        )

                    # Handle StreamingResponse or other response types
                    if hasattr(response, "body_iterator"):
                        body_bytes = b""
                        async for chunk in response.body_iterator:  # type: ignore[attr-defined]
                            body_bytes += chunk
                        try:
                            payload = (
                                json.loads(body_bytes.decode("utf-8"))
                                if body_bytes
                                else None
                            )
                        except json.JSONDecodeError:
                            payload = None

                        # Rebuild the response with the consumed body
                        new_response = Response(
                            content=body_bytes,
                            status_code=response.status_code,
                            headers=dict(response.headers),
                            media_type=response.media_type,
                            background=response.background,
                        )

                        if payload is not None:
                            await redis_helper.set(cache_key, payload, ttl=ttl)
                            logger.debug(f"Cache SET: {cache_key}")

                        # Add cache status header
                        new_response.headers["X-Cache-Status"] = "MISS"
                        return new_response

                # Non-JSON or non-2xx
                return response

            # Mutations: run handler, then invalidate
            if method in {"POST", "PUT", "PATCH", "DELETE"}:
                response = await original_route_handler(request)

                # Only invalidate on success to avoid clearing good cache on failed mutations
                if 200 <= response.status_code < 300:
                    # Invalidate ALL cached endpoints for this user
                    # This ensures mutations on /demo/create/ also clear /demos/ cache
                    pattern = f"{service_name}:*:{user_id or '*'}:*"
                    deleted = await redis_helper.invalidate_pattern(pattern)
                    if deleted:
                        logger.debug(f"Cache INVALIDATED: {pattern} ({deleted} keys)")

                return response

            # Other methods - passthrough
            return await original_route_handler(request)

        return custom_route_handler
