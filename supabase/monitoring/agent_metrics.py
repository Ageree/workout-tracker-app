"""
Agent Metrics Collection for Agent Swarm Knowledge System.

Provides detailed metrics collection and reporting for all agents.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import asyncio
import logging
import statistics


@dataclass
class AgentMetric:
    """Single metric data point."""
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentMetricsSnapshot:
    """Snapshot of agent metrics at a point in time."""
    agent_name: str
    timestamp: datetime
    processed_count: int
    error_count: int
    queue_size: int
    processing_time_ms: float
    error_rate: float
    avg_processing_time_ms: float
    recent_errors: List[str] = field(default_factory=list)


class AgentMetricsCollector:
    """
    Collects and aggregates metrics for agents.
    
    Metrics tracked:
    - processed_count: Total items processed
    - error_count: Total errors encountered
    - processing_time: Time taken for processing
    - queue_size: Current queue size
    - error_rate: Percentage of errors
    """
    
    def __init__(self, max_history: int = 1000):
        """
        Initialize metrics collector.
        
        Args:
            max_history: Maximum number of historical data points to keep
        """
        self.max_history = max_history
        self.logger = logging.getLogger(__name__)
        
        # Metrics storage per agent
        self._metrics: Dict[str, Dict[str, deque]] = {}
        self._counters: Dict[str, Dict[str, int]] = {}
        self._last_updated: Dict[str, datetime] = {}
    
    def register_agent(self, agent_name: str) -> None:
        """
        Register an agent for metrics collection.
        
        Args:
            agent_name: Unique name of the agent
        """
        if agent_name not in self._metrics:
            self._metrics[agent_name] = {
                'processing_time': deque(maxlen=self.max_history),
                'queue_size': deque(maxlen=self.max_history),
                'errors': deque(maxlen=self.max_history),
            }
            self._counters[agent_name] = {
                'processed': 0,
                'errors': 0,
            }
            self._last_updated[agent_name] = datetime.utcnow()
            self.logger.info(f"Registered agent for metrics: {agent_name}")
    
    def record_processing(
        self,
        agent_name: str,
        duration_seconds: float,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a processing event.
        
        Args:
            agent_name: Name of the agent
            duration_seconds: Processing duration in seconds
            success: Whether processing was successful
            metadata: Optional additional metadata
        """
        self.register_agent(agent_name)
        
        timestamp = datetime.utcnow()
        duration_ms = duration_seconds * 1000
        
        # Record processing time
        self._metrics[agent_name]['processing_time'].append(
            AgentMetric(timestamp=timestamp, value=duration_ms, metadata=metadata or {})
        )
        
        # Update counters
        self._counters[agent_name]['processed'] += 1
        if not success:
            self._counters[agent_name]['errors'] += 1
            self._metrics[agent_name]['errors'].append(
                AgentMetric(timestamp=timestamp, value=1.0, metadata=metadata or {})
            )
        
        self._last_updated[agent_name] = timestamp
    
    def record_error(
        self,
        agent_name: str,
        error_message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record an error event.
        
        Args:
            agent_name: Name of the agent
            error_message: Error message or type
            metadata: Optional additional metadata
        """
        self.register_agent(agent_name)
        
        timestamp = datetime.utcnow()
        
        self._counters[agent_name]['errors'] += 1
        self._metrics[agent_name]['errors'].append(
            AgentMetric(
                timestamp=timestamp,
                value=1.0,
                metadata={'error': error_message, **(metadata or {})}
            )
        )
        
        self._last_updated[agent_name] = timestamp
    
    def record_queue_size(self, agent_name: str, queue_size: int) -> None:
        """
        Record current queue size.
        
        Args:
            agent_name: Name of the agent
            queue_size: Current size of the queue
        """
        self.register_agent(agent_name)
        
        self._metrics[agent_name]['queue_size'].append(
            AgentMetric(timestamp=datetime.utcnow(), value=float(queue_size))
        )
    
    def get_metrics(self, agent_name: str) -> Dict[str, Any]:
        """
        Get current metrics for an agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Dictionary with metrics
        """
        if agent_name not in self._metrics:
            return {}
        
        counters = self._counters[agent_name]
        metrics = self._metrics[agent_name]
        
        # Calculate statistics
        processing_times = [m.value for m in metrics['processing_time']]
        queue_sizes = [m.value for m in metrics['queue_size']]
        
        total_processed = counters['processed']
        total_errors = counters['errors']
        error_rate = total_errors / max(total_processed, 1)
        
        result = {
            'agent_name': agent_name,
            'timestamp': datetime.utcnow().isoformat(),
            'counters': {
                'processed_count': total_processed,
                'error_count': total_errors,
            },
            'error_rate': error_rate,
            'last_updated': self._last_updated[agent_name].isoformat(),
        }
        
        # Add processing time statistics
        if processing_times:
            result['processing_time'] = {
                'avg_ms': statistics.mean(processing_times),
                'min_ms': min(processing_times),
                'max_ms': max(processing_times),
                'count': len(processing_times),
            }
            if len(processing_times) > 1:
                result['processing_time']['std_dev'] = statistics.stdev(processing_times)
        
        # Add queue size statistics
        if queue_sizes:
            result['queue_size'] = {
                'current': int(queue_sizes[-1]) if queue_sizes else 0,
                'avg': statistics.mean(queue_sizes),
                'max': max(queue_sizes),
            }
        
        return result
    
    def get_snapshot(self, agent_name: str) -> Optional[AgentMetricsSnapshot]:
        """
        Get a snapshot of current metrics for an agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            AgentMetricsSnapshot or None if agent not found
        """
        if agent_name not in self._metrics:
            return None
        
        metrics = self.get_metrics(agent_name)
        counters = metrics.get('counters', {})
        processing_time = metrics.get('processing_time', {})
        queue_size = metrics.get('queue_size', {})
        
        # Get recent errors
        recent_errors = [
            m.metadata.get('error', 'Unknown error')
            for m in self._metrics[agent_name]['errors']
        ][-10:]  # Last 10 errors
        
        return AgentMetricsSnapshot(
            agent_name=agent_name,
            timestamp=datetime.utcnow(),
            processed_count=counters.get('processed_count', 0),
            error_count=counters.get('error_count', 0),
            queue_size=queue_size.get('current', 0),
            processing_time_ms=processing_time.get('avg_ms', 0),
            error_rate=metrics.get('error_rate', 0),
            avg_processing_time_ms=processing_time.get('avg_ms', 0),
            recent_errors=recent_errors
        )
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get metrics for all registered agents.
        
        Returns:
            Dictionary mapping agent names to their metrics
        """
        return {
            name: self.get_metrics(name)
            for name in self._metrics.keys()
        }
    
    def check_alerts(self, agent_name: str) -> List[Dict[str, Any]]:
        """
        Check for alert conditions for an agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            List of alert conditions triggered
        """
        alerts = []
        metrics = self.get_metrics(agent_name)
        
        if not metrics:
            return alerts
        
        # Check error rate
        error_rate = metrics.get('error_rate', 0)
        if error_rate > 0.1:  # 10% error rate
            alerts.append({
                'type': 'high_error_rate',
                'severity': 'warning' if error_rate < 0.5 else 'critical',
                'message': f'Error rate is {error_rate:.1%}',
                'threshold': 0.1,
                'current_value': error_rate,
            })
        
        # Check queue size
        queue_size = metrics.get('queue_size', {}).get('current', 0)
        if queue_size > 100:
            alerts.append({
                'type': 'large_queue',
                'severity': 'warning',
                'message': f'Queue size is {queue_size}',
                'threshold': 100,
                'current_value': queue_size,
            })
        
        # Check processing time
        avg_time = metrics.get('processing_time', {}).get('avg_ms', 0)
        if avg_time > 60000:  # 1 minute
            alerts.append({
                'type': 'slow_processing',
                'severity': 'warning',
                'message': f'Average processing time is {avg_time:.0f}ms',
                'threshold': 60000,
                'current_value': avg_time,
            })
        
        # Check if agent hasn't processed anything recently
        last_updated_str = metrics.get('last_updated')
        if last_updated_str:
            last_updated = datetime.fromisoformat(last_updated_str)
            time_since_update = datetime.utcnow() - last_updated
            if time_since_update > timedelta(hours=1):
                alerts.append({
                    'type': 'stale_agent',
                    'severity': 'warning',
                    'message': f'No activity for {time_since_update}',
                    'threshold': 3600,  # 1 hour in seconds
                    'current_value': time_since_update.total_seconds(),
                })
        
        return alerts
    
    def reset_counters(self, agent_name: Optional[str] = None) -> None:
        """
        Reset counters for an agent or all agents.
        
        Args:
            agent_name: Name of the agent, or None to reset all
        """
        if agent_name:
            if agent_name in self._counters:
                self._counters[agent_name] = {
                    'processed': 0,
                    'errors': 0,
                }
                self.logger.info(f"Reset counters for agent: {agent_name}")
        else:
            for name in self._counters:
                self._counters[name] = {
                    'processed': 0,
                    'errors': 0,
                }
            self.logger.info("Reset counters for all agents")


# Global metrics collector instance
_metrics_collector: Optional[AgentMetricsCollector] = None


def get_metrics_collector() -> AgentMetricsCollector:
    """Get or create global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = AgentMetricsCollector()
    return _metrics_collector
