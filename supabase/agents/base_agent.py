"""
Base Agent class for the Knowledge System Agent Swarm.

Features:
- Graceful shutdown with cleanup
- State persistence
- Connection management
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict
from datetime import datetime
import asyncio
import logging
import traceback

from services.supabase_client import SupabaseClient


class BaseAgent(ABC):
    """Base class for all knowledge system agents with graceful shutdown support."""
    
    def __init__(self, name: str, supabase: SupabaseClient, logger: Optional[logging.Logger] = None):
        """
        Initialize the base agent.
        
        Args:
            name: Unique name of the agent
            supabase: Supabase client instance
            logger: Optional logger instance
        """
        self.name = name
        self.supabase = supabase
        self.is_running = False
        self.logger = logger or logging.getLogger(f"agent.{name}")
        self.processed_count = 0
        self.error_count = 0
        self.last_run: Optional[datetime] = None
        self.stats: Dict[str, Any] = {}  # Additional stats for subclasses
        
        # Graceful shutdown state
        self._shutdown_event = asyncio.Event()
        self._current_task: Optional[asyncio.Task] = None
        self._shutdown_timeout = 30.0  # seconds to wait for graceful shutdown
    
    @abstractmethod
    async def process(self) -> Any:
        """
        Main processing logic. Must be implemented by subclasses.
        
        Returns:
            Result of the processing (implementation-specific)
        """
        pass
    
    async def before_run(self) -> None:
        """
        Hook called before each run iteration.
        Override in subclasses if needed.
        """
        pass
    
    async def after_run(self, result: Any) -> None:
        """
        Hook called after each successful run iteration.
        Override in subclasses if needed.
        
        Args:
            result: The result from process()
        """
        pass
    
    async def on_error(self, error: Exception) -> None:
        """
        Hook called when an error occurs during processing.
        Override in subclasses for custom error handling.
        
        Args:
            error: The exception that occurred
        """
        self.error_count += 1
        self.logger.error(f"[{self.name}] Error: {error}")
        self.logger.debug(traceback.format_exc())
    
    async def on_shutdown(self) -> None:
        """
        Hook called during graceful shutdown.
        Override in subclasses to perform cleanup.
        
        Example cleanup tasks:
        - Save pending work
        - Close external connections
        - Release resources
        """
        pass
    
    async def run(self, interval_seconds: int = 300, max_iterations: Optional[int] = None):
        """
        Run agent in a loop with specified interval and graceful shutdown support.
        
        Args:
            interval_seconds: Time between iterations in seconds
            max_iterations: Maximum number of iterations (None for infinite)
        """
        self.is_running = True
        self._shutdown_event.clear()
        iteration = 0
        
        self.logger.info(f"[{self.name}] Agent started (interval: {interval_seconds}s)")
        
        try:
            while self.is_running and not self._shutdown_event.is_set():
                try:
                    iteration += 1
                    if max_iterations and iteration > max_iterations:
                        self.logger.info(f"[{self.name}] Max iterations reached, stopping")
                        break
                    
                    await self.before_run()
                    self.last_run = datetime.utcnow()
                    
                    # Track current task for graceful shutdown
                    self._current_task = asyncio.create_task(self.process())
                    result = await self._current_task
                    self.processed_count += 1
                    self._current_task = None
                    
                    await self.after_run(result)
                    
                except asyncio.CancelledError:
                    self.logger.info(f"[{self.name}] Processing cancelled")
                    raise
                except Exception as e:
                    await self.on_error(e)
                
                if self.is_running and not self._shutdown_event.is_set():
                    self.logger.debug(f"[{self.name}] Sleeping for {interval_seconds}s")
                    try:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(),
                            timeout=interval_seconds
                        )
                    except asyncio.TimeoutError:
                        pass  # Normal interval timeout, continue loop
        
        except asyncio.CancelledError:
            self.logger.info(f"[{self.name}] Agent cancelled")
        
        finally:
            await self._perform_shutdown()
    
    async def _perform_shutdown(self) -> None:
        """Internal method to perform graceful shutdown."""
        self.logger.info(f"[{self.name}] Performing graceful shutdown...")
        
        # Cancel current task if running
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
            try:
                await asyncio.wait_for(self._current_task, timeout=self._shutdown_timeout)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
        
        # Call subclass cleanup hook
        try:
            await asyncio.wait_for(
                self.on_shutdown(),
                timeout=self._shutdown_timeout
            )
        except asyncio.TimeoutError:
            self.logger.warning(f"[{self.name}] Shutdown hook timed out")
        except Exception as e:
            self.logger.error(f"[{self.name}] Error during shutdown: {e}")
        
        self.is_running = False
        self.logger.info(f"[{self.name}] Agent stopped")
    
    def stop(self):
        """
        Signal the agent to stop gracefully.
        The agent will complete current iteration and then shut down.
        """
        if self.is_running:
            self.logger.info(f"[{self.name}] Stop signal received, initiating graceful shutdown...")
            self._shutdown_event.set()
    
    async def shutdown(self, timeout: Optional[float] = None) -> bool:
        """
        Gracefully shutdown the agent with timeout.
        
        Args:
            timeout: Maximum time to wait for shutdown (default: self._shutdown_timeout)
            
        Returns:
            True if shutdown completed gracefully, False if timed out
        """
        if not self.is_running:
            return True
        
        timeout = timeout or self._shutdown_timeout
        self.stop()
        
        # Wait for shutdown to complete
        start_time = asyncio.get_event_loop().time()
        while self.is_running:
            if asyncio.get_event_loop().time() - start_time > timeout:
                self.logger.warning(f"[{self.name}] Shutdown timed out after {timeout}s")
                return False
            await asyncio.sleep(0.1)
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get agent statistics.
        
        Returns:
            Dictionary with agent statistics
        """
        return {
            'name': self.name,
            'is_running': self.is_running,
            'processed_count': self.processed_count,
            'error_count': self.error_count,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'error_rate': self.error_count / max(self.processed_count, 1),
        }
    
    def is_healthy(self) -> bool:
        """
        Check if agent is healthy.
        
        Returns:
            True if agent is running normally
        """
        if not self.is_running:
            return False
        
        # Check if agent has been running without errors
        if self.processed_count > 0 and self.error_count / self.processed_count > 0.5:
            return False
        
        return True
