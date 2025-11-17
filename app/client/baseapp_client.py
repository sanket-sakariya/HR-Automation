from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional
import httpx
from app.config.logger_config import logger
from app.exception.baseapp_exception import ServiceUnavailableException


class BaseAppHttpClient:
    """Base HTTP client for inter-service communication."""

    def __init__(
        self,
        base_url: str,
        timeout: int = 10,
        retries: int = 3,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self.default_headers = headers or {}

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic."""

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        request_headers = {**self.default_headers, **(headers or {})}

        for attempt in range(self.retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=request_headers,
                        params=params,
                        json=json_data,
                        **kwargs,
                    )

                    response.raise_for_status()
                    return response.json()

            except httpx.TimeoutException as e:
                logger.warning(
                    f"Request timeout (attempt {attempt + 1}/{self.retries}): {url}"
                )
                if attempt == self.retries - 1:
                    raise ServiceUnavailableException(
                        message="External service timeout"
                    ) from e
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
                if e.response.status_code >= 500:
                    if attempt == self.retries - 1:
                        raise ServiceUnavailableException(
                            message=f"External service error: {e.response.status_code}"
                        ) from e
                else:
                    raise ServiceUnavailableException(
                        message=f"External service error: {e.response.status_code}"
                    ) from e
            except httpx.RequestError as e:
                logger.error(
                    f"Unexpected error (attempt {attempt + 1}/{self.retries}): {str(e)}"
                )
                if attempt == self.retries - 1:
                    raise ServiceUnavailableException(
                        message=f"External service communication failed: {str(e)}"
                    ) from e

            # Wait before retry
            if attempt < self.retries - 1:
                await asyncio.sleep(2**attempt)  # Exponential backoff

        raise ServiceUnavailableException(message="All retry attempts failed")
