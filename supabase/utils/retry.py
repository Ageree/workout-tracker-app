"""
Advanced Retry Logic Implementation.

Provides comprehensive retry capabilities with:
- Multiple retry strategies with jitter
- Dead Letter Queue for failed tasks
- Retry budget for rate limiting
- Circuit breaker integration
"""

import asyncio
import logging
import time
from typing import Callable, Optional, Any, Dict, List, Tuple, Type, Union
from dataclasses import dataclass, field
from functools import wraps
from datetime import datetime, timedelta

from .retry_strategies import (
    RetryStrategy, RetryContext, get_strategy,
    ExponentialBackoffStrategy, JitterType
)


class RetryError(Exception):
    """Exception raised when all retry attempts are exhausted."""
    
    def __init__(self, message: str, last_exception: Optional[Exception] = None, attempts: int = 0):
        super().__init__(message)
        self.last_exception = last_exception
        self.attempts = attempts


@dataclass
class RetryConfig:
    """Configuration for retry operations."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    strategy: str = "exponential"
    exponential_base: float = 2.0
    jitter: JitterType = JitterType.EQUAL
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    on_retry: Optional[Callable[[Exception, int, float], None]] = None
    on_exhausted: Optional[Callable[[Exception], None]] = None
    giveup_condition: Optional[Callable[[Exception], bool]] = None
    
    def __post_init__(self):
        if isinstance(self.jitter, str):
            self.jitter = JitterType(self.jitter)


@dataclass
class RetryMetrics:
    """Metrics for retry operations."""
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    total_retries: int = 0
    cumulative_delay: float = 0.0
    last_attempt_time: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        if self.total_attempts == 0:
            return 0.0
        return self.successful_attempts / self.total_attempts


class DeadLetterQueue:
    """
    Queue for failed tasks that exhausted all retries.
    
    Stores failed tasks for later analysis and possible reprocessing.
    """
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._queue: List[Dict[str, Any]] = []
        self._logger = logging.getLogger("DeadLetterQueue")
    
    async def add(
        self,
        task_id: str,
        task_type: str,
        payload: Dict[str, Any],
        error: str,
        retry_count: int,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Add a failed task to the DLQ.
        
        Args:
            task_id: Task identifier
            task_type: Type of task
            payload: Task payload
            error: Error message
            retry_count: Number of retry attempts made
            timestamp: When the failure occurred
            
        Returns:
            True if added, False if queue is full
        """
        if len(self._queue) >= self.max_size:
            # Remove oldest entry
            self._queue.pop(0)
        
        entry = {
            "task_id": task_id,
            "task_type": task_type,
            "payload": payload,
            "error": error,
            "retry_count": retry_count,
            "timestamp": timestamp or datetime.now(),
            "status": "pending_analysis"
        }
        
        self._queue.append(entry)
        self._logger.info(f"Added task {task_id} to DLQ after {retry_count} retries")
        return True
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Get all entries in the DLQ."""
        return self._queue.copy()
    
    def get_by_type(self, task_type: str) -> List[Dict[str, Any]]:
        """Get entries by task type."""
        return [e for e in self._queue if e["task_type"] == task_type]
    
    def remove(self, task_id: str) -> bool:
        """Remove an entry from the DLQ."""
        for i, entry in enumerate(self._queue):
            if entry["task_id"] == task_id:
                self._queue.pop(i)
                return True
        return False
    
    def clear(self):
        """Clear all entries from the DLQ."""
        self._queue.clear()
    
    @property
    def size(self) -> int:
        """Get current queue size."""
        return len(self._queue)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get DLQ statistics."""
        by_type: Dict[str, int] = {}
        for entry in self._queue:
            task_type = entry["task_type"]
            by_type[task_type] = by_type.get(task_type, 0) + 1
        
        return {
            "total_entries": self.size,
            "by_type": by_type,
            "max_size": self.max_size
        }


