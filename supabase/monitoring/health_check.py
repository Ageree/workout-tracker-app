"""
Health Check System for Agent Swarm Knowledge System.

Provides comprehensive health monitoring for all system components.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import logging
import httpx

from services.supabase_client import SupabaseClient
from services.pubmed_service import PubMedService
from services.crossref_service import CrossRefService


class HealthStatusEnum(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status of a single component."""
    name: str
    status: HealthStatusEnum
    response_time_ms: float
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class HealthStatus:
    """Overall system health status."""
    status: HealthStatusEnum
    timestamp: datetime
    components: Dict[str, ComponentHealth]
    overall_response_time_ms: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'status': self.status.value,
            'timestamp': self.timestamp.isoformat(),
            'overall_response_time_ms': self.overall_response_time_ms,
            'components': {
                name: {
                    'name': comp.name,
                    'status': comp.status.value,
                    'response_time_ms': comp.response_time_ms,
                    'message': comp.message,
                    'details': comp.details,
                    'timestamp': comp.timestamp.isoformat()
                }
                for name, comp in self.components.items()
            }
        }


class HealthChecker:
    """
    Health checker for monitoring all system components.
    
    Checks:
    - Supabase database connectivity
    - PubMed API availability
    - CrossRef API availability
    - OpenAI API availability
    - Agent statuses
    """
    
    def __init__(
        self,
        supabase: SupabaseClient,
        pubmed_service: Optional[PubMedService] = None,
        crossref_service: Optional[CrossRefService] = None,
        openai_api_key: Optional[str] = None
    ):
        """
        Initialize health checker.
        
        Args:
            supabase: Supabase client instance
            pubmed_service: Optional PubMed service instance
            crossref_service: Optional CrossRef service instance
            openai_api_key: Optional OpenAI API key
        """
        self.supabase = supabase
        self.pubmed = pubmed_service or PubMedService()
        self.crossref = crossref_service or CrossRefService()
        self.openai_api_key = openai_api_key
        self.logger = logging.getLogger(__name__)
        
        # Timeout for health checks (seconds)
        self.check_timeout = 10.0
        
        # Store agent references for agent health checks
        self.agents: Dict[str, Any] = {}
    
    def register_agents(self, agents: Dict[str, Any]) -> None:
        """
        Register agents for health monitoring.
        
        Args:
            agents: Dictionary of agent instances
        """
        self.agents = agents
    
    async def check_all(self) -> HealthStatus:
        """
        Run all health checks and return overall status.
        
        Returns:
            HealthStatus with all component statuses
        """
        start_time = datetime.utcnow()
        
        # Run all checks concurrently
        checks = await asyncio.gather(
            self.check_supabase(),
            self.check_pubmed(),
            self.check_crossref(),
            self.check_openai(),
            self.check_agents(),
            return_exceptions=True
        )
        
        components = {}
        for check in checks:
            if isinstance(check, Exception):
                self.logger.error(f"Health check failed: {check}")
                continue
            components[check.name] = check
        
        # Calculate overall status
        overall_status = self._calculate_overall_status(components)
        
        # Calculate overall response time
        total_time = sum(comp.response_time_ms for comp in components.values())
        
        return HealthStatus(
            status=overall_status,
            timestamp=datetime.utcnow(),
            components=components,
            overall_response_time_ms=total_time
        )
    
    def _calculate_overall_status(
        self,
        components: Dict[str, ComponentHealth]
    ) -> HealthStatusEnum:
        """
        Calculate overall health status from component statuses.
        
        Rules:
        - Any UNHEALTHY -> UNHEALTHY
        - Any DEGRADED -> DEGRADED
        - All HEALTHY -> HEALTHY
        """
        statuses = [comp.status for comp in components.values()]
        
        if HealthStatusEnum.UNHEALTHY in statuses:
            return HealthStatusEnum.UNHEALTHY
        elif HealthStatusEnum.DEGRADED in statuses:
            return HealthStatusEnum.DEGRADED
        elif all(s == HealthStatusEnum.HEALTHY for s in statuses):
            return HealthStatusEnum.HEALTHY
        else:
            return HealthStatusEnum.UNKNOWN
    
    async def check_supabase(self) -> ComponentHealth:
        """Check Supabase database connectivity."""
        start_time = datetime.utcnow()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase.url}/rest/v1/",
                    headers=self.supabase.headers,
                    timeout=self.check_timeout
                )
                
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                if response.status_code == 200:
                    return ComponentHealth(
                        name="supabase",
                        status=HealthStatusEnum.HEALTHY,
                        response_time_ms=response_time,
                        message="Database connection successful"
                    )
                else:
                    return ComponentHealth(
                        name="supabase",
                        status=HealthStatusEnum.UNHEALTHY,
                        response_time_ms=response_time,
                        message=f"Unexpected status code: {response.status_code}"
                    )
        
        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return ComponentHealth(
                name="supabase",
                status=HealthStatusEnum.UNHEALTHY,
                response_time_ms=response_time,
                message=f"Connection failed: {str(e)}"
            )
    
    async def check_pubmed(self) -> ComponentHealth:
        """Check PubMed API availability."""
        start_time = datetime.utcnow()
        
        try:
            # Try a simple search
            result = await self.pubmed.search(
                query="test",
                max_results=1
            )
            
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return ComponentHealth(
                name="pubmed_api",
                status=HealthStatusEnum.HEALTHY,
                response_time_ms=response_time,
                message="PubMed API responding",
                details={'results_count': len(result)}
            )
        
        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return ComponentHealth(
                name="pubmed_api",
                status=HealthStatusEnum.UNHEALTHY,
                response_time_ms=response_time,
                message=f"PubMed API check failed: {str(e)}"
            )
    
    async def check_crossref(self) -> ComponentHealth:
        """Check CrossRef API availability."""
        start_time = datetime.utcnow()
        
        try:
            # Try a simple works query
            result = await self.crossref.search_works(
                query="test",
                rows=1
            )
            
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Check circuit breaker status
            cb_status = self.crossref.get_circuit_breaker_status()
            
            status = HealthStatusEnum.HEALTHY
            message = "CrossRef API responding"
            
            # If circuit breaker is open, mark as degraded
            if cb_status['state'] == 'open':
                status = HealthStatusEnum.DEGRADED
                message = "Circuit breaker is open"
            
            return ComponentHealth(
                name="crossref_api",
                status=status,
                response_time_ms=response_time,
                message=message,
                details={'circuit_breaker': cb_status}
            )
        
        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return ComponentHealth(
                name="crossref_api",
                status=HealthStatusEnum.UNHEALTHY,
                response_time_ms=response_time,
                message=f"CrossRef API check failed: {str(e)}"
            )
    
    async def check_openai(self) -> ComponentHealth:
        """Check OpenAI API availability."""
        start_time = datetime.utcnow()
        
        if not self.openai_api_key:
            return ComponentHealth(
                name="openai_api",
                status=HealthStatusEnum.UNKNOWN,
                response_time_ms=0,
                message="OpenAI API key not configured"
            )
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {self.openai_api_key}"},
                    timeout=self.check_timeout
                )
                
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                if response.status_code == 200:
                    return ComponentHealth(
                        name="openai_api",
                        status=HealthStatusEnum.HEALTHY,
                        response_time_ms=response_time,
                        message="OpenAI API responding"
                    )
                else:
                    return ComponentHealth(
                        name="openai_api",
                        status=HealthStatusEnum.UNHEALTHY,
                        response_time_ms=response_time,
                        message=f"OpenAI API error: {response.status_code}"
                    )
        
        except Exception as e:
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return ComponentHealth(
                name="openai_api",
                status=HealthStatusEnum.UNHEALTHY,
                response_time_ms=response_time,
                message=f"OpenAI API check failed: {str(e)}"
            )
    
    async def check_agents(self) -> ComponentHealth:
        """Check all registered agents' health."""
        start_time = datetime.utcnow()
        
        if not self.agents:
            return ComponentHealth(
                name="agents",
                status=HealthStatusEnum.UNKNOWN,
                response_time_ms=0,
                message="No agents registered"
            )
        
        agent_statuses = {}
        healthy_count = 0
        total_count = len(self.agents)
        
        for name, agent in self.agents.items():
            try:
                # Check if agent has is_healthy method
                if hasattr(agent, 'is_healthy'):
                    is_healthy = agent.is_healthy()
                else:
                    # Fallback: check if running
                    is_healthy = getattr(agent, 'is_running', False)
                
                agent_statuses[name] = {
                    'healthy': is_healthy,
                    'stats': getattr(agent, 'get_stats', lambda: {})()
                }
                
                if is_healthy:
                    healthy_count += 1
            
            except Exception as e:
                agent_statuses[name] = {
                    'healthy': False,
                    'error': str(e)
                }
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Determine overall status
        if healthy_count == total_count:
            status = HealthStatusEnum.HEALTHY
            message = f"All {total_count} agents healthy"
        elif healthy_count > 0:
            status = HealthStatusEnum.DEGRADED
            message = f"{healthy_count}/{total_count} agents healthy"
        else:
            status = HealthStatusEnum.UNHEALTHY
            message = f"All {total_count} agents unhealthy"
        
        return ComponentHealth(
            name="agents",
            status=status,
            response_time_ms=response_time,
            message=message,
            details={'agents': agent_statuses}
        )
    
    async def run_periodic_checks(
        self,
        interval_seconds: int = 60,
        callback: Optional[callable] = None
    ) -> None:
        """
        Run health checks periodically.
        
        Args:
            interval_seconds: Time between checks
            callback: Optional callback function to receive health status
        """
        self.logger.info(f"Starting periodic health checks (interval: {interval_seconds}s)")
        
        while True:
            try:
                health = await self.check_all()
                
                if callback:
                    await callback(health)
                
                # Log unhealthy states
                if health.status != HealthStatusEnum.HEALTHY:
                    self.logger.warning(f"System health: {health.status.value}")
                    for name, comp in health.components.items():
                        if comp.status != HealthStatusEnum.HEALTHY:
                            self.logger.warning(
                                f"  {name}: {comp.status.value} - {comp.message}"
                            )
                else:
                    self.logger.debug(f"System health: {health.status.value}")
            
            except Exception as e:
                self.logger.error(f"Health check error: {e}")
            
            await asyncio.sleep(interval_seconds)
