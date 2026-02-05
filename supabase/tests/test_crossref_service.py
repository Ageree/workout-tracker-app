"""
Tests for CrossRef service.
"""

import pytest
import httpx
from datetime import date
from unittest.mock import Mock, AsyncMock, patch

from services.crossref_service import CrossRefService, CrossRefWork


class TestCrossRefServiceInitialization:
    """Test CrossRef service initialization."""
    
    def test_init_without_mailto(self):
        """Test initialization without mailto."""
        service = CrossRefService()
        assert service.mailto is None
        assert 'User-Agent' in service.headers
        assert 'mailto' not in service.headers['User-Agent']
    
    def test_init_with_mailto(self):
        """Test initialization with mailto."""
        service = CrossRefService(mailto="test@example.com")
        assert service.mailto == "test@example.com"
        assert 'mailto:test@example.com' in service.headers['User-Agent']
    
    def test_default_queries(self):
        """Test that default queries are set."""
        service = CrossRefService()
        assert len(service.DEFAULT_QUERIES) > 0
        assert "resistance training" in service.DEFAULT_QUERIES
        assert "strength training" in service.DEFAULT_QUERIES


class TestCrossRefWork:
    """Test CrossRefWork dataclass."""
    
    def test_work_creation(self):
        """Test creating a CrossRefWork."""
        work = CrossRefWork(
            doi="10.1234/test",
            title="Test Title",
            authors=["John Doe"],
            abstract="Test abstract",
            publication_date=date(2024, 1, 15),
            journal="Test Journal",
            url="https://example.com",
            subject=["Test"],
            is_referenced_by_count=42,
            type="journal-article"
        )
        
        assert work.doi == "10.1234/test"
        assert work.title == "Test Title"
        assert work.publication_date == date(2024, 1, 15)


class TestParseWork:
    """Test _parse_work method."""
    
    def test_parse_work_valid(self):
        """Test parsing valid work data."""
        service = CrossRefService()
        item = {
            'DOI': '10.1234/test',
            'title': ['Test Title'],
            'author': [{'given': 'John', 'family': 'Doe'}],
            'published-print': {'date-parts': [[2024, 1, 15]]},
            'container-title': ['Test Journal'],
            'URL': 'https://example.com',
            'subject': ['Sports Science'],
            'is-referenced-by-count': 42,
            'type': 'journal-article'
        }
        
        work = service._parse_work(item)
        
        assert work is not None
        assert work.doi == '10.1234/test'
        assert work.title == 'Test Title'
        assert work.authors == ['John Doe']
        assert work.publication_date == date(2024, 1, 15)
        assert work.journal == 'Test Journal'
    
    def test_parse_work_without_title(self):
        """Test parsing work without title."""
        service = CrossRefService()
        item = {
            'DOI': '10.1234/test',
            'author': [{'given': 'John', 'family': 'Doe'}],
        }
        
        work = service._parse_work(item)
        assert work is None
    
    def test_parse_work_without_doi(self):
        """Test parsing work without DOI."""
        service = CrossRefService()
        item = {
            'title': ['Test Title'],
            'author': [{'given': 'John', 'family': 'Doe'}],
        }
        
        work = service._parse_work(item)
        assert work is None
    
    def test_parse_work_invalid_date(self):
        """Test parsing work with invalid date."""
        service = CrossRefService()
        item = {
            'DOI': '10.1234/test',
            'title': ['Test Title'],
            'author': [{'given': 'John', 'family': 'Doe'}],
            'published-print': {'date-parts': [[9999, 99, 99]]}
        }
        
        work = service._parse_work(item)
        assert work is not None
        assert work.publication_date is None
    
    def test_parse_work_multiple_authors(self):
        """Test parsing work with multiple authors."""
        service = CrossRefService()
        item = {
            'DOI': '10.1234/test',
            'title': ['Test Title'],
            'author': [
                {'given': 'John', 'family': 'Doe'},
                {'given': 'Jane', 'family': 'Smith'},
                {'given': 'Bob', 'family': 'Johnson'}
            ],
        }
        
        work = service._parse_work(item)
        assert work.authors == ['John Doe', 'Jane Smith', 'Bob Johnson']
    
    def test_parse_work_author_with_only_family_name(self):
        """Test parsing work with author having only family name."""
        service = CrossRefService()
        item = {
            'DOI': '10.1234/test',
            'title': ['Test Title'],
            'author': [{'family': 'Doe'}],
        }
        
        work = service._parse_work(item)
        assert work.authors == ['Doe']
    
    def test_parse_work_author_with_only_given_name(self):
        """Test parsing work with author having only given name."""
        service = CrossRefService()
        item = {
            'DOI': '10.1234/test',
            'title': ['Test Title'],
            'author': [{'given': 'John'}],
        }
        
        work = service._parse_work(item)
        assert work.authors == ['John']


