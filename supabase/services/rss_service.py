"""
RSS Feed Service for Research Agent.

Features:
- Graceful XML parsing with error handling
- CDATA section support
- Multiple namespace support (RSS 2.0, RSS 1.0, Atom)
- Configurable timeouts with exponential backoff
- Feed validation before parsing
- Retry logic for failed fetches
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, date
import httpx
import xml.etree.ElementTree as ET
from html import unescape
import re
import logging

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

# Configure logger
logger = logging.getLogger(__name__)

# XML namespaces commonly used in RSS/Atom feeds
NAMESPACES = {
    'atom': 'http://www.w3.org/2005/Atom',
    'rss1': 'http://purl.org/rss/1.0/',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'content': 'http://purl.org/rss/1.0/modules/content/',
    'media': 'http://search.yahoo.com/mrss/',
}


@dataclass
class RSSArticle:
    """Represents an article from an RSS feed."""
    title: str
    link: str
    description: Optional[str]
    publication_date: Optional[date]
    authors: List[str]
    source: str
    doi: Optional[str]
    categories: List[str]


class RSSService:
    """Service for fetching and parsing RSS feeds from scientific journals with resilience."""
    
    # RSS feeds for exercise science and sports medicine journals
    DEFAULT_FEEDS = {
        # Scientific journals
        # Note: Some LWW journals block direct RSS access. Using PubMed for these instead.
        'frontiers_sports': {
            'name': 'Frontiers in Sports and Active Living',
            'url': 'https://www.frontiersin.org/journals/sports-and-active-living/rss',
            'categories': ['sports_science', 'exercise', 'research']
        },
        'jissn': {
            'name': 'Journal of ISSN',
            'url': 'https://jissn.biomedcentral.com/articles/most-recent/rss.xml',
            'categories': ['nutrition', 'supplements', 'research']
        },
        'ejp': {
            'name': 'European Journal of Physiology',
            'url': 'https://link.springer.com/search.rss?facet-content-type=Article&facet-journal-id=424&channel-name=Pfl%C3%BCgers%20Archiv%20-%20European%20Journal%20of%20Physiology',
            'categories': ['physiology', 'research']
        },
        'jappl': {
            'name': 'Journal of Applied Physiology',
            'url': 'https://www.physiology.org/action/showFeed?type=etoc&feed=rss&jc=jappl',
            'categories': ['physiology', 'research']
        },
        'sports_medicine': {
            'name': 'Sports Medicine',
            'url': 'https://link.springer.com/search.rss?facet-content-type=Article&facet-journal-id=40279&channel-name=Sports%20Medicine',
            'categories': ['sports_medicine', 'research']
        },
        'bjsm': {
            'name': 'British Journal of Sports Medicine',
            'url': 'https://bjsm.bmj.com/rss/current.xml',
            'categories': ['sports_medicine', 'injury', 'research']
        },

        # Practical fitness sources
        'sbs': {
            'name': 'Stronger By Science',
            'url': 'https://www.strongerbyscience.com/feed/',
            'categories': ['strength', 'hypertrophy', 'programming']
        },
        'examine': {
            'name': 'Examine.com',
            'url': 'https://examine.com/blog/feed/',
            'categories': ['nutrition', 'supplements']
        },
        'menno': {
            'name': 'Menno Henselmans',
            'url': 'https://mennohenselmans.com/feed/',
            'categories': ['hypertrophy', 'nutrition']
        },
        'weightology': {
            'name': 'Weightology',
            'url': 'https://weightology.net/feed/',
            'categories': ['strength', 'nutrition', 'research']
        },
        # YouTube channels with fitness science content
        'jeff_nippard_yt': {
            'name': 'Jeff Nippard (YouTube)',
            'url': 'https://www.youtube.com/feeds/videos.xml?channel_id=UC68TLK0mAEzUyHx5x5k-S1Q',
            'categories': ['hypertrophy', 'technique', 'research']
        },
        'renaissance_yt': {
            'name': 'Renaissance Periodization (YouTube)',
            'url': 'https://www.youtube.com/feeds/videos.xml?channel_id=UCfQgsKhHjSyRLOp9mnffqVg',
            'categories': ['programming', 'hypertrophy', 'nutrition']
        },
        'precision_nutrition': {
            'name': 'Precision Nutrition',
            'url': 'https://www.precisionnutrition.com/feed/',
            'categories': ['nutrition', 'coaching']
        }
    }
    
    def __init__(self, feeds_config: Optional[Dict[str, Dict[str, str]]] = None):
        """
        Initialize RSS service.
        
        Args:
            feeds_config: Custom feed configuration (optional)
        """
        self.feeds = feeds_config or self.DEFAULT_FEEDS
        self.headers = {
            'User-Agent': 'FitnessAI-KnowledgeBot/1.0'
        }
        self.logger = logging.getLogger(__name__)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def fetch_feed(self, feed_url: str, timeout: float = 30.0) -> Optional[str]:
        """
        Fetch RSS feed content with retry logic.
        
        Args:
            feed_url: URL of the RSS feed
            timeout: Request timeout in seconds
        
        Returns:
            Raw XML content or None if failed
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                feed_url,
                headers=self.headers,
                timeout=timeout,
                follow_redirects=True
            )
            response.raise_for_status()
            return response.text
    
    def _validate_feed(self, xml_content: str) -> bool:
        """
        Validate that content is valid XML before parsing.
        
        Args:
            xml_content: Raw XML content
            
        Returns:
            True if valid, False otherwise
        """
        if not xml_content or not xml_content.strip():
            self.logger.warning("Empty feed content")
            return False
        
        # Check for basic XML structure
        if not xml_content.strip().startswith('<?xml') and not xml_content.strip().startswith('<'):
            self.logger.warning("Content does not appear to be XML")
            return False
        
        return True
    
    def parse_feed(self, xml_content: str, source_name: str) -> List[RSSArticle]:
        """
        Parse RSS XML content into articles with support for multiple formats.
        
        Supports:
        - RSS 2.0
        - RSS 1.0 (RDF)
        - Atom 1.0
        
        Args:
            xml_content: Raw XML content
            source_name: Name of the source
        
        Returns:
            List of RSSArticle objects
        """
        articles = []
        
        # Validate feed before parsing
        if not self._validate_feed(xml_content):
            return articles
        
        try:
            # Parse XML with CDATA support
            # ET.parse handles CDATA automatically in Python 3.6+
            root = ET.fromstring(xml_content)
            
            # Determine feed type and extract items
            items = self._extract_items(root)
            
            for item in items:
                try:
                    article = self._parse_item(item, source_name)
                    if article:
                        articles.append(article)
                except Exception as e:
                    self.logger.warning(f"Error parsing RSS item: {e}")
                    continue
                    
        except ET.ParseError as e:
            self.logger.error(f"XML parse error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error parsing feed: {e}")
        
        return articles
    
    def _extract_items(self, root: ET.Element) -> List[ET.Element]:
        """
        Extract items/entries from feed based on format.
        
        Args:
            root: Root XML element
            
        Returns:
            List of item/entry elements
        """
        items = []
        
        # Get tag without namespace for easier checking
        root_tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag
        
        # RSS 2.0
        if root_tag == 'rss':
            channel = root.find('.//channel')
            if channel is not None:
                items = channel.findall('item')
        
        # Atom feed
        elif root_tag == 'feed':
            # Atom uses 'entry' elements with namespace
            atom_ns = NAMESPACES['atom']
            items = root.findall(f'{{{atom_ns}}}entry')
        
        # RSS 1.0 (RDF)
        elif root_tag == 'RDF':
            # RSS 1.0 uses items directly under RDF with namespace
            rss_ns = NAMESPACES['rss1']
            items = root.findall(f'{{{rss_ns}}}item')
        
        # Try generic fallback
        else:
            # Try to find items without namespace
            items = root.findall('.//item')
            if not items:
                # Try with common namespaces
                for ns in NAMESPACES.values():
                    items = root.findall(f'.//{{{ns}}}item')
                    if items:
                        break
            
            # Try entries (Atom style)
            if not items:
                for ns in NAMESPACES.values():
                    items = root.findall(f'.//{{{ns}}}entry')
                    if items:
                        break
        
        return items
    
    def _parse_item(self, item: ET.Element, source_name: str) -> Optional[RSSArticle]:
        """
        Parse a single RSS/Atom item with namespace support.
        
        Args:
            item: XML item element
            source_name: Name of the source
            
        Returns:
            RSSArticle or None if invalid
        """
        # Get title with namespace fallback
        title = self._get_text_content(item, 'title', default='')
        title = unescape(title) if title else ''
        
        if not title:
            return None
        
        # Get link with namespace fallback and attribute support (Atom)
        link = self._get_link(item)
        
        # Get description/abstract with multiple field support
        description = self._get_description(item)
        
        # Get publication date with multiple field support
        pub_date = self._get_publication_date(item)
        
        # Get authors with multiple field support
        authors = self._get_authors(item)
        
        # Get categories with multiple field support
        categories = self._get_categories(item)
        
        # Try to extract DOI from link or description
        doi = self._extract_doi(link, description)
        
        return RSSArticle(
            title=title,
            link=link,
            description=description,
            publication_date=pub_date,
            authors=authors,
            source=source_name,
            doi=doi,
            categories=categories
        )
    
    def _get_text_content(self, element: ET.Element, tag: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get text content from element with namespace fallback.
        
        Args:
            element: Parent XML element
            tag: Tag name to find
            default: Default value if not found
            
        Returns:
            Text content or default
        """
        # Try without namespace first
        elem = element.find(tag)
        if elem is not None and elem.text:
            return elem.text
        
        # Try with common namespaces
        for prefix, ns in NAMESPACES.items():
            elem = element.find(f'{{{ns}}}{tag}')
            if elem is not None and elem.text:
                return elem.text
        
        return default
    
    def _get_link(self, item: ET.Element) -> str:
        """
        Extract link from item with support for various formats.
        
        Args:
            item: XML item element
            
        Returns:
            Link URL
        """
        # Try standard link element
        link_elem = item.find('link')
        if link_elem is not None:
            if link_elem.text:
                return link_elem.text
            # Atom uses href attribute
            href = link_elem.get('href')
            if href:
                return href
        
        # Try with namespaces
        for prefix, ns in NAMESPACES.items():
            link_elem = item.find(f'{{{ns}}}link')
            if link_elem is not None:
                if link_elem.text:
                    return link_elem.text
                href = link_elem.get('href')
                if href:
                    return href
        
        # Try guid with isPermaLink
        guid_elem = item.find('guid')
        if guid_elem is not None:
            is_permalink = guid_elem.get('isPermaLink', 'true').lower() == 'true'
            if is_permalink and guid_elem.text:
                return guid_elem.text
        
        return ''
    
    def _get_description(self, item: ET.Element) -> Optional[str]:
        """
        Extract description/abstract with multiple field support.
        
        Args:
            item: XML item element
            
        Returns:
            Description text or None
        """
        # Try multiple fields in order of preference
        fields = ['description', 'summary', 'content', 'abstract']
        
        for field in fields:
            text = self._get_text_content(item, field)
            if text:
                # Unescape HTML entities
                text = unescape(text)
                # Strip HTML tags
                text = re.sub(r'<[^>]+>', '', text)
                # Strip CDATA markers if present
                text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', text, flags=re.DOTALL)
                return text.strip() if text.strip() else None
        
        return None
    
    def _get_publication_date(self, item: ET.Element) -> Optional[date]:
        """
        Extract publication date with multiple field support.
        
        Args:
            item: XML item element
            
        Returns:
            datetime.date or None
        """
        # Try multiple date fields
        date_fields = ['pubDate', 'published', 'updated', 'date', 'dc:date']
        
        for field in date_fields:
            if field == 'dc:date':
                # Dublin Core namespace
                ns = NAMESPACES.get('dc')
                elem = item.find(f'{{{ns}}}date') if ns else None
            else:
                elem = item.find(field)
                # Try with namespaces
                if elem is None:
                    for prefix, ns in NAMESPACES.items():
                        elem = item.find(f'{{{ns}}}{field}')
                        if elem is not None:
                            break
            
            if elem is not None and elem.text:
                parsed_date = self._parse_date(elem.text)
                if parsed_date:
                    return parsed_date.date() if isinstance(parsed_date, datetime) else parsed_date
        
        return None
    
    def _get_authors(self, item: ET.Element) -> List[str]:
        """
        Extract authors with multiple field support.
        
        Args:
            item: XML item element
            
        Returns:
            List of author names
        """
        authors = []
        
        # Try Atom author elements
        atom_ns = NAMESPACES.get('atom')
        if atom_ns:
            for author_elem in item.findall(f'{{{atom_ns}}}author'):
                name_elem = author_elem.find(f'{{{atom_ns}}}name')
                if name_elem is not None and name_elem.text:
                    authors.append(name_elem.text)
        
        # Try Dublin Core creator
        dc_ns = NAMESPACES.get('dc')
        if dc_ns:
            for creator_elem in item.findall(f'{{{dc_ns}}}creator'):
                if creator_elem.text:
                    authors.append(creator_elem.text)
        
        # Try standard author element
        author_elem = item.find('author')
        if author_elem is not None and author_elem.text and not authors:
            authors.append(author_elem.text)
        
        return authors
    
    def _get_categories(self, item: ET.Element) -> List[str]:
        """
        Extract categories with multiple field support.
        
        Args:
            item: XML item element
            
        Returns:
            List of category names
        """
        categories = []
        
        # Try standard category elements
        for cat_elem in item.findall('category'):
            if cat_elem.text:
                categories.append(cat_elem.text)
            # Atom uses term attribute
            term = cat_elem.get('term')
            if term:
                categories.append(term)
        
        # Try with namespaces
        for prefix, ns in NAMESPACES.items():
            for cat_elem in item.findall(f'{{{ns}}}category'):
                if cat_elem.text:
                    categories.append(cat_elem.text)
                term = cat_elem.get('term')
                if term:
                    categories.append(term)
        
        # Try Dublin Core subject
        dc_ns = NAMESPACES.get('dc')
        if dc_ns:
            for subject_elem in item.findall(f'{{{dc_ns}}}subject'):
                if subject_elem.text:
                    categories.append(subject_elem.text)
        
        return categories
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse various date formats commonly found in RSS feeds.
        
        Args:
            date_str: Date string to parse
            
        Returns:
            datetime or None
        """
        if not date_str:
            return None
        
        # Clean up the string
        date_str = date_str.strip()
        
        # Common date formats in RSS feeds
        formats = [
            '%a, %d %b %Y %H:%M:%S %z',      # RFC 2822 with timezone
            '%a, %d %b %Y %H:%M:%S %Z',      # RFC 2822 with named timezone
            '%Y-%m-%dT%H:%M:%S%z',           # ISO 8601 with timezone
            '%Y-%m-%dT%H:%M:%SZ',            # ISO 8601 UTC
            '%Y-%m-%dT%H:%M:%S.%f%z',        # ISO 8601 with milliseconds
            '%Y-%m-%dT%H:%M:%S.%fZ',         # ISO 8601 with milliseconds UTC
            '%Y-%m-%d',                       # ISO date only
            '%d %b %Y',                       # Day Month Year
            '%d %b %Y %H:%M:%S',             # Day Month Year with time
            '%Y-%m-%d %H:%M:%S',             # Common SQL format
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # Try parsing with dateutil as fallback
        try:
            from dateutil import parser
            return parser.parse(date_str)
        except Exception:
            pass
        
        self.logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def _extract_doi(self, link: Optional[str], description: Optional[str]) -> Optional[str]:
        """
        Extract DOI from link or description.
        
        Args:
            link: URL link
            description: Article description
            
        Returns:
            DOI string or None
        """
        doi_pattern = r'10\.\d{4,}/[^\s<>"]+'
        
        if link:
            match = re.search(doi_pattern, link)
            if match:
                return match.group(0)
        
        if description:
            match = re.search(doi_pattern, description)
            if match:
                return match.group(0)
        
        return None
    
    async def fetch_all_feeds(
        self,
        days_back: int = 30
    ) -> List[RSSArticle]:
        """
        Fetch and parse all configured feeds.
        
        Args:
            days_back: Filter articles published within this many days
        
        Returns:
            List of RSSArticle objects
        """
        from datetime import timedelta
        
        cutoff_date = date.today() - timedelta(days=days_back)
        all_articles = []
        
        for feed_id, feed_config in self.feeds.items():
            try:
                self.logger.info(f"Fetching feed: {feed_config['name']}")
                
                xml_content = await self.fetch_feed(feed_config['url'])
                if xml_content:
                    articles = self.parse_feed(xml_content, feed_config['name'])
                    
                    # Filter by date
                    recent_articles = [
                        article for article in articles
                        if article.publication_date is None or article.publication_date >= cutoff_date
                    ]
                    
                    all_articles.extend(recent_articles)
                    self.logger.info(f"Found {len(recent_articles)} articles from {feed_config['name']}")
                else:
                    self.logger.warning(f"Failed to fetch feed: {feed_config['name']}")
                    
            except Exception as e:
                self.logger.error(f"Error processing feed {feed_id}: {e}")
                continue
        
        return all_articles
    
    def get_feed_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all configured feeds.
        
        Returns:
            Dictionary with feed configurations
        """
        return {
            feed_id: {
                'name': config['name'],
                'url': config['url'],
                'enabled': True
            }
            for feed_id, config in self.feeds.items()
        }
