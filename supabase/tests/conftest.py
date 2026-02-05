"""
Pytest configuration and fixtures for Agent Swarm tests.
"""

import pytest
import asyncio
from datetime import datetime, date
from typing import Generator
from unittest.mock import Mock, AsyncMock

from config import Settings, TestingConfig


# =============================================================================
# Event Loop Fixture
# =============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Settings Fixtures
# =============================================================================

@pytest.fixture
def test_settings() -> Settings:
    """Test configuration."""
    return TestingConfig(
        supabase_url="http://localhost:54321",
        supabase_service_key="test-service-key",
        openai_api_key="sk-test-openai-key",
        anthropic_api_key="sk-ant-test-anthropic-key",
        log_level="DEBUG"
    )


@pytest.fixture
def mock_settings() -> Settings:
    """Mock settings for unit tests."""
    settings = Mock(spec=Settings)
    settings.supabase_url = "http://localhost:54321"
    settings.supabase_service_key = "test-key"
    settings.openai_api_key = "sk-test-key"
    settings.anthropic_api_key = None
    settings.log_level = "DEBUG"
    settings.log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Agent intervals
    settings.research_interval = 60
    settings.extraction_interval = 30
    settings.validation_interval = 15
    settings.kb_interval = 10
    settings.conflict_interval = 20
    
    # Batch sizes
    settings.research_batch_size = 5
    settings.extraction_batch_size = 2
    settings.validation_batch_size = 3
    settings.kb_batch_size = 3
    settings.conflict_batch_size = 3
    
    # Rate limits
    settings.pubmed_rate_limit = 100.0
    settings.crossref_rate_limit = 100.0
    settings.openai_rate_limit = 100.0
    settings.rss_rate_limit = 100.0
    
    return settings


# =============================================================================
# Service Fixtures
# =============================================================================

@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client for testing."""
    client = Mock()
    client.get_pending_research = AsyncMock(return_value=[])
    client.get_pending_extraction = AsyncMock(return_value=[])
    client.get_pending_validation = AsyncMock(return_value=[])
    client.get_pending_kb_integration = AsyncMock(return_value=[])
    client.save_research_paper = AsyncMock(return_value={"id": "test-id"})
    client.save_claim = AsyncMock(return_value={"id": "test-claim-id"})
    return client


@pytest.fixture
def mock_llm_service():
    """Mock LLM service for testing."""
    service = Mock()
    service.extract_claims = AsyncMock(return_value=[
        {
            "claim_text": "Test claim",
            "confidence": 0.9,
            "evidence_level": 2,
            "category": "test"
        }
    ])
    service.validate_claim = AsyncMock(return_value={
        "is_valid": True,
        "confidence": 0.85,
        "feedback": "Valid claim"
    })
    return service


@pytest.fixture
def crossref_service():
    """CrossRef service for testing."""
    from services.crossref_service import CrossRefService
    return CrossRefService(mailto="test@example.com")


@pytest.fixture
def rss_service():
    """RSS service for testing."""
    from services.rss_service import RSSService
    return RSSService()


@pytest.fixture
def rate_limiter():
    """Rate limiter for testing."""
    from utils.rate_limiter import RateLimiter
    return RateLimiter(requests_per_second=10.0)


# =============================================================================
# Agent Fixtures
# =============================================================================

@pytest.fixture
def mock_research_agent(mock_supabase_client):
    """Mock research agent for testing."""
    from agents.research_agent import ResearchAgent
    agent = ResearchAgent(
        supabase=mock_supabase_client,
        days_back=1,
        max_results_per_source=5
    )
    return agent


@pytest.fixture
def mock_extraction_agent(mock_supabase_client, mock_llm_service):
    """Mock extraction agent for testing."""
    from agents.extraction_agent import ExtractionAgent
    agent = ExtractionAgent(
        supabase=mock_supabase_client,
        llm_service=mock_llm_service,
        batch_size=2
    )
    return agent


# =============================================================================
# Data Fixtures
# =============================================================================

@pytest.fixture
def sample_research_paper():
    """Sample research paper data."""
    return {
        "id": "test-paper-id",
        "title": "Test Research Paper",
        "authors": ["John Doe", "Jane Smith"],
        "abstract": "This is a test abstract about resistance training.",
        "publication_date": date(2024, 1, 15),
        "doi": "10.1234/test",
        "journal": "Journal of Testing",
        "source": "crossref",
        "source_url": "https://example.com/paper",
        "status": "pending_extraction"
    }


@pytest.fixture
def sample_claim():
    """Sample claim data."""
    return {
        "id": "test-claim-id",
        "paper_id": "test-paper-id",
        "claim_text": "Resistance training improves muscle strength",
        "confidence": 0.9,
        "evidence_level": 2,
        "category": "strength_training",
        "status": "pending_validation"
    }


@pytest.fixture
def sample_crossref_response():
    """Sample CrossRef API response."""
    return {
        "message": {
            "items": [
                {
                    "DOI": "10.1234/test",
                    "title": ["Test Paper Title"],
                    "author": [
                        {"given": "John", "family": "Doe"},
                        {"given": "Jane", "family": "Smith"}
                    ],
                    "abstract": "Test abstract about resistance training",
                    "published-print": {"date-parts": [[2024, 1, 15]]},
                    "container-title": ["Journal of Testing"],
                    "URL": "https://doi.org/10.1234/test",
                    "subject": ["Sports Science", "Physiology"],
                    "is-referenced-by-count": 42,
                    "type": "journal-article"
                }
            ],
            "total-results": 1
        }
    }


# =============================================================================
# Helper Fixtures
# =============================================================================

@pytest.fixture
def fixed_datetime():
    """Fixed datetime for consistent testing."""
    return datetime(2024, 1, 15, 10, 30, 0)


@pytest.fixture
def fixed_date():
    """Fixed date for consistent testing."""
    return date(2024, 1, 15)
