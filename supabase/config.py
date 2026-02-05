"""
Configuration for Agent Swarm Knowledge System.

This module provides backward compatibility with the old Config class.
New code should use the config package directly.

Example:
    # New way (recommended)
    from config import get_settings
    settings = get_settings()
    
    # Old way (still works for backward compatibility)
    from config import Config
    config = Config.from_env()
"""

import os
import warnings
from typing import Optional, List
from dataclasses import dataclass, field

# Import new settings for backward compatibility
from config.settings import Settings, get_settings
from config.environments import DevelopmentConfig, ProductionConfig, TestingConfig


@dataclass
class Config:
    """
    Application configuration (legacy class).
    
    This class is maintained for backward compatibility.
    New code should use Settings from config.settings module.
    
    Deprecated: Use Settings class from config module instead.
    """
    
    # Supabase
    supabase_url: str = ""
    supabase_service_key: str = ""
    
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = 'gpt-4o'
    embedding_model: str = 'text-embedding-3-small'
    
    # Anthropic (optional alternative)
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = 'claude-3-sonnet-20240229'
    
    # PubMed
    pubmed_api_key: Optional[str] = None
    
    # Agent Intervals (seconds)
    research_interval: int = 86400      # Daily
    extraction_interval: int = 1800     # 30 minutes
    validation_interval: int = 900      # 15 minutes
    kb_interval: int = 600              # 10 minutes
    conflict_interval: int = 3600       # 1 hour
    
    # Agent Batch Sizes
    research_batch_size: int = 20
    extraction_batch_size: int = 5
    validation_batch_size: int = 10
    kb_batch_size: int = 10
    conflict_batch_size: int = 10
    
    # Validation Settings
    similarity_threshold: float = 0.85
    min_evidence_level: int = 2
    
    # Logging
    log_level: str = 'INFO'
    
    # Internal settings instance for delegation
    _settings: Optional[Settings] = field(default=None, repr=False)
    
    def __post_init__(self):
        """Initialize and show deprecation warning."""
        warnings.warn(
            "Config class is deprecated. Use Settings from config module instead.",
            DeprecationWarning,
            stacklevel=2
        )
    
    @classmethod
    def from_env(cls) -> 'Config':
        """
        Create configuration from environment variables.
        
        Returns:
            Config instance
        """
        warnings.warn(
            "Config.from_env() is deprecated. Use get_settings() from config module instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Try to use new settings first
        try:
            settings = get_settings()
            return cls.from_settings(settings)
        except Exception:
            # Fall back to direct environment loading
            return cls(
                supabase_url=os.getenv('SUPABASE_URL', ''),
                supabase_service_key=os.getenv('SUPABASE_SERVICE_KEY', ''),
                openai_api_key=os.getenv('OPENAI_API_KEY'),
                anthropic_api_key=os.getenv('ANTHROPIC_API_KEY'),
                pubmed_api_key=os.getenv('PUBMED_API_KEY'),
                log_level=os.getenv('LOG_LEVEL', 'INFO'),
            )
    
    @classmethod
    def from_settings(cls, settings: Settings) -> 'Config':
        """
        Create Config from Settings instance.
        
        Args:
            settings: Settings instance
            
        Returns:
            Config instance
        """
        return cls(
            supabase_url=settings.supabase_url,
            supabase_service_key=settings.supabase_service_key,
            openai_api_key=settings.openai_api_key,
            openai_model=settings.openai_model,
            embedding_model=settings.embedding_model,
            anthropic_api_key=settings.anthropic_api_key,
            anthropic_model=settings.anthropic_model,
            pubmed_api_key=settings.pubmed_api_key,
            research_interval=settings.research_interval,
            extraction_interval=settings.extraction_interval,
            validation_interval=settings.validation_interval,
            kb_interval=settings.kb_interval,
            conflict_interval=settings.conflict_interval,
            research_batch_size=settings.research_batch_size,
            extraction_batch_size=settings.extraction_batch_size,
            validation_batch_size=settings.validation_batch_size,
            kb_batch_size=settings.kb_batch_size,
            conflict_batch_size=settings.conflict_batch_size,
            similarity_threshold=settings.similarity_threshold,
            min_evidence_level=settings.min_evidence_level,
            log_level=settings.log_level,
            _settings=settings,
        )
    
    def validate(self) -> List[str]:
        """
        Validate configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not self.supabase_url:
            errors.append("SUPABASE_URL is required")
        
        if not self.supabase_service_key:
            errors.append("SUPABASE_SERVICE_KEY is required")
        
        if not self.openai_api_key and not self.anthropic_api_key:
            errors.append("Either OPENAI_API_KEY or ANTHROPIC_API_KEY is required")
        
        return errors
    
    def to_settings(self) -> Settings:
        """
        Convert to Settings instance.
        
        Returns:
            Settings instance
        """
        if self._settings is not None:
            return self._settings
        
        # Create new settings from config values
        return Settings(
            supabase_url=self.supabase_url,
            supabase_service_key=self.supabase_service_key,
            openai_api_key=self.openai_api_key,
            openai_model=self.openai_model,
            embedding_model=self.embedding_model,
            anthropic_api_key=self.anthropic_api_key,
            anthropic_model=self.anthropic_model,
            pubmed_api_key=self.pubmed_api_key,
            research_interval=self.research_interval,
            extraction_interval=self.extraction_interval,
            validation_interval=self.validation_interval,
            kb_interval=self.kb_interval,
            conflict_interval=self.conflict_interval,
            research_batch_size=self.research_batch_size,
            extraction_batch_size=self.extraction_batch_size,
            validation_batch_size=self.validation_batch_size,
            kb_batch_size=self.kb_batch_size,
            conflict_batch_size=self.conflict_batch_size,
            similarity_threshold=self.similarity_threshold,
            min_evidence_level=self.min_evidence_level,
            log_level=self.log_level,
        )


# Re-export new classes for convenience
__all__ = [
    'Config',
    'Settings',
    'get_settings',
    'DevelopmentConfig',
    'ProductionConfig',
    'TestingConfig',
]
