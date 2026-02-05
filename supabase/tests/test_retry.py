"""
Tests for retry utilities.
"""

import pytest
import httpx
from unittest.mock import Mock, AsyncMock, patch
from tenacity import RetryError

from utils.retry import (
    fetch_with_retry,
    fetch_json_with_retry,
    is_retryable_error,
    DEFAULT_RETRY_CONFIG
)


class TestIsRetryableError:
    """Test is_retryable_error function."""
    
    def test_is_retryable_error_429(self):
        """Test 429 is retryable."""
        error = httpx.HTTPStatusError(
            "Rate limited",
            request=None,
            response=type('Response', (), {'status_code': 429})()
        )
        assert is_retryable_error(error) is True
    
    def test_is_retryable_error_500(self):
        """Test 500 is retryable."""
        error = httpx.HTTPStatusError(
            "Server error",
            request=None,
            response=type('Response', (), {'status_code': 500})()
        )
        assert is_retryable_error(error) is True
    
    def test_is_retryable_error_502(self):
        """Test 502 is retryable."""
        error = httpx.HTTPStatusError(
            "Bad gateway",
            request=None,
            response=type('Response', (), {'status_code': 502})()
        )
        assert is_retryable_error(error) is True
    
    def test_is_retryable_error_503(self):
        """Test 503 is retryable."""
        error = httpx.HTTPStatusError(
            "Service unavailable",
            request=None,
            response=type('Response', (), {'status_code': 503})()
        )
        assert is_retryable_error(error) is True
    
    def test_is_retryable_error_504(self):
        """Test 504 is retryable."""
        error = httpx.HTTPStatusError(
            "Gateway timeout",
            request=None,
            response=type('Response', (), {'status_code': 504})()
        )
        assert is_retryable_error(error) is True
    
    def test_is_retryable_error_400(self):
        """Test 400 is not retryable."""
        error = httpx.HTTPStatusError(
            "Bad request",
            request=None,
            response=type('Response', (), {'status_code': 400})()
        )
        assert is_retryable_error(error) is False
    
    def test_is_retryable_error_404(self):
        """Test 404 is not retryable."""
        error = httpx.HTTPStatusError(
            "Not found",
            request=None,
            response=type('Response', (), {'status_code': 404})()
        )
        assert is_retryable_error(error) is False
    
    def test_is_retryable_error_connect_error(self):
        """Test ConnectError is retryable."""
        error = httpx.ConnectError("Connection failed")
        assert is_retryable_error(error) is True
    
    def test_is_retryable_error_timeout(self):
        """Test TimeoutException is retryable."""
        error = httpx.TimeoutException("Request timed out")
        assert is_retryable_error(error) is True
    
    def test_is_retryable_error_network(self):
        """Test NetworkError is retryable."""
        error = httpx.NetworkError("Network error")
        assert is_retryable_error(error) is True
    
    def test_is_retryable_error_other_exception(self):
        """Test other exceptions are not retryable."""
        error = ValueError("Some error")
        assert is_retryable_error(error) is False


class TestFetchWithRetry:
    """Test fetch_with_retry function."""
    
    @pytest.mark.asyncio
    async def test_fetch_with_retry_success(self):
        """Test successful request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        
        mock_client = Mock()
        mock_client.request = AsyncMock(return_value=mock_response)
        
        response = await fetch_with_retry(
            client=mock_client,
            url="https://api.example.com/test"
        )
        
        assert response == mock_response
        mock_client.request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_with_retry_success_after_failure(self):
        """Test success after one failure."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        
        mock_client = Mock()
        mock_client.request = AsyncMock(side_effect=[
            httpx.HTTPStatusError(
                "Server error",
                request=None,
                response=type('Response', (), {'status_code': 500})()
            ),
            mock_response
        ])
        
        response = await fetch_with_retry(
            client=mock_client,
            url="https://api.example.com/test"
        )
        
        assert response == mock_response
        assert mock_client.request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_fetch_with_retry_rate_limit(self):
        """Test handling of rate limit (429)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        
        mock_client = Mock()
        mock_client.request = AsyncMock(side_effect=[
            httpx.HTTPStatusError(
                "Rate limited",
                request=None,
                response=type('Response', (), {
                    'status_code': 429,
                    'headers': {'retry-after': '1'}
                })()
            ),
            mock_response
        ])
        
        response = await fetch_with_retry(
            client=mock_client,
            url="https://api.example.com/test"
        )
        
        assert response == mock_response
        assert mock_client.request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_fetch_with_retry_exhausted(self):
        """Test retry exhaustion."""
        mock_client = Mock()
        mock_client.request = AsyncMock(side_effect=httpx.HTTPStatusError(
            "Server error",
            request=None,
            response=type('Response', (), {'status_code': 500})()
        ))
        
        with pytest.raises(RetryError):
            await fetch_with_retry(
                client=mock_client,
                url="https://api.example.com/test"
            )
        
        # Should have retried 3 times (default)
        assert mock_client.request.call_count == 3
    
    @pytest.mark.asyncio
    async def test_fetch_with_retry_post_request(self):
        """Test POST request with JSON data."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.raise_for_status = Mock()
        
        mock_client = Mock()
        mock_client.request = AsyncMock(return_value=mock_response)
        
        response = await fetch_with_retry(
            client=mock_client,
            url="https://api.example.com/test",
            method="POST",
            headers={"Content-Type": "application/json"},
            json_data={"key": "value"},
            timeout=60.0
        )
        
        assert response == mock_response
        mock_client.request.assert_called_once_with(
            method="POST",
            url="https://api.example.com/test",
            headers={"Content-Type": "application/json"},
            params=None,
            json={"key": "value"},
            timeout=60.0
        )
    
    @pytest.mark.asyncio
    async def test_fetch_with_retry_with_params(self):
        """Test request with query parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        
        mock_client = Mock()
        mock_client.request = AsyncMock(return_value=mock_response)
        
        response = await fetch_with_retry(
            client=mock_client,
            url="https://api.example.com/test",
            params={"page": 1, "limit": 10}
        )
        
        assert response == mock_response
        mock_client.request.assert_called_once_with(
            method="GET",
            url="https://api.example.com/test",
            headers=None,
            params={"page": 1, "limit": 10},
            json=None,
            timeout=30.0
        )


class TestFetchJsonWithRetry:
    """Test fetch_json_with_retry function."""
    
    @pytest.mark.asyncio
    async def test_fetch_json_with_retry_success(self):
        """Test successful JSON request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(return_value={"key": "value"})
        
        mock_client = Mock()
        mock_client.request = AsyncMock(return_value=mock_response)
        
        result = await fetch_json_with_retry(
            client=mock_client,
            url="https://api.example.com/test"
        )
        
        assert result == {"key": "value"}
    
    @pytest.mark.asyncio
    async def test_fetch_json_with_retry_invalid_json(self):
        """Test handling of invalid JSON."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(side_effect=ValueError("Invalid JSON"))
        
        mock_client = Mock()
        mock_client.request = AsyncMock(return_value=mock_response)
        
        with pytest.raises(ValueError):
            await fetch_json_with_retry(
                client=mock_client,
                url="https://api.example.com/test"
            )


class TestDefaultRetryConfig:
    """Test default retry configuration."""
    
    def test_default_retry_config_exists(self):
        """Test that default config exists and has required keys."""
        assert 'stop' in DEFAULT_RETRY_CONFIG
        assert 'wait' in DEFAULT_RETRY_CONFIG
        assert 'retry' in DEFAULT_RETRY_CONFIG
        assert 'before_sleep' in DEFAULT_RETRY_CONFIG
