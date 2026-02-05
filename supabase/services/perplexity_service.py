"""
Perplexity Sonar API Service for research article search.

Provides integration with Perplexity's Sonar API for searching
scientific articles and fitness research with citations.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import logging
import os

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

logger = logging.getLogger(__name__)


@dataclass
class PerplexityArticle:
    """Represents an article found via Perplexity Sonar API."""
    title: str
    url: str
    snippet: str
    citations: List[str] = field(default_factory=list)
    source_type: str = 'perplexity'
    relevance_score: Optional[float] = None
    search_query: Optional[str] = None


@dataclass
class PerplexitySearchResult:
    """Result from a Perplexity search query."""
    answer: str
    citations: List[str]
    articles: List[PerplexityArticle]
    query: str
    model: str = 'sonar'


class PerplexityService:
    """
    Perplexity Sonar API service for scientific article search.

    Features:
    - Search for fitness/training research
    - Extract citations from responses
    - Rate limiting and retry logic
    - Configurable search queries
    """

    # Default search queries for fitness research
    SEARCH_QUERIES = [
        "hypertrophy training research",
        "strength training scientific study",
        "muscle growth evidence-based",
        "resistance training meta-analysis",
        "protein synthesis exercise",
        "progressive overload study",
        "recovery between workouts research",
        "training volume hypertrophy"
    ]

    # Perplexity API endpoints
    API_BASE_URL = "https://api.perplexity.ai"
    CHAT_COMPLETIONS_ENDPOINT = "/chat/completions"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "sonar",
        timeout: float = 60.0,
        max_tokens: int = 1024
    ):
        """
        Initialize Perplexity service.

        Args:
            api_key: Perplexity API key (defaults to env var)
            model: Model to use (sonar, sonar-pro)
            timeout: Request timeout in seconds
            max_tokens: Maximum tokens in response
        """
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY", "")
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.logger = logging.getLogger(__name__)

        if not self.api_key:
            self.logger.warning("PERPLEXITY_API_KEY not configured")

    @property
    def headers(self) -> Dict[str, str]:
        """Get API request headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def _make_request(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Make a request to Perplexity API.

        Args:
            messages: Chat messages for the API

        Returns:
            API response as dictionary
        """
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY not configured")

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "return_citations": True
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.API_BASE_URL}{self.CHAT_COMPLETIONS_ENDPOINT}",
                headers=self.headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()

    async def search(
        self,
        query: str,
        system_prompt: Optional[str] = None
    ) -> Optional[PerplexitySearchResult]:
        """
        Search for information using Perplexity Sonar.

        Args:
            query: Search query
            system_prompt: Optional system prompt for context

        Returns:
            PerplexitySearchResult or None if failed
        """
        if not self.api_key:
            self.logger.warning("Perplexity API key not configured, skipping search")
            return None

        default_system = """You are a research assistant focused on fitness and exercise science.
Provide evidence-based answers with citations to scientific studies.
Focus on peer-reviewed research, meta-analyses, and systematic reviews.
Always cite your sources."""

        messages = [
            {"role": "system", "content": system_prompt or default_system},
            {"role": "user", "content": query}
        ]

        try:
            response = await self._make_request(messages)

            # Extract answer and citations
            choice = response.get("choices", [{}])[0]
            message = choice.get("message", {})
            answer = message.get("content", "")
            citations = response.get("citations", [])

            # Build articles from citations
            articles = []
            for i, citation in enumerate(citations):
                if isinstance(citation, str):
                    articles.append(PerplexityArticle(
                        title=f"Source {i + 1}",
                        url=citation,
                        snippet="",
                        citations=[citation],
                        search_query=query
                    ))
                elif isinstance(citation, dict):
                    articles.append(PerplexityArticle(
                        title=citation.get("title", f"Source {i + 1}"),
                        url=citation.get("url", ""),
                        snippet=citation.get("snippet", ""),
                        citations=[citation.get("url", "")],
                        search_query=query
                    ))

            return PerplexitySearchResult(
                answer=answer,
                citations=citations if isinstance(citations, list) else [],
                articles=articles,
                query=query,
                model=self.model
            )

        except Exception as e:
            self.logger.error(f"Perplexity search failed for query '{query}': {e}")
            return None

    async def search_research(
        self,
        queries: Optional[List[str]] = None,
        max_results: int = 10
    ) -> List[PerplexityArticle]:
        """
        Search for research articles using multiple queries.

        Args:
            queries: List of search queries (defaults to SEARCH_QUERIES)
            max_results: Maximum total articles to return

        Returns:
            List of PerplexityArticle objects
        """
        if not self.api_key:
            self.logger.warning("Perplexity API key not configured, skipping research search")
            return []

        search_queries = queries or self.SEARCH_QUERIES
        all_articles: List[PerplexityArticle] = []
        seen_urls = set()

        for query in search_queries:
            if len(all_articles) >= max_results:
                break

            try:
                result = await self.search(query)
                if result:
                    for article in result.articles:
                        # Deduplicate by URL
                        if article.url and article.url not in seen_urls:
                            seen_urls.add(article.url)
                            all_articles.append(article)

                            if len(all_articles) >= max_results:
                                break

                # Small delay between queries to be nice to API
                await asyncio.sleep(0.5)

            except Exception as e:
                self.logger.error(f"Search failed for query '{query}': {e}")
                continue

        self.logger.info(f"Perplexity search found {len(all_articles)} unique articles")
        return all_articles

    async def search_topic(
        self,
        topic: str,
        include_meta_analyses: bool = True,
        include_reviews: bool = True
    ) -> Optional[PerplexitySearchResult]:
        """
        Search for a specific fitness/training topic.

        Args:
            topic: The topic to search for
            include_meta_analyses: Prefer meta-analyses
            include_reviews: Prefer systematic reviews

        Returns:
            PerplexitySearchResult or None
        """
        query_parts = [topic]

        if include_meta_analyses:
            query_parts.append("meta-analysis")
        if include_reviews:
            query_parts.append("systematic review")

        query_parts.append("scientific study peer-reviewed")

        full_query = " ".join(query_parts)
        return await self.search(full_query)

    def is_configured(self) -> bool:
        """Check if the service is properly configured."""
        return bool(self.api_key)
