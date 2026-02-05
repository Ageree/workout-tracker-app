"""
Environment-specific configurations for Agent Swarm.

This module provides pre-configured settings for different environments:
- Development: Frequent updates, verbose logging
- Production: Conservative settings, stable operation
- Testing: Fast intervals for quick test execution
"""

from .settings import Settings


class DevelopmentConfig(Settings):
    """
    Development environment configuration.
    
    Features:
    - Debug logging for detailed output
    - More frequent agent runs for faster iteration
    - Shorter health check intervals
    - Higher rate limits for testing
    """
    
    # Logging
    log_level: str = "DEBUG"
    
    # Monitoring - more frequent for development
    health_check_interval: int = 30
    metrics_collection_interval: int = 60
    
    # Agent Intervals - more frequent for development
    research_interval: int = 3600      # 1 hour (vs 1 day)
    extraction_interval: int = 300     # 5 min (vs 30 min)
    validation_interval: int = 180     # 3 min (vs 15 min)
    kb_interval: int = 120             # 2 min (vs 10 min)
    conflict_interval: int = 600       # 10 min (vs 1 hour)
    
    # Rate Limits - more permissive for development
    pubmed_rate_limit: float = 5.0
    crossref_rate_limit: float = 15.0
    openai_rate_limit: float = 10.0
    
    # Retry - faster retries
    retry_backoff: float = 1.0
    retry_max_wait: int = 5
    
    model_config = {"env_file": (".env", ".env.development"), "extra": "ignore"}


class ProductionConfig(Settings):
    """
    Production environment configuration.
    
    Features:
    - Info level logging (cleaner output)
    - Conservative rate limits to avoid API quotas
    - Longer intervals for stability
    - Higher retry thresholds
    """
    
    # Logging
    log_level: str = "INFO"
    
    # Monitoring - standard intervals
    health_check_interval: int = 60
    metrics_collection_interval: int = 300
    
    # Agent Intervals - conservative for stability
    research_interval: int = 86400     # 1 day
    extraction_interval: int = 1800    # 30 min
    validation_interval: int = 900     # 15 min
    kb_interval: int = 600             # 10 min
    conflict_interval: int = 3600      # 1 hour
    
    # Rate Limits - conservative to avoid quotas
    pubmed_rate_limit: float = 2.0
    crossref_rate_limit: float = 5.0
    openai_rate_limit: float = 3.0
    rss_rate_limit: float = 1.0
    
    # Circuit Breaker - more tolerant
    circuit_breaker_fail_max: int = 10
    circuit_breaker_reset_timeout: int = 120
    
    # Retry - more patient
    max_retries: int = 5
    retry_backoff: float = 2.0
    retry_max_wait: int = 30
    
    model_config = {"env_file": (".env", ".env.production"), "extra": "ignore"}


class TestingConfig(Settings):
    """
    Testing environment configuration.
    
    Features:
    - Fast intervals for quick test execution
    - Debug logging for troubleshooting
    - Minimal retries for faster failure
    """
    
    # Logging
    log_level: str = "DEBUG"
    
    # Monitoring - minimal
    health_check_interval: int = 10
    metrics_collection_interval: int = 30
    
    # Agent Intervals - very fast for tests
    research_interval: int = 60        # 1 min
    extraction_interval: int = 30      # 30 sec
    validation_interval: int = 15      # 15 sec
    kb_interval: int = 10              # 10 sec
    conflict_interval: int = 20        # 20 sec
    
    # Batch Sizes - small for tests
    research_batch_size: int = 5
    extraction_batch_size: int = 2
    validation_batch_size: int = 3
    kb_batch_size: int = 3
    conflict_batch_size: int = 3
    
    # Rate Limits - high for fast tests
    pubmed_rate_limit: float = 100.0
    crossref_rate_limit: float = 100.0
    openai_rate_limit: float = 100.0
    rss_rate_limit: float = 100.0
    
    # Retry - minimal for fast failure
    max_retries: int = 1
    retry_backoff: float = 0.1
    retry_max_wait: int = 1
    
    # Circuit Breaker - very sensitive
    circuit_breaker_fail_max: int = 2
    circuit_breaker_reset_timeout: int = 5
    
    model_config = {"env_file": (".env", ".env.testing"), "extra": "ignore"}


def get_config_for_environment(environment: str) -> Settings:
    """
    Get configuration for a specific environment.
    
    Args:
        environment: Environment name ('development', 'production', 'testing')
        
    Returns:
        Settings instance for the environment
        
    Raises:
        ValueError: If environment is not recognized
    """
    configs = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig,
        'dev': DevelopmentConfig,
        'prod': ProductionConfig,
        'test': TestingConfig,
    }
    
    env_lower = environment.lower()
    if env_lower not in configs:
        raise ValueError(
            f"Unknown environment: {environment}. "
            f"Choose from: {', '.join(configs.keys())}"
        )
    
    return configs[env_lower]()