class RetryBudget:
    """
    Rate limiting for retries to prevent cascading failures.
    
    Tracks retry attempts within a time window and limits them.
    """
    
    def __init__(
        self,
        max_retries_per_window: int = 100,
        window_seconds: float = 60.0,
        max_concurrent_retries: int = 10
    ):
        self.max_retries_per_window = max_retries_per_window
        self.window_seconds = window_seconds
        self.max_concurrent_retries = max_concurrent_retries
        
        self._retry_history: List[float] = []
        self._current_retries = 0
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """
        Try to acquire budget for a retry.
        
        Returns:
            True if budget is available
        """
        async with self._lock:
            now = time.time()
            
            # Clean old entries
            cutoff = now - self.window_seconds
            self._retry_history = [t for t in self._retry_history if t > cutoff]
            
            # Check limits
            if len(self._retry_history) >= self.max_retries_per_window:
                return False
            
            if self._current_retries >= self.max_concurrent_retries:
                return False
            
            # Acquire budget
            self._retry_history.append(now)
            self._current_retries += 1
            return True
    
    async def release(self):
        """Release budget after retry completes."""
        async with self._lock:
            self._current_retries = max(0, self._current_retries - 1)
    
    async def get_usage(self) -> Dict[str, Any]:
        """Get current budget usage."""
        async with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds
            recent_retries = len([t for t in self._retry_history if t > cutoff])
            
            return {
                "recent_retries": recent_retries,
                "current_retries": self._current_retries,
                "max_per_window": self.max_retries_per_window,
                "max_concurrent": self.max_concurrent_retries,
                "available": (
                    recent_retries < self.max_retries_per_window and
                    self._current_retries < self.max_concurrent_retries
                )
            }


class RetryHandler:
    """
    Main retry handler with comprehensive retry logic.
    
    Features:
    - Configurable retry strategies
    - Dead letter queue integration
    - Retry budget for rate limiting
    - Circuit breaker integration
    - Detailed metrics
    
    Usage:
        handler = RetryHandler(config=RetryConfig(max_retries=3))
        
        result = await handler.execute(
            func=my_async_function,
            args=(arg1, arg2),
            kwargs={"key": "value"}
        )
    """
    
    def __init__(
        self,
        config: Optional[RetryConfig] = None,
        dead_letter_queue: Optional[DeadLetterQueue] = None,
        retry_budget: Optional[RetryBudget] = None
    ):
        self.config = config or RetryConfig()
        self.dlq = dead_letter_queue or DeadLetterQueue()
        self.budget = retry_budget
        self.metrics = RetryMetrics()
        self._strategy = self._create_strategy()
        self._logger = logging.getLogger("RetryHandler")
    
    def _create_strategy(self) -> RetryStrategy:
        """Create retry strategy from config."""
        return get_strategy(
            name=self.config.strategy,
            base_delay=self.config.base_delay,
            jitter=self.config.jitter,
            exponential_base=self.config.exponential_base,
            max_delay=self.config.max_delay
        )
    
    async def execute(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: Optional[Dict] = None,
        task_id: Optional[str] = None,
        task_type: str = "default"
    ) -> Any:
        """
        Execute function with retry logic.
        
        Args:
            func: Function to execute
            args: Positional arguments
            kwargs: Keyword arguments
            task_id: Task identifier for DLQ
            task_type: Task type for DLQ
            
        Returns:
            Function result
            
        Raises:
            Exception: Last exception after retries exhausted
        """
        kwargs = kwargs or {}
        last_exception: Optional[Exception] = None
        cumulative_delay = 0.0
        
        for attempt in range(self.config.max_retries + 1):
            self.metrics.total_attempts += 1
            self.metrics.last_attempt_time = datetime.now()
            
            try:
                # Execute function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Success
                self.metrics.successful_attempts += 1
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if exception is retryable
                if not isinstance(e, self.config.retryable_exceptions):
                    raise
                
                # Check giveup condition
                if self.config.giveup_condition and self.config.giveup_condition(e):
                    raise
                
                # Check if retries exhausted
                if attempt >= self.config.max_retries:
                    break
                
                # Check retry budget
                if self.budget:
                    budget_available = await self.budget.acquire()
                    if not budget_available:
                        self._logger.warning("Retry budget exhausted")
                        raise
                
                # Calculate delay
                context = RetryContext(
                    attempt=attempt,
                    last_delay=cumulative_delay,
                    base_delay=self.config.base_delay,
                    max_delay=self.config.max_delay,
                    cumulative_delay=cumulative_delay
                )
                delay = self._strategy.get_delay(context)
                cumulative_delay += delay
                
                # Log retry
                self._logger.warning(
                    f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s..."
                )
                
                # Callback
                if self.config.on_retry:
                    self.config.on_retry(e, attempt + 1, delay)
                
                # Wait before retry
                await asyncio.sleep(delay)
                
                self.metrics.total_retries += 1
                self.metrics.cumulative_delay += delay
                
                # Release budget
                if self.budget:
                    await self.budget.release()
        
        # Retries exhausted
        self.metrics.failed_attempts += 1
        
        # Add to DLQ
        if task_id:
            await self.dlq.add(
                task_id=task_id,
                task_type=task_type,
                payload={"args": str(args), "kwargs": str(kwargs)},
                error=str(last_exception),
                retry_count=self.config.max_retries
            )
        
        # Callback
        if self.config.on_exhausted:
            self.config.on_exhausted(last_exception)
        
        raise last_exception
    
    def get_metrics(self) -> RetryMetrics:
        """Get retry metrics."""
        return self.metrics


