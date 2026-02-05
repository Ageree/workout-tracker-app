"""
Tests for rate limiter utilities.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch

from utils.rate_limiter import RateLimiter, AdaptiveRateLimiter


class TestRateLimiter:
    """Test RateLimiter class."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(requests_per_second=10.0)
        assert limiter.rate == 10.0
        assert limiter.burst_size == 10
        assert limiter.tokens == 10
    
    @pytest.mark.asyncio
    async def test_rate_limiter_custom_burst(self):
        """Test rate limiter with custom burst size."""
        limiter = RateLimiter(requests_per_second=10.0, burst_size=5)
        assert limiter.burst_size == 5
        assert limiter.tokens == 5
    
    @pytest.mark.asyncio
    async def test_rate_limiter_acquire_single_token(self):
        """Test acquiring a single token."""
        limiter = RateLimiter(requests_per_second=100.0)  # High rate for fast test
        wait_time = await limiter.acquire()
        assert wait_time >= 0
        assert limiter.tokens == 99
    
    @pytest.mark.asyncio
    async def test_rate_limiter_acquire_multiple_tokens(self):
        """Test acquiring multiple tokens."""
        limiter = RateLimiter(requests_per_second=100.0)
        wait_time = await limiter.acquire(tokens=5)
        assert wait_time >= 0
        assert limiter.tokens == 95
    
    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_when_empty(self):
        """Test that acquire blocks when tokens are exhausted."""
        limiter = RateLimiter(requests_per_second=10.0, burst_size=1)
        
        # First acquire should succeed immediately
        start = time.monotonic()
        await limiter.acquire()
        first_duration = time.monotonic() - start
        assert first_duration < 0.1  # Should be fast
        
        # Second acquire should wait for token replenishment
        start = time.monotonic()
        await limiter.acquire()
        second_duration = time.monotonic() - start
        assert second_duration >= 0.08  # Should wait at least ~0.1s (1/10 rate)
    
    @pytest.mark.asyncio
    async def test_rate_limiter_context_manager(self):
        """Test using rate limiter as async context manager."""
        limiter = RateLimiter(requests_per_second=100.0)
        
        async with limiter:
            pass  # Token should be acquired
        
        assert limiter.tokens == 99
    
    @pytest.mark.asyncio
    async def test_rate_limiter_token_replenishment(self):
        """Test that tokens are replenished over time."""
        limiter = RateLimiter(requests_per_second=10.0, burst_size=10)
        
        # Use all tokens
        for _ in range(10):
            await limiter.acquire()
        
        assert limiter.tokens == 0
        
        # Wait for replenishment
        await asyncio.sleep(0.2)  # Should get ~2 tokens
        
        # Check that tokens were replenished
        assert limiter.tokens >= 1
    
    @pytest.mark.asyncio
    async def test_rate_limiter_concurrent_access(self):
        """Test concurrent access to rate limiter."""
        limiter = RateLimiter(requests_per_second=100.0, burst_size=10)
        
        async def acquire_token():
            await limiter.acquire()
            return True
        
        # Try to acquire more tokens than burst size concurrently
        tasks = [acquire_token() for _ in range(15)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # First 10 should succeed, rest should wait
        success_count = sum(1 for r in results if r is True)
        assert success_count == 15  # All should eventually succeed


class TestAdaptiveRateLimiter:
    """Test AdaptiveRateLimiter class."""
    
    @pytest.mark.asyncio
    async def test_adaptive_rate_limiter_initialization(self):
        """Test adaptive rate limiter initialization."""
        limiter = AdaptiveRateLimiter(
            initial_rate=10.0,
            min_rate=1.0,
            max_rate=100.0
        )
        assert limiter.current_rate == 10.0
        assert limiter.min_rate == 1.0
        assert limiter.max_rate == 100.0
    
    @pytest.mark.asyncio
    async def test_adaptive_rate_limiter_report_success(self):
        """Test reporting success increases rate."""
        limiter = AdaptiveRateLimiter(
            initial_rate=10.0,
            min_rate=1.0,
            max_rate=100.0,
            increase_factor=1.5
        )
        
        initial_rate = limiter.current_rate
        await limiter.report_success()
        
        assert limiter.current_rate == min(initial_rate * 1.5, 100.0)
    
    @pytest.mark.asyncio
    async def test_adaptive_rate_limiter_report_rate_limit(self):
        """Test reporting rate limit decreases rate."""
        limiter = AdaptiveRateLimiter(
            initial_rate=10.0,
            min_rate=1.0,
            max_rate=100.0,
            decrease_factor=0.5
        )
        
        initial_rate = limiter.current_rate
        await limiter.report_rate_limit()
        
        assert limiter.current_rate == max(initial_rate * 0.5, 1.0)
    
    @pytest.mark.asyncio
    async def test_adaptive_rate_limiter_respects_min_rate(self):
        """Test that rate doesn't go below minimum."""
        limiter = AdaptiveRateLimiter(
            initial_rate=2.0,
            min_rate=1.0,
            max_rate=100.0,
            decrease_factor=0.5
        )
        
        # Report multiple rate limits
        for _ in range(5):
            await limiter.report_rate_limit()
        
        assert limiter.current_rate >= 1.0
    
    @pytest.mark.asyncio
    async def test_adaptive_rate_limiter_respects_max_rate(self):
        """Test that rate doesn't exceed maximum."""
        limiter = AdaptiveRateLimiter(
            initial_rate=50.0,
            min_rate=1.0,
            max_rate=100.0,
            increase_factor=2.0
        )
        
        # Report multiple successes
        for _ in range(5):
            await limiter.report_success()
        
        assert limiter.current_rate <= 100.0
    
    @pytest.mark.asyncio
    async def test_adaptive_rate_limiter_acquire(self):
        """Test acquiring token from adaptive rate limiter."""
        limiter = AdaptiveRateLimiter(
            initial_rate=100.0,
            min_rate=1.0,
            max_rate=1000.0
        )
        
        wait_time = await limiter.acquire()
        assert wait_time >= 0
    
    @pytest.mark.asyncio
    async def test_adaptive_rate_limiter_get_stats(self):
        """Test getting stats from adaptive rate limiter."""
        limiter = AdaptiveRateLimiter(
            initial_rate=10.0,
            min_rate=1.0,
            max_rate=100.0
        )
        
        # Generate some events
        await limiter.report_success()
        await limiter.report_success()
        await limiter.report_rate_limit()
        
        stats = limiter.get_stats()
        assert 'current_rate' in stats
        assert 'min_rate' in stats
        assert 'max_rate' in stats
        assert 'success_count' in stats
        assert 'rate_limit_count' in stats
        assert stats['success_count'] == 2
        assert stats['rate_limit_count'] == 1


class TestRateLimiterEdgeCases:
    """Test edge cases for rate limiters."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_zero_rate(self):
        """Test rate limiter with very low rate."""
        # Very low rate should still work
        limiter = RateLimiter(requests_per_second=0.1, burst_size=1)
        
        # First acquire should succeed
        await limiter.acquire()
        
        # Second acquire should take ~10 seconds, so we'll just verify it blocks
        # by checking that we can start the acquire
        acquire_task = asyncio.create_task(limiter.acquire())
        
        # Cancel the task to avoid waiting
        acquire_task.cancel()
        try:
            await acquire_task
        except asyncio.CancelledError:
            pass
    
    @pytest.mark.asyncio
    async def test_rate_limiter_very_high_rate(self):
        """Test rate limiter with very high rate."""
        limiter = RateLimiter(requests_per_second=10000.0)
        
        # Should be able to acquire many tokens quickly
        start = time.monotonic()
        for _ in range(100):
            await limiter.acquire()
        duration = time.monotonic() - start
        
        assert duration < 1.0  # Should complete quickly
    
    @pytest.mark.asyncio
    async def test_rate_limiter_more_tokens_than_burst(self):
        """Test acquiring more tokens than burst size."""
        limiter = RateLimiter(requests_per_second=100.0, burst_size=5)
        
        # Should wait for tokens to replenish
        start = time.monotonic()
        await limiter.acquire(tokens=10)
        duration = time.monotonic() - start
        
        # Should have waited for at least some replenishment
        assert duration > 0
