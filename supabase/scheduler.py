"""
Scheduler for Agent Swarm Knowledge System.

Coordinates the execution of all agents with different intervals.
"""

import asyncio
import logging
import signal
import sys
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass

from config import Settings, get_settings, get_config_for_environment
from services.supabase_client import SupabaseClient
from services.llm_service import LLMService
from services.fitness_scraper_service import FitnessScraperService
from agents.research_agent import ResearchAgent
from agents.extraction_agent import ExtractionAgent
from agents.validation_agent import ValidationAgent
from agents.kb_agent import KnowledgeBaseAgent
from agents.conflict_agent import ConflictAgent
from agents.prompt_engineering_agent import PromptEngineeringAgent
from monitoring.alert_service import AlertService, AlertSeverity


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    enabled: bool = True
    interval_seconds: int = 300
    batch_size: int = 10


class AgentScheduler:
    """
    Scheduler that manages and coordinates all agents.
    
    Each agent runs on its own schedule:
    - Research Agent: Daily (86400s) - searches for new papers
    - Extraction Agent: Every 30 min (1800s) - extracts claims
    - Validation Agent: Every 15 min (900s) - validates claims
    - KB Agent: Every 10 min (600s) - integrates into KB
    - Conflict Agent: Hourly (3600s) - detects conflicts
    """
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        log_level: Optional[str] = None
    ):
        """
        Initialize the scheduler.
        
        Args:
            settings: Settings instance (recommended, takes precedence)
            supabase_url: Supabase project URL (legacy, use settings)
            supabase_key: Supabase service role key (legacy, use settings)
            openai_api_key: OpenAI API key (legacy, use settings)
            anthropic_api_key: Anthropic API key (legacy, use settings)
            log_level: Logging level (legacy, use settings)
        """
        # Load settings
        if settings is not None:
            self.settings = settings
        else:
            # Try to load from environment
            try:
                env = os.getenv('ENVIRONMENT', 'development')
                self.settings = get_config_for_environment(env)
            except Exception:
                # Fall back to legacy initialization
                self.settings = None
        
        # Setup logging
        level = log_level or (self.settings.log_level if self.settings else 'INFO')
        log_format = self.settings.log_format if self.settings else '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=getattr(logging, level.upper()),
            format=log_format
        )
        self.logger = logging.getLogger('AgentScheduler')
        
        # Get credentials from settings or legacy parameters
        if self.settings:
            supabase_url = self.settings.supabase_url
            supabase_key = self.settings.supabase_service_key
            openai_api_key = self.settings.openai_api_key
            anthropic_api_key = self.settings.anthropic_api_key
            kimi_api_key = self.settings.kimi_api_key
            deepseek_api_key = self.settings.deepseek_api_key
        else:
            kimi_api_key = os.getenv('KIMI_API_KEY')
            deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
        
        # Validate required credentials
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY are required")
        
        # Initialize services
        self.supabase = SupabaseClient(supabase_url, supabase_key)
        self.llm = None

        # Determine LLM provider priority: DeepSeek > Kimi > OpenAI > Anthropic
        if deepseek_api_key or kimi_api_key or openai_api_key or anthropic_api_key:
            # Determine default provider
            if deepseek_api_key:
                default_provider = 'deepseek'
                self.logger.info("Using DeepSeek as LLM provider")
            elif kimi_api_key:
                default_provider = 'kimi'
                self.logger.info("Using Kimi (Moonshot AI) as LLM provider")
            elif openai_api_key:
                default_provider = 'openai'
                self.logger.info("Using OpenAI as LLM provider")
            else:
                default_provider = 'anthropic'
                self.logger.info("Using Anthropic as LLM provider")
            
            self.llm = LLMService(
                openai_api_key=openai_api_key,
                anthropic_api_key=anthropic_api_key,
                kimi_api_key=kimi_api_key,
                deepseek_api_key=deepseek_api_key,
                default_provider=default_provider
            )

        # Initialize fitness scraper with settings
        scraper_config = self.settings.get_scraper_config() if self.settings else {}
        self.fitness_scraper = FitnessScraperService(
            rate_limit_delay=scraper_config.get('rate_limit_delay', 2.0),
            timeout=scraper_config.get('timeout', 30.0)
        ) if scraper_config.get('enabled', True) else None

        # Initialize alert service
        alert_config = self.settings.get_alert_config() if self.settings else {}
        self.alert_service = AlertService(
            telegram_bot_token=alert_config.get('telegram_bot_token'),
            telegram_chat_id=alert_config.get('telegram_chat_id'),
            slack_webhook_url=alert_config.get('slack_webhook_url'),
            min_severity=AlertSeverity.WARNING
        )
        
        # Agent configurations from settings or defaults
        if self.settings:
            self.configs = {
                'research': AgentConfig(
                    enabled=True,
                    interval_seconds=self.settings.research_interval,
                    batch_size=self.settings.research_batch_size
                ),
                'extraction': AgentConfig(
                    enabled=True,
                    interval_seconds=self.settings.extraction_interval,
                    batch_size=self.settings.extraction_batch_size
                ),
                'validation': AgentConfig(
                    enabled=True,
                    interval_seconds=self.settings.validation_interval,
                    batch_size=self.settings.validation_batch_size
                ),
                'kb': AgentConfig(
                    enabled=True,
                    interval_seconds=self.settings.kb_interval,
                    batch_size=self.settings.kb_batch_size
                ),
                'conflict': AgentConfig(
                    enabled=True,
                    interval_seconds=self.settings.conflict_interval,
                    batch_size=self.settings.conflict_batch_size
                ),
                'prompt_engineering': AgentConfig(
                    enabled=True,
                    interval_seconds=self.settings.prompt_engineering_interval,
                    batch_size=1
                ),
            }
        else:
            # Default configurations
            self.configs = {
                'research': AgentConfig(enabled=True, interval_seconds=86400),      # Daily
                'extraction': AgentConfig(enabled=True, interval_seconds=1800),     # 30 min
                'validation': AgentConfig(enabled=True, interval_seconds=900),      # 15 min
                'kb': AgentConfig(enabled=True, interval_seconds=600),              # 10 min
                'conflict': AgentConfig(enabled=True, interval_seconds=3600),       # 1 hour
                'prompt_engineering': AgentConfig(enabled=True, interval_seconds=86400),  # Daily
            }
        
        # Initialize agents
        self.agents: Dict[str, Any] = {}
        self._init_agents()
        
        # Control flags
        self.running = False
        self.tasks: list = []
    
    def _init_agents(self):
        """Initialize all agents."""
        batch_sizes = self.settings.get_agent_batch_sizes() if self.settings else {
            'research': 20,
            'extraction': 5,
            'validation': 10,
            'kb': 10,
            'conflict': 10
        }
        
        self.agents['research'] = ResearchAgent(
            supabase=self.supabase,
            fitness_scraper=self.fitness_scraper,
            days_back=7,
            max_results_per_source=batch_sizes.get('research', 20),
            enable_web_scraping=self.fitness_scraper is not None
        )
        
        self.agents['extraction'] = ExtractionAgent(
            supabase=self.supabase,
            llm_service=self.llm,
            batch_size=self.configs['extraction'].batch_size
        )
        
        self.agents['validation'] = ValidationAgent(
            supabase=self.supabase,
            llm_service=self.llm,
            batch_size=self.configs['validation'].batch_size
        )
        
        self.agents['kb'] = KnowledgeBaseAgent(
            supabase=self.supabase,
            llm_service=self.llm,
            batch_size=self.configs['kb'].batch_size
        )
        
        self.agents['conflict'] = ConflictAgent(
            supabase=self.supabase,
            llm_service=self.llm,
            batch_size=self.configs['conflict'].batch_size
        )
        
        self.agents['prompt_engineering'] = PromptEngineeringAgent(
            supabase=self.supabase,
            llm_service=self.llm,
            categories=['strength_training', 'hypertrophy', 'nutrition', 'recovery', 'cardio', 'general']
        )
    
    def configure_agent(self, name: str, **kwargs):
        """
        Configure an agent.
        
        Args:
            name: Agent name
            **kwargs: Configuration options (enabled, interval_seconds, batch_size)
        """
        if name in self.configs:
            for key, value in kwargs.items():
                if hasattr(self.configs[name], key):
                    setattr(self.configs[name], key, value)
                    self.logger.info(f"Configured {name}: {key}={value}")
    
    async def _run_agent(self, name: str, agent: Any, config: AgentConfig):
        """Run a single agent with its configuration."""
        if not config.enabled:
            self.logger.info(f"Agent {name} is disabled")
            return
        
        self.logger.info(
            f"Starting agent {name} with interval {config.interval_seconds}s"
        )
        
        try:
            await agent.run(interval_seconds=config.interval_seconds)
        except asyncio.CancelledError:
            self.logger.info(f"Agent {name} cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Agent {name} error: {e}")
    
    async def start(self):
        """Start all agents."""
        self.logger.info("Starting Agent Scheduler...")
        self.running = True
        
        # Setup signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self.stop)
        
        # Create tasks for each agent
        self.tasks = []
        for name, agent in self.agents.items():
            config = self.configs[name]
            task = asyncio.create_task(
                self._run_agent(name, agent, config),
                name=f"agent_{name}"
            )
            self.tasks.append(task)
        
        # Wait for all tasks
        try:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        except asyncio.CancelledError:
            self.logger.info("Scheduler cancelled")
        
        self.logger.info("Agent Scheduler stopped")
    
    def stop(self, reason: Optional[str] = None):
        """Stop all agents gracefully."""
        self.logger.info("Stopping Agent Scheduler...")
        self.running = False

        # Send alert if alert service is configured
        if self.alert_service.is_configured():
            asyncio.create_task(
                self.alert_service.alert_scheduler_stopped(reason)
            )

        # Stop all agents
        for name, agent in self.agents.items():
            try:
                agent.stop()
                self.logger.info(f"Stopped agent {name}")
            except Exception as e:
                self.logger.error(f"Error stopping agent {name}: {e}")

        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
    
    async def run_once(self, agent_name: Optional[str] = None):
        """
        Run agent(s) once for testing.
        
        Args:
            agent_name: Specific agent to run, or None for all
        """
        if agent_name:
            if agent_name not in self.agents:
                raise ValueError(f"Unknown agent: {agent_name}")
            
            self.logger.info(f"Running agent {agent_name} once...")
            result = await self.agents[agent_name].process()
            self.logger.info(f"Result: {result}")
            return result
        else:
            results = {}
            for name, agent in self.agents.items():
                if self.configs[name].enabled:
                    self.logger.info(f"Running agent {name} once...")
                    try:
                        results[name] = await agent.process()
                    except Exception as e:
                        self.logger.error(f"Error running {name}: {e}")
                        results[name] = {'error': str(e)}
            return results
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of all agents."""
        return {
            'running': self.running,
            'agents': {
                name: {
                    'enabled': self.configs[name].enabled,
                    'interval': self.configs[name].interval_seconds,
                    'stats': agent.get_stats()
                }
                for name, agent in self.agents.items()
            },
            'alert_service': self.alert_service.get_status() if self.alert_service else None,
            'scraper_enabled': self.fitness_scraper is not None
        }

    async def check_error_rates(self) -> None:
        """Check error rates and send alerts if needed."""
        if not self.alert_service.is_configured():
            return

        threshold = self.settings.alert_error_rate_threshold if self.settings else 0.5

        for name, agent in self.agents.items():
            stats = agent.get_stats()
            total = stats.get('processed', 0)
            errors = stats.get('errors', 0)

            if total > 0:
                error_rate = errors / total
                if error_rate > threshold:
                    await self.alert_service.alert_high_error_rate(
                        error_rate=error_rate,
                        threshold=threshold,
                        agent_name=name
                    )


async def main():
    """Main entry point."""
    # Load configuration from environment
    env = os.getenv('ENVIRONMENT', 'development')
    
    try:
        settings = get_config_for_environment(env)
        settings.validate_api_keys()
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)
    
    # Create scheduler with settings
    scheduler = AgentScheduler(settings=settings)
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'once':
            # Run once and exit
            agent_name = sys.argv[2] if len(sys.argv) > 2 else None
            results = await scheduler.run_once(agent_name)
            print(results)
            return
        
        elif command == 'status':
            # Print status
            status = scheduler.get_status()
            print(status)
            return
    
    # Start scheduler
    await scheduler.start()


if __name__ == '__main__':
    asyncio.run(main())