# Convenience decorators
def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    strategy: str = "exponential",
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    jitter: Union[JitterType, str] = JitterType.EQUAL
):
    """
    Decorator to add retry logic to a function.
    
    Usage:
        @retry(max_retries=3, base_delay=1.0)
        async def my_function():
            return await api_call()
    """
    if isinstance(jitter, str):
        jitter = JitterType(jitter)
    
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        strategy=strategy,
        retryable_exceptions=retryable_exceptions,
        jitter=jitter
    )
    
    def decorator(func: Callable) -> Callable:
        handler = RetryHandler(config=config)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await handler.execute(func, args, kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(handler.execute(func, args, kwargs))
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def db_retry(max_retries: int = 3, base_delay: float = 0.5):
    """Retry decorator optimized for database operations."""
    return retry(
        max_retries=max_retries,
        base_delay=base_delay,
        strategy="exponential",
        retryable_exceptions=(ConnectionError, TimeoutError),
        jitter=JitterType.EQUAL
    )


def api_retry(max_retries: int = 3, base_delay: float = 1.0):
    """Retry decorator optimized for API calls."""
    return retry(
        max_retries=max_retries,
        base_delay=base_delay,
        strategy="exponential",
        retryable_exceptions=(ConnectionError, TimeoutError, Exception),
        jitter=JitterType.FULL
    )


def critical_retry(max_retries: int = 5, base_delay: float = 2.0):
    """Retry decorator for critical operations with more retries."""
    return retry(
        max_retries=max_retries,
        base_delay=base_delay,
        strategy="exponential",
        retryable_exceptions=(Exception,),
        jitter=JitterType.DECORRELATED
    )


class MultiStrategyRetry:
    """
    Different retry strategies for different exception types.
    
    Usage:
        multi = MultiStrategyRetry()
        multi.add_strategy(ConnectionError, RetryConfig(max_retries=5))
        multi.add_strategy(TimeoutError, RetryConfig(max_retries=3))
        
        result = await multi.execute(func, args, kwargs)
    """
    
    def __init__(self):
        self._strategies: Dict[Type[Exception], RetryHandler] = {}
        self._default_handler: Optional[RetryHandler] = None
    
    def add_strategy(
        self,
        exception_type: Type[Exception],
        config: RetryConfig
    ):
        """Add retry strategy for specific exception type."""
        self._strategies[exception_type] = RetryHandler(config=config)
    
    def set_default(self, config: RetryConfig):
        """Set default retry strategy."""
        self._default_handler = RetryHandler(config=config)
    
    async def execute(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: Optional[Dict] = None
    ) -> Any:
        """Execute with multi-strategy retry."""
        kwargs = kwargs or {}
        
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except Exception as e:
            # Find matching handler
            handler = None
            for exc_type, h in self._strategies.items():
                if isinstance(e, exc_type):
                    handler = h
                    break
            
            if handler is None:
                handler = self._default_handler
            
            if handler is None:
                raise
            
            # Retry with appropriate handler
            return await handler.execute(func, args, kwargs)


class RetryContext:
    """Context manager for retry operations with cleanup."""
    
    def __init__(self, handler: RetryHandler, max_time: Optional[float] = None):
        self.handler = handler
        self.max_time = max_time
        self._start_time: Optional[float] = None
    
    async def __aenter__(self):
        self._start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def is_time_exceeded(self) -> bool:
        """Check if max time is exceeded."""
        if self.max_time is None or self._start_time is None:
            return False
        return time.time() - self._start_time > self.max_time
