"""
Configuration management for Agent Swarm using Pydantic.

This module provides centralized configuration with validation,
support for different environments, and type safety.
"""

from typing import Optional

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings

from pydantic import Field, field_validator


class Settings(BaseSettings):
    """
    Application configuration with validation.
    
    Loads configuration from environment variables and .env files.
    All fields are validated on instantiation.
    """
    
    # Supabase
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_service_key: str = Field(..., description="Supabase service role key")
    
    # API Keys
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key")
    pubmed_api_key: Optional[str] = Field(None, description="PubMed API key")
    perplexity_api_key: Optional[str] = Field(None, description="Perplexity API key for Sonar search")
    
    # LLM Settings
    openai_model: str = Field("gpt-4o", description="OpenAI model to use")
    embedding_model: str = Field("text-embedding-3-small", description="Embedding model")
    anthropic_model: str = Field("claude-3-sonnet-20240229", description="Anthropic model")
    
    # Agent Intervals (seconds)
    research_interval: int = Field(86400, description="Research agent interval (seconds)")
    extraction_interval: int = Field(1800, description="Extraction agent interval (seconds)")
    validation_interval: int = Field(900, description="Validation agent interval (seconds)")
    kb_interval: int = Field(600, description="KB agent interval (seconds)")
    conflict_interval: int = Field(3600, description="Conflict agent interval (seconds)")
    prompt_engineering_interval: int = Field(86400, description="Prompt engineering agent interval (seconds)")
    
    # Agent Batch Sizes
    research_batch_size: int = Field(20, description="Research agent batch size")
    extraction_batch_size: int = Field(5, description="Extraction agent batch size")
    validation_batch_size: int = Field(10, description="Validation agent batch size")
    kb_batch_size: int = Field(10, description="KB agent batch size")
    conflict_batch_size: int = Field(10, description="Conflict agent batch size")
    
    # Rate Limits (requests per second)
    pubmed_rate_limit: float = Field(3.0, description="PubMed rate limit (req/s)")
    crossref_rate_limit: float = Field(10.0, description="CrossRef rate limit (req/s)")
    openai_rate_limit: float = Field(5.0, description="OpenAI rate limit (req/s)")
    rss_rate_limit: float = Field(2.0, description="RSS rate limit (req/s)")

    # Web Scraper Settings
    scraper_enabled: bool = Field(False, description="Enable web scraping for fitness sites (disabled until whitelist configured)")
    scraper_rate_limit_delay: float = Field(2.0, description="Delay between scraper requests (seconds)")
    scraper_timeout: float = Field(30.0, description="Scraper request timeout (seconds)")
    scraper_max_retries: int = Field(3, description="Maximum scraper retry attempts")

    # Perplexity Sonar Settings
    perplexity_enabled: bool = Field(True, description="Enable Perplexity Sonar for research search")
    perplexity_model: str = Field("sonar", description="Perplexity model (sonar, sonar-pro)")
    perplexity_timeout: float = Field(60.0, description="Perplexity request timeout (seconds)")
    perplexity_max_tokens: int = Field(1024, description="Maximum tokens in Perplexity response")
    
    # Retry Settings
    max_retries: int = Field(3, description="Maximum retry attempts")
    retry_backoff: float = Field(2.0, description="Retry backoff multiplier")
    retry_max_wait: int = Field(10, description="Maximum retry wait time (seconds)")
    
    # Circuit Breaker
    circuit_breaker_fail_max: int = Field(5, description="Circuit breaker failure threshold")
    circuit_breaker_reset_timeout: int = Field(60, description="Circuit breaker reset timeout (seconds)")
    
    # Validation Settings
    similarity_threshold: float = Field(0.85, description="Similarity threshold for validation")
    min_evidence_level: int = Field(2, description="Minimum evidence level")
    
    # Monitoring
    health_check_interval: int = Field(60, description="Health check interval (seconds)")
    metrics_collection_interval: int = Field(300, description="Metrics collection interval (seconds)")
    alert_threshold_error_rate: float = Field(0.1, description="Alert threshold for error rate")

    # Alerting
    telegram_bot_token: Optional[str] = Field(None, description="Telegram bot token for alerts")
    telegram_chat_id: Optional[str] = Field(None, description="Telegram chat ID for alerts")
    slack_webhook_url: Optional[str] = Field(None, description="Slack webhook URL for alerts")
    alert_error_rate_threshold: float = Field(0.5, description="Error rate threshold to trigger alert (50%)")
    
    # Logging
    log_level: str = Field("INFO", description="Logging level")
    log_format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }
    
    @field_validator('supabase_url')
    @classmethod
    def validate_supabase_url(cls, v: str) -> str:
        """Validate Supabase URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('supabase_url must start with http:// or https://')
        if '.supabase.co' not in v and 'localhost' not in v:
            raise ValueError('supabase_url must contain .supabase.co or localhost')
        return v

    @field_validator('openai_api_key')
    @classmethod
    def validate_openai_key_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate OpenAI API key format if provided."""
        if v and not v.startswith('sk-'):
            raise ValueError('openai_api_key must start with "sk-"')
        return v

    @field_validator('anthropic_api_key')
    @classmethod
    def validate_anthropic_key_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate Anthropic API key format if provided."""
        if v and not v.startswith('sk-ant-'):
            raise ValueError('anthropic_api_key must start with "sk-ant-"')
        return v

    @field_validator('research_interval', 'extraction_interval', 'validation_interval',
                     'kb_interval', 'conflict_interval')
    @classmethod
    def validate_intervals(cls, v: int) -> int:
        """Validate that intervals are positive."""
        if v <= 0:
            raise ValueError('interval must be positive')
        return v

    @field_validator('pubmed_rate_limit', 'crossref_rate_limit', 'openai_rate_limit', 'rss_rate_limit')
    @classmethod
    def validate_rate_limits(cls, v: float) -> float:
        """Validate that rate limits are positive."""
        if v <= 0:
            raise ValueError('rate limit must be positive')
        return v

    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f'log_level must be one of {valid_levels}')
        return v_upper
    
    def validate_api_keys(self) -> bool:
        """
        Check that at least one LLM API key is configured.
        
        Returns:
            True if at least one LLM key is present
            
        Raises:
            ValueError: If no LLM API keys are configured
        """
        if not self.openai_api_key and not self.anthropic_api_key:
            raise ValueError(
                "At least one LLM API key must be configured. "
                "Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable."
            )
        return True
    
    def get_llm_config(self) -> dict:
        """
        Get LLM configuration dictionary.
        
        Returns:
            Dictionary with LLM configuration
        """
        return {
            'openai_api_key': self.openai_api_key,
            'anthropic_api_key': self.anthropic_api_key,
            'default_provider': 'openai' if self.openai_api_key else 'anthropic',
            'openai_model': self.openai_model,
            'anthropic_model': self.anthropic_model,
        }
    
    def get_agent_intervals(self) -> dict:
        """
        Get agent intervals as a dictionary.
        
        Returns:
            Dictionary mapping agent names to intervals
        """
        return {
            'research': self.research_interval,
            'extraction': self.extraction_interval,
            'validation': self.validation_interval,
            'kb': self.kb_interval,
            'conflict': self.conflict_interval,
        }
    
    def get_agent_batch_sizes(self) -> dict:
        """
        Get agent batch sizes as a dictionary.
        
        Returns:
            Dictionary mapping agent names to batch sizes
        """
        return {
            'research': self.research_batch_size,
            'extraction': self.extraction_batch_size,
            'validation': self.validation_batch_size,
            'kb': self.kb_batch_size,
            'conflict': self.conflict_batch_size,
        }
    
    def get_rate_limits(self) -> dict:
        """
        Get rate limits as a dictionary.

        Returns:
            Dictionary mapping service names to rate limits
        """
        return {
            'pubmed': self.pubmed_rate_limit,
            'crossref': self.crossref_rate_limit,
            'openai': self.openai_rate_limit,
            'rss': self.rss_rate_limit,
        }

    def get_scraper_config(self) -> dict:
        """
        Get scraper configuration as a dictionary.

        Returns:
            Dictionary with scraper configuration
        """
        return {
            'enabled': self.scraper_enabled,
            'rate_limit_delay': self.scraper_rate_limit_delay,
            'timeout': self.scraper_timeout,
            'max_retries': self.scraper_max_retries,
        }

    def get_perplexity_config(self) -> dict:
        """
        Get Perplexity configuration as a dictionary.

        Returns:
            Dictionary with Perplexity configuration
        """
        return {
            'api_key': self.perplexity_api_key,
            'enabled': self.perplexity_enabled,
            'model': self.perplexity_model,
            'timeout': self.perplexity_timeout,
            'max_tokens': self.perplexity_max_tokens,
        }

    def get_alert_config(self) -> dict:
        """
        Get alerting configuration as a dictionary.

        Returns:
            Dictionary with alerting configuration
        """
        return {
            'telegram_bot_token': self.telegram_bot_token,
            'telegram_chat_id': self.telegram_chat_id,
            'slack_webhook_url': self.slack_webhook_url,
            'error_rate_threshold': self.alert_error_rate_threshold,
        }


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get or create global settings instance.
    
    Returns:
        Settings instance (cached)
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """
    Reload settings from environment.
    
    Useful for testing or when environment variables change.
    
    Returns:
        New Settings instance
    """
    global _settings
    _settings = Settings()
    return _settings