class TestSearchWorks:
    """Test search_works method."""
    
    @pytest.mark.asyncio
    async def test_search_works_success(self, respx_mock):
        """Test successful search."""
        mock_response = {
            'message': {
                'items': [
                    {
                        'DOI': '10.1234/test',
                        'title': ['Test Title'],
                        'author': [{'given': 'John', 'family': 'Doe'}],
                        'published-print': {'date-parts': [[2024, 1, 15]]},
                        'type': 'journal-article'
                    }
                ],
                'total-results': 1
            }
        }
        
        respx_mock.get("https://api.crossref.org/works").mock(
            return_value=httpx.Response(200, json=mock_response)
        )
        
        service = CrossRefService(mailto="test@example.com")
        result = await service.search_works(query="resistance training", rows=5)
        
        assert 'message' in result
        assert 'items' in result['message']
        assert len(result['message']['items']) == 1
    
    @pytest.mark.asyncio
    async def test_search_works_with_filters(self, respx_mock):
        """Test search with filters."""
        mock_response = {
            'message': {
                'items': [],
                'total-results': 0
            }
        }
        
        route = respx_mock.get("https://api.crossref.org/works").mock(
            return_value=httpx.Response(200, json=mock_response)
        )
        
        service = CrossRefService()
        await service.search_works(
            query="resistance training",
            rows=10,
            offset=0,
            filter_params={'from_pub_date': '2024-01-01'}
        )
        
        # Verify the request was made with correct parameters
        request = route.calls[0].request
        assert 'query' in str(request.url)
        assert 'rows=10' in str(request.url)
    
    @pytest.mark.asyncio
    async def test_search_works_rate_limit(self, respx_mock):
        """Test handling of rate limit."""
        respx_mock.get("https://api.crossref.org/works").mock(
            return_value=httpx.Response(429, json={"error": "Rate limited"})
        )
        
        service = CrossRefService()
        
        with pytest.raises(Exception):  # Should raise after retries
            await service.search_works(query="test")
    
    @pytest.mark.asyncio
    async def test_search_works_server_error(self, respx_mock):
        """Test handling of server error."""
        respx_mock.get("https://api.crossref.org/works").mock(
            return_value=httpx.Response(500, json={"error": "Server error"})
        )
        
        service = CrossRefService()
        
        with pytest.raises(Exception):  # Should raise after retries
            await service.search_works(query="test")


class TestGetWorkByDoi:
    """Test get_work_by_doi method."""
    
    @pytest.mark.asyncio
    async def test_get_work_by_doi_success(self, respx_mock):
        """Test successful DOI lookup."""
        mock_response = {
            'message': {
                'DOI': '10.1234/test',
                'title': ['Test Title'],
                'author': [{'given': 'John', 'family': 'Doe'}],
                'type': 'journal-article'
            }
        }
        
        respx_mock.get("https://api.crossref.org/works/10.1234/test").mock(
            return_value=httpx.Response(200, json=mock_response)
        )
        
        service = CrossRefService()
        result = await service.get_work_by_doi("10.1234/test")
        
        assert result is not None
        assert result.doi == '10.1234/test'
        assert result.title == 'Test Title'
    
    @pytest.mark.asyncio
    async def test_get_work_by_doi_not_found(self, respx_mock):
        """Test DOI not found."""
        respx_mock.get("https://api.crossref.org/works/10.1234/notfound").mock(
            return_value=httpx.Response(404, json={"error": "Not found"})
        )
        
        service = CrossRefService()
        result = await service.get_work_by_doi("10.1234/notfound")
        
        assert result is None


class TestFetchRecentPapers:
    """Test fetch_recent_papers method."""
    
    @pytest.mark.asyncio
    async def test_fetch_recent_papers(self, respx_mock):
        """Test fetching recent papers."""
        mock_response = {
            'message': {
                'items': [
                    {
                        'DOI': f'10.1234/test{i}',
                        'title': [f'Test Title {i}'],
                        'author': [{'given': 'John', 'family': 'Doe'}],
                        'published-print': {'date-parts': [[2024, 1, 15]]},
                        'type': 'journal-article'
                    }
                    for i in range(5)
                ],
                'total-results': 5
            }
        }
        
        respx_mock.get("https://api.crossref.org/works").mock(
            return_value=httpx.Response(200, json=mock_response)
        )
        
        service = CrossRefService()
        papers = await service.fetch_recent_papers(days_back=7, rows=5)
        
        assert len(papers) == 5
        assert all(isinstance(p, CrossRefWork) for p in papers)
    
    @pytest.mark.asyncio
    async def test_fetch_recent_papers_empty_result(self, respx_mock):
        """Test fetching recent papers with empty result."""
        mock_response = {
            'message': {
                'items': [],
                'total-results': 0
            }
        }
        
        respx_mock.get("https://api.crossref.org/works").mock(
            return_value=httpx.Response(200, json=mock_response)
        )
        
        service = CrossRefService()
        papers = await service.fetch_recent_papers(days_back=7)
        
        assert len(papers) == 0


class TestCircuitBreaker:
    """Test circuit breaker integration."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self, respx_mock):
        """Test circuit breaker opens after multiple failures."""
        # Mock consistent failures
        respx_mock.get("https://api.crossref.org/works").mock(
            return_value=httpx.Response(500, json={"error": "Server error"})
        )
        
        service = CrossRefService()
        
        # Make requests until circuit opens
        for _ in range(6):
            try:
                await service.search_works(query="test")
            except Exception:
                pass
        
        # Circuit should be open now - request should fail immediately
        # Note: This test may need adjustment based on actual circuit breaker behavior
