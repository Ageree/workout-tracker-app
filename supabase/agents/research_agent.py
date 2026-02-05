"""
Research Agent (🔍) - Поиск и первичная фильтрация научных источников

Enhanced with:
- Trusted authors and journals priority boosting
- Journal-specific and author-specific search
- Source quality scoring based on authoritative sources database
"""

from typing import List, Optional, Dict, Any, Set
from datetime import datetime, timedelta, date
import asyncio
import re

from agents.base_agent import BaseAgent
from services.supabase_client import SupabaseClient, ResearchQueueItem
from services.pubmed_service import PubMedService, PubMedArticle
from services.crossref_service import CrossRefService, CrossRefWork
from services.rss_service import RSSService, RSSArticle
from services.fitness_scraper_service import FitnessScraperService, ScrapedArticle
from services.perplexity_service import PerplexityService, PerplexityArticle
from utils.date_utils import datetime_to_date


class ResearchAgent(BaseAgent):
    """
    Research Agent responsible for:
    - Searching scientific sources (PubMed, CrossRef, RSS)
    - Filtering by quality criteria
    - Adding sources to research queue
    - Priority boosting for trusted authors and journals
    """

    def __init__(
        self,
        supabase: SupabaseClient,
        pubmed_service: Optional[PubMedService] = None,
        crossref_service: Optional[CrossRefService] = None,
        rss_service: Optional[RSSService] = None,
        fitness_scraper: Optional[FitnessScraperService] = None,
        perplexity_service: Optional[PerplexityService] = None,
        days_back: int = 7,
        max_results_per_source: int = 20,
        enable_web_scraping: bool = False,  # Disabled until whitelist is configured
        enable_perplexity: bool = True,
        enable_trusted_source_search: bool = True  # Search specifically in trusted journals/by authors
    ):
        super().__init__(name="ResearchAgent", supabase=supabase)
        self.pubmed = pubmed_service or PubMedService()
        self.crossref = crossref_service or CrossRefService()
        self.rss = rss_service or RSSService()
        self.fitness_scraper = fitness_scraper or FitnessScraperService()
        self.perplexity = perplexity_service or PerplexityService()
        self.days_back = days_back
        self.max_results_per_source = max_results_per_source
        self.enable_web_scraping = enable_web_scraping
        self.enable_perplexity = enable_perplexity
        self.enable_trusted_source_search = enable_trusted_source_search
        self.stats['sources_found'] = 0
        self.stats['sources_added'] = 0
        self.stats['web_scraped'] = 0
        self.stats['perplexity_found'] = 0
        self.stats['trusted_sources_found'] = 0

        # Cached trusted sources (loaded from DB)
        self._trusted_authors: Dict[str, int] = {}  # normalized_name -> priority_boost
        self._trusted_journals: Dict[str, int] = {}  # normalized_name -> priority_boost
        self._trusted_sources_loaded = False
    
    async def _load_trusted_sources(self) -> None:
        """Load trusted authors and journals from database."""
        if self._trusted_sources_loaded:
            return

        try:
            # Load trusted authors
            authors = await self.supabase.get_trusted_authors()
            for author in authors:
                normalized = author.get('normalized_name', '').lower()
                boost = author.get('priority_boost', 2)
                if normalized:
                    self._trusted_authors[normalized] = boost

            # Load trusted journals
            journals = await self.supabase.get_trusted_journals()
            for journal in journals:
                normalized = journal.get('normalized_name', '').lower()
                boost = journal.get('priority_boost', 2)
                if normalized:
                    self._trusted_journals[normalized] = boost
                # Also add short name if available
                short_name = journal.get('short_name')
                if short_name:
                    self._trusted_journals[short_name.lower()] = boost

            self._trusted_sources_loaded = True
            self.logger.info(
                f"Loaded {len(self._trusted_authors)} trusted authors, "
                f"{len(self._trusted_journals)} trusted journals"
            )
        except Exception as e:
            self.logger.warning(f"Failed to load trusted sources: {e}")
            # Continue without trusted sources
            self._trusted_sources_loaded = True

    def _normalize_author_name(self, name: str) -> str:
        """Normalize author name for matching."""
        # Remove dots, extra spaces, convert to lowercase
        normalized = re.sub(r'[.]', '', name.lower())
        normalized = ' '.join(normalized.split())
        return normalized

    def _normalize_journal_name(self, name: str) -> str:
        """Normalize journal name for matching."""
        return name.lower().strip()

    def _get_author_boost(self, authors: List[str]) -> int:
        """
        Get maximum priority boost from author list.

        Args:
            authors: List of author names

        Returns:
            Maximum priority boost (0 if no trusted authors)
        """
        max_boost = 0
        for author in authors:
            normalized = self._normalize_author_name(author)
            # Check exact match
            if normalized in self._trusted_authors:
                max_boost = max(max_boost, self._trusted_authors[normalized])
            else:
                # Check partial match (author last name might be in the trusted list)
                for trusted_name, boost in self._trusted_authors.items():
                    if trusted_name in normalized or normalized in trusted_name:
                        max_boost = max(max_boost, boost)
                        break
        return max_boost

    def _get_journal_boost(self, journal: Optional[str]) -> int:
        """
        Get priority boost for a journal.

        Args:
            journal: Journal name

        Returns:
            Priority boost (0 if not trusted)
        """
        if not journal:
            return 0

        normalized = self._normalize_journal_name(journal)

        # Check exact match
        if normalized in self._trusted_journals:
            return self._trusted_journals[normalized]

        # Check partial match
        for trusted_name, boost in self._trusted_journals.items():
            if trusted_name in normalized or normalized in trusted_name:
                return boost

        return 0

    def _is_trusted_source(self, authors: List[str], journal: Optional[str]) -> bool:
        """Check if article is from a trusted source."""
        return self._get_author_boost(authors) > 0 or self._get_journal_boost(journal) > 0

    async def process(self) -> Dict[str, Any]:
        """
        Main processing: search all sources and add to queue.

        Returns:
            Dictionary with search results
        """
        self.logger.info("Starting research search...")

        # Load trusted sources from database
        await self._load_trusted_sources()

        results = {
            'pubmed': [],
            'crossref': [],
            'rss': [],
            'web_scraped': [],
            'perplexity': [],
            'trusted_journal_search': [],
            'trusted_author_search': [],
            'total_added': 0
        }

        # Search all sources concurrently
        tasks = [
            self._search_pubmed(),
            self._search_crossref(),
            self._search_rss()
        ]

        # Add trusted source specific searches if enabled
        if self.enable_trusted_source_search and self._trusted_sources_loaded:
            tasks.append(self._search_trusted_journals())
            tasks.append(self._search_by_trusted_authors())

        # Add web scraping if enabled
        if self.enable_web_scraping:
            tasks.append(self._search_web_sources())

        # Add Perplexity search if enabled
        if self.enable_perplexity and self.perplexity.is_configured():
            tasks.append(self._search_perplexity())

        search_results = await asyncio.gather(
            *tasks,
            return_exceptions=True
        )

        # Unpack results based on enabled sources
        pubmed_results = search_results[0]
        crossref_results = search_results[1]
        rss_results = search_results[2]

        # Calculate index for optional sources
        optional_idx = 3
        trusted_journal_results = []
        trusted_author_results = []
        web_results = []
        perplexity_results = []

        if self.enable_trusted_source_search and self._trusted_sources_loaded:
            trusted_journal_results = search_results[optional_idx] if len(search_results) > optional_idx else []
            optional_idx += 1
            trusted_author_results = search_results[optional_idx] if len(search_results) > optional_idx else []
            optional_idx += 1

        if self.enable_web_scraping:
            web_results = search_results[optional_idx] if len(search_results) > optional_idx else []
            optional_idx += 1

        if self.enable_perplexity and self.perplexity.is_configured():
            perplexity_results = search_results[optional_idx] if len(search_results) > optional_idx else []
        
        # Process PubMed results
        if isinstance(pubmed_results, list):
            added = await self._process_pubmed_articles(pubmed_results)
            results['pubmed'] = {'found': len(pubmed_results), 'added': added}
            results['total_added'] += added
        else:
            self.logger.error(f"PubMed search failed: {pubmed_results}")
        
        # Process CrossRef results
        if isinstance(crossref_results, list):
            added = await self._process_crossref_works(crossref_results)
            results['crossref'] = {'found': len(crossref_results), 'added': added}
            results['total_added'] += added
        else:
            self.logger.error(f"CrossRef search failed: {crossref_results}")
        
        # Process RSS results
        if isinstance(rss_results, list):
            added = await self._process_rss_articles(rss_results)
            results['rss'] = {'found': len(rss_results), 'added': added}
            results['total_added'] += added
        else:
            self.logger.error(f"RSS search failed: {rss_results}")

        # Process trusted journal search results
        if isinstance(trusted_journal_results, list):
            added = await self._process_pubmed_articles(trusted_journal_results)
            results['trusted_journal_search'] = {'found': len(trusted_journal_results), 'added': added}
            results['total_added'] += added
            self.stats['trusted_sources_found'] += added
        elif self.enable_trusted_source_search:
            self.logger.error(f"Trusted journal search failed: {trusted_journal_results}")

        # Process trusted author search results
        if isinstance(trusted_author_results, list):
            added = await self._process_pubmed_articles(trusted_author_results)
            results['trusted_author_search'] = {'found': len(trusted_author_results), 'added': added}
            results['total_added'] += added
            self.stats['trusted_sources_found'] += added
        elif self.enable_trusted_source_search:
            self.logger.error(f"Trusted author search failed: {trusted_author_results}")

        # Process web scraped results
        if isinstance(web_results, list):
            added = await self._process_scraped_articles(web_results)
            results['web_scraped'] = {'found': len(web_results), 'added': added}
            results['total_added'] += added
            self.stats['web_scraped'] += added
        elif self.enable_web_scraping:
            self.logger.error(f"Web scraping failed: {web_results}")

        # Process Perplexity results
        if isinstance(perplexity_results, list):
            added = await self._process_perplexity_articles(perplexity_results)
            results['perplexity'] = {'found': len(perplexity_results), 'added': added}
            results['total_added'] += added
            self.stats['perplexity_found'] += added
        elif self.enable_perplexity and self.perplexity.is_configured():
            self.logger.error(f"Perplexity search failed: {perplexity_results}")

        self.stats['sources_found'] += sum([
            results['pubmed'].get('found', 0),
            results['crossref'].get('found', 0),
            results['rss'].get('found', 0),
            results['trusted_journal_search'].get('found', 0) if isinstance(results['trusted_journal_search'], dict) else 0,
            results['trusted_author_search'].get('found', 0) if isinstance(results['trusted_author_search'], dict) else 0,
            results['web_scraped'].get('found', 0) if isinstance(results['web_scraped'], dict) else 0,
            results['perplexity'].get('found', 0) if isinstance(results['perplexity'], dict) else 0
        ])
        self.stats['sources_added'] += results['total_added']
        
        self.logger.info(
            f"Research search complete. Added {results['total_added']} new sources to queue."
        )
        
        return results
    
    async def _search_pubmed(self) -> List[PubMedArticle]:
        """Search PubMed for recent articles."""
        try:
            self.logger.debug("Searching PubMed...")
            articles = await self.pubmed.search_recent(
                days_back=self.days_back,
                max_results=self.max_results_per_source
            )
            self.logger.debug(f"PubMed found {len(articles)} articles")
            return articles
        except Exception as e:
            self.logger.error(f"PubMed search error: {e}")
            raise
    
    async def _search_crossref(self) -> List[CrossRefWork]:
        """Search CrossRef for recent works."""
        try:
            self.logger.debug("Searching CrossRef...")
            works = await self.crossref.search_recent(
                days_back=self.days_back,
                max_results=self.max_results_per_source
            )
            self.logger.debug(f"CrossRef found {len(works)} works")
            return works
        except Exception as e:
            self.logger.error(f"CrossRef search error: {e}")
            raise
    
    async def _search_rss(self) -> List[RSSArticle]:
        """Search RSS feeds for recent articles."""
        try:
            self.logger.debug("Searching RSS feeds...")
            articles = await self.rss.fetch_all_feeds(
                days_back=self.days_back
            )
            self.logger.debug(f"RSS found {len(articles)} articles")
            return articles
        except Exception as e:
            self.logger.error(f"RSS search error: {e}")
            raise

    async def _search_web_sources(self) -> List[ScrapedArticle]:
        """Search web sources via scraping."""
        try:
            self.logger.debug("Scraping fitness websites...")
            articles = await self.fitness_scraper.scrape_all()
            self.logger.debug(f"Web scraper found {len(articles)} articles")
            return articles
        except Exception as e:
            self.logger.error(f"Web scraping error: {e}")
            raise

    async def _search_perplexity(self) -> List[PerplexityArticle]:
        """Search for research via Perplexity Sonar API."""
        try:
            self.logger.debug("Searching via Perplexity Sonar...")
            articles = await self.perplexity.search_research(
                max_results=self.max_results_per_source
            )
            self.logger.debug(f"Perplexity found {len(articles)} articles")
            return articles
        except Exception as e:
            self.logger.error(f"Perplexity search error: {e}")
            raise

    async def _search_trusted_journals(self) -> List[PubMedArticle]:
        """Search specifically in trusted journals."""
        try:
            self.logger.debug("Searching trusted journals...")

            # Get journal names for PubMed search
            journal_names = list(self._trusted_journals.keys())[:10]  # Limit to avoid query length issues
            if not journal_names:
                return []

            # Build PubMed journal filter
            journal_filter = ' OR '.join([f'"{j}"[journal]' for j in journal_names])
            query = f"({journal_filter}) AND (resistance training OR hypertrophy OR strength training OR protein synthesis)"

            articles = await self.pubmed.search_with_query(
                query=query,
                days_back=self.days_back * 2,  # Look back further for trusted sources
                max_results=self.max_results_per_source
            )

            self.logger.debug(f"Trusted journals search found {len(articles)} articles")
            return articles
        except Exception as e:
            self.logger.error(f"Trusted journals search error: {e}")
            return []

    async def _search_by_trusted_authors(self) -> List[PubMedArticle]:
        """Search for papers by trusted authors."""
        try:
            self.logger.debug("Searching by trusted authors...")

            # Get author names for PubMed search
            author_names = list(self._trusted_authors.keys())[:10]  # Limit to avoid query length issues
            if not author_names:
                return []

            # Build PubMed author filter
            author_filter = ' OR '.join([f'"{a}"[author]' for a in author_names])
            query = f"({author_filter})"

            articles = await self.pubmed.search_with_query(
                query=query,
                days_back=self.days_back * 2,  # Look back further for trusted authors
                max_results=self.max_results_per_source
            )

            self.logger.debug(f"Trusted authors search found {len(articles)} articles")
            return articles
        except Exception as e:
            self.logger.error(f"Trusted authors search error: {e}")
            return []
    
    async def _process_pubmed_articles(self, articles: List[PubMedArticle]) -> int:
        """Process PubMed articles and add to queue."""
        added_count = 0
        
        for article in articles:
            try:
                # Check if already in queue (by DOI or PMID)
                if await self._is_duplicate(doi=article.doi, pmid=article.pmid):
                    continue
                
                # Filter by criteria
                if not self._meets_criteria(article):
                    continue
                
                # Check if from trusted source
                is_trusted = self._is_trusted_source(article.authors, article.journal)

                # Create queue item
                queue_item = ResearchQueueItem(
                    id="",  # Will be generated by DB
                    title=article.title,
                    authors=article.authors,
                    abstract=article.abstract,
                    doi=article.doi,
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{article.pmid}/" if article.pmid else None,
                    publication_date=datetime_to_date(article.publication_date),
                    source_type='pubmed',
                    status='pending',
                    priority=self._calculate_priority(article),
                    raw_data={
                        'pmid': article.pmid,
                        'journal': article.journal,
                        'mesh_terms': article.mesh_terms,
                        'study_type': article.study_type,
                        'trusted_source': is_trusted,
                        'author_boost': self._get_author_boost(article.authors),
                        'journal_boost': self._get_journal_boost(article.journal)
                    }
                )
                
                # Add to queue
                await self.supabase.add_to_queue(queue_item)
                added_count += 1
                
            except Exception as e:
                self.logger.error(f"Error processing PubMed article {article.pmid}: {e}")
                continue
        
        return added_count
    
    async def _process_crossref_works(self, works: List[CrossRefWork]) -> int:
        """Process CrossRef works and add to queue."""
        added_count = 0
        
        for work in works:
            try:
                # Check if already in queue
                if await self._is_duplicate(doi=work.doi):
                    continue
                
                # Create queue item
                queue_item = ResearchQueueItem(
                    id="",
                    title=work.title,
                    authors=work.authors,
                    abstract=work.abstract,
                    doi=work.doi,
                    url=work.url,
                    publication_date=work.publication_date,
                    source_type='crossref',
                    status='pending',
                    priority=self._calculate_priority_crossref(work),
                    raw_data={
                        'journal': work.journal,
                        'subjects': work.subject,
                        'cited_by_count': work.is_referenced_by_count,
                        'type': work.type
                    }
                )
                
                await self.supabase.add_to_queue(queue_item)
                added_count += 1
                
            except Exception as e:
                self.logger.error(f"Error processing CrossRef work {work.doi}: {e}")
                continue
        
        return added_count
    
    async def _process_rss_articles(self, articles: List[RSSArticle]) -> int:
        """Process RSS articles and add to queue."""
        added_count = 0

        for article in articles:
            try:
                # Check if already in queue
                if await self._is_duplicate(doi=article.doi, url=article.link):
                    continue

                # Create queue item
                queue_item = ResearchQueueItem(
                    id="",
                    title=article.title,
                    authors=article.authors,
                    abstract=article.description,
                    doi=article.doi,
                    url=article.link,
                    publication_date=article.publication_date,
                    source_type='rss_feed',
                    status='pending',
                    priority=5,  # Default priority for RSS
                    raw_data={
                        'source': article.source,
                        'categories': article.categories
                    }
                )

                await self.supabase.add_to_queue(queue_item)
                added_count += 1

            except Exception as e:
                self.logger.error(f"Error processing RSS article: {e}")
                continue

        return added_count

    async def _process_scraped_articles(self, articles: List[ScrapedArticle]) -> int:
        """Process scraped articles and add to queue."""
        added_count = 0

        for article in articles:
            try:
                # Check if already in queue by URL
                if await self._is_duplicate(url=article.link):
                    continue

                # Create queue item
                queue_item = ResearchQueueItem(
                    id="",
                    title=article.title,
                    authors=article.authors,
                    abstract=article.description or article.content_preview,
                    doi=None,
                    url=article.link,
                    publication_date=article.publication_date,
                    source_type='web_scrape',
                    status='pending',
                    priority=6,  # Slightly lower priority than RSS for scraped content
                    raw_data={
                        'source': article.source,
                        'categories': article.categories,
                        'scraped': True
                    }
                )

                await self.supabase.add_to_queue(queue_item)
                added_count += 1

            except Exception as e:
                self.logger.error(f"Error processing scraped article: {e}")
                continue

        return added_count

    async def _process_perplexity_articles(self, articles: List[PerplexityArticle]) -> int:
        """Process Perplexity articles and add to queue."""
        added_count = 0

        for article in articles:
            try:
                # Check if already in queue by URL
                if await self._is_duplicate(url=article.url):
                    continue

                # Create queue item
                queue_item = ResearchQueueItem(
                    id="",
                    title=article.title,
                    authors=[],  # Perplexity doesn't provide authors
                    abstract=article.snippet,
                    doi=None,
                    url=article.url,
                    publication_date=None,  # Perplexity doesn't provide dates
                    source_type='perplexity',
                    status='pending',
                    priority=4,  # Higher priority for Perplexity results (curated)
                    raw_data={
                        'source': 'perplexity',
                        'citations': article.citations,
                        'search_query': article.search_query
                    }
                )

                await self.supabase.add_to_queue(queue_item)
                added_count += 1

            except Exception as e:
                self.logger.error(f"Error processing Perplexity article: {e}")
                continue

        return added_count
    
    async def _is_duplicate(
        self,
        doi: Optional[str] = None,
        pmid: Optional[str] = None,
        url: Optional[str] = None
    ) -> bool:
        """Check if article already exists in queue."""
        # This is a simplified check - in production, query the database
        # For now, we'll rely on unique constraints in the database
        return False
    
    def _meets_criteria(self, article: PubMedArticle) -> bool:
        """
        Check if article meets filtering criteria.
        
        Criteria:
        - Published in last 5 years
        - Has abstract
        - Is relevant study type (RCT, meta-analysis, etc.)
        """
        # Check publication date
        if article.publication_date:
            five_years_ago = datetime.now() - timedelta(days=365*5)
            if article.publication_date < five_years_ago:
                return False
        
        # Must have abstract
        if not article.abstract or len(article.abstract) < 100:
            return False
        
        # Prefer certain study types
        preferred_types = ['meta_analysis', 'systematic_review', 'rct', 'cohort']
        if article.study_type and article.study_type not in preferred_types:
            # Still accept but lower priority
            pass
        
        return True
    
    def _calculate_priority(self, article: PubMedArticle) -> int:
        """
        Calculate priority score (1-10, lower is higher priority).

        Priority factors:
        - Study design (meta-analysis > systematic review > RCT)
        - Trusted author boost
        - Trusted journal boost
        - Recency

        An article from a trusted author (boost 4) with a meta-analysis
        could get priority as low as 1 (5 - 3 - 4 + adjustments).
        """
        priority = 5  # Default

        # Higher priority for better study designs
        if article.study_type == 'meta_analysis':
            priority -= 3
        elif article.study_type == 'systematic_review':
            priority -= 2
        elif article.study_type == 'rct':
            priority -= 1

        # Author boost from trusted authors database
        author_boost = self._get_author_boost(article.authors)
        priority -= author_boost

        # Journal boost from trusted journals database
        journal_boost = self._get_journal_boost(article.journal)
        priority -= journal_boost

        # Higher priority for recent articles
        if article.publication_date:
            age_days = (datetime.now() - article.publication_date).days
            if age_days < 30:
                priority -= 1

        # Ensure within bounds (1 is highest priority, 10 is lowest)
        return max(1, min(10, priority))
    
    def _calculate_priority_crossref(self, work: CrossRefWork) -> int:
        """Calculate priority for CrossRef work."""
        priority = 5
        
        # Higher priority for highly cited works
        if work.is_referenced_by_count > 50:
            priority -= 2
        elif work.is_referenced_by_count > 10:
            priority -= 1
        
        # Recent articles get boost
        if work.publication_date:
            age_days = (datetime.now() - work.publication_date).days
            if age_days < 30:
                priority -= 1
        
        return max(1, min(10, priority))