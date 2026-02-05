"""
CrossRef REST API Service for Research Agent.

Features:
- Retry logic with exponential backoff
- Circuit breaker pattern for resilience
- Rate limiting handling (429 errors)
- Improved date parsing with validation
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, date
import httpx
import logging

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    RetryError
)
from pybreaker import CircuitBreaker

# Configure logger
logger = logging.getLogger(__name__)

# Circuit breaker configuration
# After 5 failures, circuit opens for 60 seconds
crossref_breaker = CircuitBreaker(fail_max=5, reset_timeout=60)


@dataclass
class CrossRefWork:
    """Represents a work from CrossRef."""
    doi: str
    title: str
    authors: List[str]
    abstract: Optional[str]
    publication_date: Optional[date]
    journal: Optional[str]
    url: Optional[str]
    subject: List[str]
    is_referenced_by_count: int
    type: str


class CrossRefService:
    """Service for interacting with CrossRef REST API with resilience patterns."""
    
    BASE_URL = "https://api.crossref.org"
    
    # Fitness and exercise science related query terms
    DEFAULT_QUERIES = [
        "resistance training",
        "strength training",
        "muscle hypertrophy",
        "protein synthesis",
        "exercise physiology",
        "sports nutrition",
        "periodization",
        "training adaptation",
        "muscle recovery",
        "bodybuilding",
        "powerlifting",
        "weightlifting"
    ]
    
    def __init__(self, mailto: Optional[str] = None):
        """
        Initialize CrossRef service.
        
        Args:
            mailto: Email address for polite pool (recommended)
        """
        self.mailto = mailto
        self.headers = {
            'User-Agent': 'FitnessAI-KnowledgeBot/1.0'
        }
        if mailto:
            self.headers['User-Agent'] += f' (mailto:{mailto})'
        
        self.logger = logging.getLogger(__name__)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def _make_request(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic and rate limit handling.
        
        Args:
            client: HTTPX async client
            url: Request URL
            params: Query parameters
            
        Returns:
            JSON response
            
        Raises:
            httpx.HTTPStatusError: On non-retryable HTTP errors
        """
        response = await client.get(
            url,
            headers=self.headers,
            params=params,
            timeout=30.0
        )
        
        # Handle rate limiting (429)
        if response.status_code == 429:
            retry_after = response.headers.get('retry-after', '10')
            wait_time = int(retry_after) if retry_after.isdigit() else 10
            self.logger.warning(f"Rate limited by CrossRef. Waiting {wait_time}s")
            # Raise exception to trigger retry
            raise httpx.HTTPStatusError(
                f"Rate limited: {response.status_code}",
                request=response.request,
                response=response
            )
        
        # Handle server errors (5xx) - these will trigger retry
        if response.status_code >= 500:
            self.logger.warning(f"CrossRef server error: {response.status_code}")
            raise httpx.HTTPStatusError(
                f"Server error: {response.status_code}",
                request=response.request,
                response=response
            )
        
        response.raise_for_status()
        return response.json()
    
    @crossref_breaker
    async def search_works(
        self,
        query: str,
        filter_params: Optional[Dict[str, str]] = None,
        sort: str = 'relevance',
        order: str = 'desc',
        rows: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search for works in CrossRef with circuit breaker protection.
        
        Args:
            query: Search query
            filter_params: Filter parameters (e.g., {'from_pub_date': '2020-01-01'})
            sort: Sort field
            order: Sort order (asc/desc)
            rows: Number of results per page
            offset: Pagination offset
        
        Returns:
            Raw API response
            
        Raises:
            pybreaker.CircuitBreakerError: If circuit breaker is open
        """
        url = f"{self.BASE_URL}/works"
        
        params = {
            'query': query,
            'sort': sort,
            'order': order,
            'rows': rows,
            'offset': offset
        }
        
        if filter_params:
            params['filter'] = ','.join([f"{k}:{v}" for k, v in filter_params.items()])
        
        if self.mailto:
            params['mailto'] = self.mailto
        
        async with httpx.AsyncClient() as client:
            return await self._make_request(client, url, params)
    
    async def search_recent(
        self,
        days_back: int = 30,
        max_results: int = 100
    ) -> List[CrossRefWork]:
        """
        Search for recent works on fitness topics.
        
        Args:
            days_back: Number of days to look back
            max_results: Maximum total results
        
        Returns:
            List of CrossRefWork objects
        """
        from datetime import timedelta
        
        date_from = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        filter_params = {
            'from_pub_date': date_from,
            'type': 'journal-article'
        }
        
        all_works = []
        seen_dois = set()
        
        for query in self.DEFAULT_QUERIES:
            try:
                results_per_query = min(20, max_results // len(self.DEFAULT_QUERIES))
                
                data = await self.search_works(
                    query=query,
                    filter_params=filter_params,
                    sort='published',
                    order='desc',
                    rows=results_per_query
                )
                
                items = data.get('message', {}).get('items', [])
                
                for item in items:
                    work = self._parse_work(item)
                    if work and work.doi not in seen_dois:
                        seen_dois.add(work.doi)
                        all_works.append(work)
                
            except RetryError as e:
                self.logger.error(f"Retry failed for query '{query}': {e}")
                continue
            except Exception as e:
                self.logger.error(f"Error searching CrossRef for '{query}': {e}")
                continue
        
        return all_works[:max_results]
    
    @crossref_breaker
    async def get_work_by_doi(self, doi: str) -> Optional[CrossRefWork]:
        """
        Get a specific work by DOI with circuit breaker protection.
        
        Args:
            doi: The DOI to look up
        
        Returns:
            CrossRefWork or None
        """
        url = f"{self.BASE_URL}/works/{doi}"
        
        params = {}
        if self.mailto:
            params['mailto'] = self.mailto
        
        async with httpx.AsyncClient() as client:
            try:
                data = await self._make_request(client, url, params)
                item = data.get('message', {})
                return self._parse_work(item)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                raise
    
    def _parse_work(self, item: Dict[str, Any]) -> Optional[CrossRefWork]:
        """
        Parse a CrossRef work item with improved date validation.
        
        Args:
            item: Raw CrossRef work item
            
        Returns:
            CrossRefWork or None if parsing fails
        """
        doi = item.get('DOI')
        if not doi:
            return None
        
        # Get title
        titles = item.get('title', [])
        title = titles[0] if titles else item.get('container-title', [''])[0]
        
        # Get authors
        authors = []
        for author in item.get('author', []):
            given = author.get('given', '')
            family = author.get('family', '')
            if family:
                name = f"{given} {family}".strip()
                authors.append(name)
        
        # Get abstract (rarely available in CrossRef)
        abstract = item.get('abstract')
        
        # Get publication date with improved validation
        pub_date = self._parse_publication_date(item)
        
        # Get journal
        journal = None
        container = item.get('container-title', [])
        if container:
            journal = container[0]
        
        # Get URL
        url = item.get('URL')
        
        # Get subjects
        subjects = item.get('subject', [])
        
        # Get citation count
        cited_count = item.get('is-referenced-by-count', 0)
        
        # Get type
        work_type = item.get('type', 'unknown')
        
        return CrossRefWork(
            doi=doi,
            title=title,
            authors=authors,
            abstract=abstract,
            publication_date=pub_date,
            journal=journal,
            url=url,
            subject=subjects,
            is_referenced_by_count=cited_count,
            type=work_type
        )
    
    def _parse_publication_date(self, item: Dict[str, Any]) -> Optional[date]:
        """
        Parse publication date from CrossRef item with validation.
        
        CrossRef provides dates in date-parts format: [year, month, day]
        Some dates may be incomplete (e.g., only year, or year+month).
        
        Args:
            item: CrossRef work item
            
        Returns:
            datetime.date or None
        """
        # Try published-print first, then published-online
        date_parts = None
        
        published_print = item.get('published-print', {})
        if published_print and 'date-parts' in published_print:
            date_parts = published_print.get('date-parts', [])
        
        if not date_parts:
            published_online = item.get('published-online', {})
            if published_online and 'date-parts' in published_online:
                date_parts = published_online.get('date-parts', [])
        
        if not date_parts or not isinstance(date_parts, list) or len(date_parts) == 0:
            return None
        
        parts = date_parts[0]
        if not isinstance(parts, list) or len(parts) == 0:
            return None
        
        try:
            year = parts[0]
            # Validate year is reasonable (between 1900 and current year + 1)
            current_year = datetime.now().year
            if not isinstance(year, int) or year < 1900 or year > current_year + 1:
                self.logger.warning(f"Invalid year in CrossRef date: {year}")
                return None
            
            month = parts[1] if len(parts) > 1 else 1
            day = parts[2] if len(parts) > 2 else 1
            
            # Validate month and day
            month = max(1, min(12, month)) if isinstance(month, int) else 1
            day = max(1, min(31, day)) if isinstance(day, int) else 1
            
            return date(year, month, day)
            
        except (ValueError, TypeError, IndexError) as e:
            self.logger.warning(f"Failed to parse CrossRef date parts {parts}: {e}")
            return None
    
    @crossref_breaker
    async def get_journal_metrics(self, issn: str) -> Optional[Dict[str, Any]]:
        """
        Get journal metrics from CrossRef with circuit breaker protection.
        
        Args:
            issn: Journal ISSN
        
        Returns:
            Dictionary with journal metrics or None
        """
        url = f"{self.BASE_URL}/journals/{issn}"
        
        params = {}
        if self.mailto:
            params['mailto'] = self.mailto
        
        async with httpx.AsyncClient() as client:
            try:
                data = await self._make_request(client, url, params)
                return data.get('message', {})
            except Exception as e:
                self.logger.error(f"Error fetching journal metrics for {issn}: {e}")
                return None
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """
        Get current circuit breaker status for monitoring.
        
        Returns:
            Dictionary with circuit breaker state
        """
        return {
            'fail_counter': crossref_breaker.fail_counter,
            'state': str(crossref_breaker.current_state),
            'fail_max': crossref_breaker.fail_max,
            'reset_timeout': crossref_breaker.reset_timeout
        }
