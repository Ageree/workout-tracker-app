"""
Rate limiter for controlling API request rates.

This module provides rate limiting to avoid hitting API rate limits.
"""

import asyncio
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter for API requests.
    
    Ensures that requests are made at a controlled rate to avoid
    hitting API rate limits.
    
    Example:
        limiter = RateLimiter(requests_per_second=10)
        
        async def make_request():
            await limiter.acquire()
            # Make API call
    """
    
    def __init__(self, requests_per_second: float, burst_size: Optional[int] = None):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_second: Maximum number of requests per second
            burst_size: Maximum burst size (defaults to requests_per_second)
        """
        self.rate = requests_per_second
        self.burst_size = burst_size or int(requests_per_second)
        self.tokens = self.burst_size
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()
        self.logger = logging.getLogger(__name__)
    
    async def acquire(self, tokens: int = 1) -> float:
        """
        Acquire tokens from the bucket.
        
        Blocks until the required tokens are available.
        
        Args:
            tokens: Number of tokens to acquire (default 1)
            
        Returns:
            Time waited in seconds
        """
        async with self.lock:
            start_time = time.monotonic()
            
            while self.tokens < tokens:
                # Calculate time to wait for tokens to replenish
                now = time.monotonic()
                elapsed = now - self.last_update
                self.tokens = min(
                    self.burst_size,
                    self.tokens + elapsed * self.rate
                )
                self.last_update = now
                
                if self.tokens < tokens:
                    # Need to wait for more tokens
                    needed = tokens - self.tokens
                    wait_time = needed / self.rate
                    self.logger.debug(f"Rate limit: waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
            
            self.tokens -= tokens
            self.last_update = time.monotonic()
            
            return time.monotonic() - start_time
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass


class AdaptiveRateLimiter:
    """
    Adaptive rate limiter that adjusts based on API responses.
    
    Increases rate when requests succeed, decreases when rate limited.
    """
    
    def __init__(
        self,
        initial_rate: float = 10.0,
        min_rate: float = 1.0,
        max_rate: float = 100.0,
        backoff_factor: float = 0.5,
        increase_factor: float = 1.1
    ):
        """
        Initialize adaptive rate limiter.
        
        Args:
            initial_rate: Starting requests per second
            min_rate: Minimum allowed rate
            max_rate: Maximum allowed rate
            backoff_factor: Factor to reduce rate on 429 (0.5 = halve)
            increase_factor: Factor to increase rate on success
        """
        self.rate = initial_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.backoff_factor = backoff_factor
        self.increase_factor = increase_factor
        
        self.limiter = RateLimiter(self.rate)
        self.lock = asyncio.Lock()
        self.logger = logging.getLogger(__name__)
    
    async def acquire(self) -> None:
        """Acquire permission to make a request."""
        await self.limiter.acquire()
    
    async def report_success(self) -> None:
        """Report successful request - may increase rate."""
        async with self.lock:
            new_rate = min(self.max_rate, self.rate * self.increase_factor)
            if new_rate != self.rate:
                self.rate = new_rate
                self.limiter = RateLimiter(self.rate)
                self.logger.debug(f"Increased rate to {self.rate:.2f} req/s")
    
    async def report_rate_limited(self) -> None:
        """Report rate limit hit - reduces rate."""
        async with self.lock:
            new_rate = max(self.min_rate, self.rate * self.backoff_factor)
            if new_rate != self.rate:
                self.rate = new_rate
                self.limiter = RateLimiter(self.rate)
                self.logger.warning(f"Rate limited! Reduced rate to {self.rate:.2f} req/s")


# Pre-configured rate limiters for common APIs
class APIRateLimiters:
    """Pre-configured rate limiters for external APIs."""
    
    @staticmethod
    def pubmed() -> RateLimiter:
        """
        Rate limiter for PubMed API.
        
        Without API key: 3 requests per second
        With API key: 10 requests per second
        """
        return RateLimiter(requests_per_second=3.0)
    
    @staticmethod
    def crossref() -> RateLimiter:
        """
        Rate limiter for CrossRef API.
        
        Polite pool (with email): ~10-20 requests per second
        Regular: Be conservative
        """
        return RateLimiter(requests_per_second=10.0)
    
    @staticmethod
    def openai() -> RateLimiter:
        """
        Rate limiter for OpenAI API.
        
        Varies by tier, but be conservative by default.
        """
        return RateLimiter(requests_per_second=5.0)
    
    @staticmethod
    def rss_feeds() -> RateLimiter:
        """
        Rate limiter for RSS feed fetching.
        
        Be polite to journal websites.
        """
        return RateLimiter(requests_per_second=2.0)
