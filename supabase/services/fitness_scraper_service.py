"""
Fitness Website Scraper Service.

Scrapes fitness websites that don't provide RSS feeds for articles and content.
Uses BeautifulSoup for HTML parsing with rate limiting and retry logic.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, date
import asyncio
import re
import logging

import httpx
from bs4 import BeautifulSoup
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

logger = logging.getLogger(__name__)


@dataclass
class ScrapedArticle:
    """Represents an article scraped from a fitness website."""
    title: str
    link: str
    description: Optional[str]
    publication_date: Optional[date]
    authors: List[str]
    source: str
    categories: List[str]
    content_preview: Optional[str] = None


class FitnessScraperService:
    """
    Scraper for fitness websites without RSS feeds.

    Features:
    - Configurable site definitions
    - Rate limiting per domain
    - Retry logic with exponential backoff
    - HTML parsing with BeautifulSoup
    - Content extraction and cleaning
    """

    # Site configurations for scraping
    # Whitelist will be populated with trusted sources later
    # Example format:
    # 'examine': {
    #     'name': 'Examine.com',
    #     'base_url': 'https://examine.com/articles/',
    #     'article_selector': 'article, .blog-post',
    #     'title_selector': 'h2 a, h3 a',
    #     'link_selector': 'h2 a, h3 a',
    #     'description_selector': '.excerpt, .summary',
    #     'date_selector': '.date, time',
    #     'categories': ['nutrition', 'supplements']
    # }
    SITES = {}

    def __init__(
        self,
        sites_config: Optional[Dict[str, Dict[str, Any]]] = None,
        rate_limit_delay: float = 2.0,
        timeout: float = 30.0
    ):
        """
        Initialize the scraper service.

        Args:
            sites_config: Custom site configuration (optional, defaults to SITES)
            rate_limit_delay: Delay between requests to same domain (seconds)
            timeout: Request timeout (seconds)
        """
        self.sites = sites_config or self.SITES
        self.rate_limit_delay = rate_limit_delay
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; FitnessAI-KnowledgeBot/1.0; +https://github.com/fitness-ai)'
        }

        # Track last request time per domain for rate limiting
        self._last_request: Dict[str, float] = {}

    async def _rate_limit(self, domain: str) -> None:
        """Apply rate limiting for a domain."""
        import time

        current_time = time.time()
        last_request = self._last_request.get(domain, 0)
        elapsed = current_time - last_request

        if elapsed < self.rate_limit_delay:
            wait_time = self.rate_limit_delay - elapsed
            self.logger.debug(f"Rate limiting {domain}: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)

        self._last_request[domain] = time.time()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def _fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch a web page with retry logic.

        Args:
            url: URL to fetch

        Returns:
            HTML content or None if failed
        """
        # Extract domain for rate limiting
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        await self._rate_limit(domain)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self.headers,
                timeout=self.timeout,
                follow_redirects=True
            )
            response.raise_for_status()
            return response.text

    def _parse_date(self, date_str: str) -> Optional[date]:
        """
        Parse various date formats commonly found on websites.

        Args:
            date_str: Date string to parse

        Returns:
            datetime.date or None
        """
        if not date_str:
            return None

        date_str = date_str.strip()

        # Common date formats
        formats = [
            '%B %d, %Y',          # January 15, 2024
            '%b %d, %Y',          # Jan 15, 2024
            '%Y-%m-%d',           # 2024-01-15
            '%d/%m/%Y',           # 15/01/2024
            '%m/%d/%Y',           # 01/15/2024
            '%d %B %Y',           # 15 January 2024
            '%d %b %Y',           # 15 Jan 2024
            '%Y/%m/%d',           # 2024/01/15
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        # Try dateutil as fallback
        try:
            from dateutil import parser
            return parser.parse(date_str).date()
        except Exception:
            pass

        return None

    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        if not text:
            return ""

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        return text

    def _extract_articles_from_page(
        self,
        html: str,
        site_config: Dict[str, Any],
        base_url: str
    ) -> List[ScrapedArticle]:
        """
        Extract articles from HTML content.

        Args:
            html: HTML content
            site_config: Site configuration
            base_url: Base URL for relative links

        Returns:
            List of ScrapedArticle objects
        """
        articles = []
        soup = BeautifulSoup(html, 'html.parser')

        # Find all article elements
        article_elements = soup.select(site_config['article_selector'])

        for elem in article_elements:
            try:
                # Extract title
                title_elem = elem.select_one(site_config['title_selector'])
                if not title_elem:
                    continue

                title = self._clean_text(title_elem.get_text())
                if not title:
                    continue

                # Extract link
                link_elem = elem.select_one(site_config['link_selector'])
                link = ""
                if link_elem:
                    link = link_elem.get('href', '')
                    # Handle relative URLs
                    if link and not link.startswith('http'):
                        from urllib.parse import urljoin
                        link = urljoin(base_url, link)

                # Extract description
                description = None
                desc_elem = elem.select_one(site_config['description_selector'])
                if desc_elem:
                    description = self._clean_text(desc_elem.get_text())
                    # Limit description length
                    if description and len(description) > 500:
                        description = description[:500] + "..."

                # Extract date
                pub_date = None
                date_elem = elem.select_one(site_config['date_selector'])
                if date_elem:
                    date_text = date_elem.get_text() or date_elem.get('datetime', '')
                    pub_date = self._parse_date(self._clean_text(date_text))

                # Create article
                article = ScrapedArticle(
                    title=title,
                    link=link,
                    description=description,
                    publication_date=pub_date,
                    authors=[],  # Most blog sites don't show authors in listings
                    source=site_config['name'],
                    categories=site_config.get('categories', [])
                )

                articles.append(article)

            except Exception as e:
                self.logger.warning(f"Error parsing article element: {e}")
                continue

        return articles

    async def scrape_site(self, site_id: str) -> List[ScrapedArticle]:
        """
        Scrape articles from a specific site.

        Args:
            site_id: Site identifier from SITES config

        Returns:
            List of ScrapedArticle objects
        """
        if site_id not in self.sites:
            self.logger.error(f"Unknown site: {site_id}")
            return []

        site_config = self.sites[site_id]
        self.logger.info(f"Scraping site: {site_config['name']}")

        try:
            html = await self._fetch_page(site_config['base_url'])
            if not html:
                self.logger.warning(f"No content from {site_config['name']}")
                return []

            articles = self._extract_articles_from_page(
                html,
                site_config,
                site_config['base_url']
            )

            self.logger.info(f"Found {len(articles)} articles from {site_config['name']}")
            return articles

        except Exception as e:
            self.logger.error(f"Error scraping {site_config['name']}: {e}")
            return []

    async def scrape_all(
        self,
        site_ids: Optional[List[str]] = None
    ) -> List[ScrapedArticle]:
        """
        Scrape articles from all configured sites.

        Args:
            site_ids: Optional list of specific site IDs to scrape

        Returns:
            List of all ScrapedArticle objects
        """
        sites_to_scrape = site_ids or list(self.sites.keys())
        all_articles = []

        for site_id in sites_to_scrape:
            try:
                articles = await self.scrape_site(site_id)
                all_articles.extend(articles)
            except Exception as e:
                self.logger.error(f"Error scraping site {site_id}: {e}")
                continue

        self.logger.info(f"Total articles scraped: {len(all_articles)}")
        return all_articles

    def get_site_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all configured sites.

        Returns:
            Dictionary with site configurations and status
        """
        return {
            site_id: {
                'name': config['name'],
                'url': config['base_url'],
                'categories': config.get('categories', []),
                'enabled': True
            }
            for site_id, config in self.sites.items()
        }

    async def check_site_availability(self, site_id: str) -> Dict[str, Any]:
        """
        Check if a site is accessible.

        Args:
            site_id: Site identifier

        Returns:
            Dictionary with availability status
        """
        if site_id not in self.sites:
            return {'available': False, 'error': 'Unknown site'}

        site_config = self.sites[site_id]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.head(
                    site_config['base_url'],
                    headers=self.headers,
                    timeout=10.0,
                    follow_redirects=True
                )

                return {
                    'available': response.status_code == 200,
                    'status_code': response.status_code,
                    'url': site_config['base_url']
                }

        except Exception as e:
            return {
                'available': False,
                'error': str(e),
                'url': site_config['base_url']
            }
