"""
Retry utilities for HTTP requests with exponential backoff.

This module provides standardized retry logic for external API calls.
"""

import httpx
import logging
from typing import Optional, Dict, Any

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    RetryError
)

logger = logging.getLogger(__name__)


DEFAULT_RETRY_CONFIG = {
    'stop': stop_after_attempt(3),
    'wait': wait_exponential(multiplier=1, min=2, max=10),
    'retry': retry_if_exception_type((
        httpx.HTTPStatusError,
        httpx.ConnectError,
        httpx.TimeoutException,
        httpx.NetworkError
    )),
    'before_sleep': before_sleep_log(logger, logging.WARNING)
}


@retry(
    stop=DEFAULT_RETRY_CONFIG['stop'],
    wait=DEFAULT_RETRY_CONFIG['wait'],
    retry=DEFAULT_RETRY_CONFIG['retry'],
    before_sleep=DEFAULT_RETRY_CONFIG['before_sleep']
)
async def fetch_with_retry(
    client: httpx.AsyncClient,
    url: str,
    method: str = 'GET',
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    timeout: float = 30.0
) -> httpx.Response:
    """
    Make HTTP request with retry logic and exponential backoff.
    
    Args:
        client: HTTPX async client
        url: Request URL
        method: HTTP method (GET, POST, etc.)
        headers: Request headers
        params: Query parameters
        json_data: JSON body for POST/PUT requests
        timeout: Request timeout in seconds
        
    Returns:
        HTTPX Response object
        
    Raises:
        RetryError: If all retry attempts fail
        httpx.HTTPStatusError: On non-retryable HTTP errors
    """
    response = await client.request(
        method=method,
        url=url,
        headers=headers,
        params=params,
        json=json_data,
        timeout=timeout
    )
    
    # Handle rate limiting (429)
    if response.status_code == 429:
        retry_after = response.headers.get('retry-after', '5')
        wait_time = int(retry_after) if retry_after.isdigit() else 5
        logger.warning(f"Rate limited. Waiting {wait_time}s before retry")
        raise httpx.HTTPStatusError(
            f"Rate limited: {response.status_code}",
            request=response.request,
            response=response
        )
    
    # Handle server errors (5xx) - these trigger retry
    if response.status_code >= 500:
        logger.warning(f"Server error: {response.status_code}")
        raise httpx.HTTPStatusError(
            f"Server error: {response.status_code}",
            request=response.request,
            response=response
        )
    
    response.raise_for_status()
    return response


async def fetch_json_with_retry(
    client: httpx.AsyncClient,
    url: str,
    method: str = 'GET',
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    timeout: float = 30.0
) -> Dict[str, Any]:
    """
    Make HTTP request and return JSON response with retry logic.
    
    Args:
        client: HTTPX async client
        url: Request URL
        method: HTTP method
        headers: Request headers
        params: Query parameters
        json_data: JSON body
        timeout: Request timeout
        
    Returns:
        Parsed JSON response
    """
    response = await fetch_with_retry(
        client=client,
        url=url,
        method=method,
        headers=headers,
        params=params,
        json_data=json_data,
        timeout=timeout
    )
    return response.json()


def is_retryable_error(error: Exception) -> bool:
    """
    Check if an error is retryable.
    
    Args:
        error: Exception to check
        
    Returns:
        True if error is retryable
    """
    if isinstance(error, httpx.HTTPStatusError):
        # Retry on rate limit (429) and server errors (5xx)
        return error.response.status_code in [429, 500, 502, 503, 504]
    
    return isinstance(error, (
        httpx.ConnectError,
        httpx.TimeoutException,
        httpx.NetworkError
    ))
