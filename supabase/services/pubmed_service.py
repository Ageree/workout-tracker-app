"""
PubMed E-utilities API Service for Research Agent.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import httpx
import xml.etree.ElementTree as ET


@dataclass
class PubMedArticle:
    """Represents a PubMed article."""
    pmid: str
    title: str
    abstract: Optional[str]
    authors: List[str]
    publication_date: Optional[datetime]
    journal: Optional[str]
    doi: Optional[str]
    mesh_terms: List[str]
    study_type: Optional[str]


class PubMedService:
    """Service for interacting with PubMed E-utilities API."""
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    # Search terms for fitness-related research
    DEFAULT_SEARCH_TERMS = [
        "resistance training",
        "strength training",
        "muscle hypertrophy",
        "protein synthesis",
        "muscle recovery",
        "exercise nutrition",
        "periodization",
        "training volume",
        "training intensity",
        "muscle damage",
        "DOMS",
        "creatine supplementation",
        "protein supplementation",
        "BCAA",
        "sleep recovery",
        "overtraining"
    ]
    
    def __init__(self, api_key: Optional[str] = None, rate_limit_delay: float = 0.34):
        """
        Initialize PubMed service.
        
        Args:
            api_key: NCBI API key (optional, increases rate limits)
            rate_limit_delay: Delay between requests in seconds (default 0.34 = 3 req/sec without key)
        """
        self.api_key = api_key
        self.rate_limit_delay = rate_limit_delay if api_key else 0.34
        self.last_request_time: Optional[datetime] = None
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Make a rate-limited request to PubMed API."""
        # Rate limiting
        if self.last_request_time:
            elapsed = (datetime.now() - self.last_request_time).total_seconds()
            if elapsed < self.rate_limit_delay:
                import asyncio
                await asyncio.sleep(self.rate_limit_delay - elapsed)
        
        if self.api_key:
            params['api_key'] = self.api_key
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=30.0)
            self.last_request_time = datetime.now()
            response.raise_for_status()
            return response.text
    
    async def search(
        self,
        query: str,
        max_results: int = 20,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        study_types: Optional[List[str]] = None
    ) -> List[str]:
        """
        Search PubMed and return list of PMIDs.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            date_from: Start date (YYYY/MM/DD)
            date_to: End date (YYYY/MM/DD)
            study_types: Filter by study types (e.g., ['Randomized Controlled Trial'])
        
        Returns:
            List of PMIDs
        """
        # Build query
        full_query = query
        
        if study_types:
            study_filter = " OR ".join([f'"{st}"[pt]' for st in study_types])
            full_query = f"({query}) AND ({study_filter})"
        
        if date_from or date_to:
            date_range = f"{date_from or '1900/01/01'}:{date_to or '3000/12/31'}[pdat]"
            full_query = f"({full_query}) AND {date_range}"
        
        params = {
            'db': 'pubmed',
            'term': full_query,
            'retmax': max_results,
            'retmode': 'json',
            'sort': 'date'
        }
        
        response_text = await self._make_request('esearch.fcgi', params)
        data = httpx.Response(200, text=response_text).json()
        
        return data.get('esearchresult', {}).get('idlist', [])
    
    async def fetch_articles(self, pmids: List[str]) -> List[PubMedArticle]:
        """
        Fetch full article details for given PMIDs.
        
        Args:
            pmids: List of PubMed IDs
        
        Returns:
            List of PubMedArticle objects
        """
        if not pmids:
            return []
        
        params = {
            'db': 'pubmed',
            'id': ','.join(pmids),
            'retmode': 'xml'
        }
        
        xml_text = await self._make_request('efetch.fcgi', params)
        return self._parse_pubmed_xml(xml_text)
    
    def _parse_pubmed_xml(self, xml_text: str) -> List[PubMedArticle]:
        """Parse PubMed XML response into article objects."""
        articles = []
        
        try:
            root = ET.fromstring(xml_text)
            
            for article_elem in root.findall('.//PubmedArticle'):
                try:
                    article = self._parse_article_element(article_elem)
                    if article:
                        articles.append(article)
                except Exception as e:
                    print(f"Error parsing article: {e}")
                    continue
        except ET.ParseError as e:
            print(f"XML parse error: {e}")
        
        return articles
    
    def _parse_article_element(self, elem: ET.Element) -> Optional[PubMedArticle]:
        """Parse a single PubmedArticle element."""
        # Get PMID
        pmid_elem = elem.find('.//PMID')
        if pmid_elem is None:
            return None
        pmid = pmid_elem.text or ""
        
        # Get title
        title_elem = elem.find('.//ArticleTitle')
        title = title_elem.text if title_elem is not None else ""
        
        # Get abstract
        abstract_elem = elem.find('.//Abstract/AbstractText')
        abstract = abstract_elem.text if abstract_elem is not None else None
        
        # Get authors
        authors = []
        for author_elem in elem.findall('.//Author'):
            last_name = author_elem.find('LastName')
            fore_name = author_elem.find('ForeName')
            if last_name is not None:
                name = last_name.text or ""
                if fore_name is not None:
                    name = f"{fore_name.text} {name}"
                authors.append(name)
        
        # Get publication date
        pub_date = None
        date_elem = elem.find('.//PubDate')
        if date_elem is not None:
            year = date_elem.find('Year')
            month = date_elem.find('Month')
            day = date_elem.find('Day')
            
            try:
                y = int(year.text) if year is not None else 2000
                m = self._parse_month(month.text) if month is not None else 1
                d = int(day.text) if day is not None else 1
                pub_date = datetime(y, m, d)
            except (ValueError, TypeError):
                pass
        
        # Get journal
        journal_elem = elem.find('.//Journal/Title')
        journal = journal_elem.text if journal_elem is not None else None
        
        # Get DOI
        doi = None
        for id_elem in elem.findall('.//ArticleId'):
            if id_elem.get('IdType') == 'doi':
                doi = id_elem.text
                break
        
        # Get MeSH terms
        mesh_terms = []
        for mesh_elem in elem.findall('.//MeshHeading/DescriptorName'):
            if mesh_elem.text:
                mesh_terms.append(mesh_elem.text)
        
        # Determine study type
        study_type = self._determine_study_type(elem, mesh_terms)
        
        return PubMedArticle(
            pmid=pmid,
            title=title,
            abstract=abstract,
            authors=authors,
            publication_date=pub_date,
            journal=journal,
            doi=doi,
            mesh_terms=mesh_terms,
            study_type=study_type
        )
    
    def _parse_month(self, month_str: str) -> int:
        """Parse month string to number."""
        months = {
            'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
            'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12,
            'January': 1, 'February': 2, 'March': 3, 'April': 4,
            'June': 6, 'July': 7, 'August': 8, 'September': 9,
            'October': 10, 'November': 11, 'December': 12
        }
        return months.get(month_str, 1)
    
    def _determine_study_type(self, elem: ET.Element, mesh_terms: List[str]) -> Optional[str]:
        """Determine study type from publication type and MeSH terms."""
        # Check publication types
        pub_types = []
        for pt_elem in elem.findall('.//PublicationType'):
            if pt_elem.text:
                pub_types.append(pt_elem.text.lower())
        
        # Map to our categories
        if any('meta-analysis' in pt for pt in pub_types):
            return 'meta_analysis'
        elif any('systematic review' in pt for pt in pub_types):
            return 'systematic_review'
        elif any('randomized controlled trial' in pt for pt in pub_types):
            return 'rct'
        elif any('controlled clinical trial' in pt for pt in pub_types):
            return 'rct'
        elif any('cohort' in pt for pt in pub_types):
            return 'cohort'
        elif any('case-control' in pt for pt in pub_types):
            return 'case_control'
        elif any('cross-sectional' in pt for pt in pub_types):
            return 'cross_sectional'
        
        # Check MeSH terms
        mesh_lower = [m.lower() for m in mesh_terms]
        if any('meta-analysis' in m for m in mesh_lower):
            return 'meta_analysis'
        elif any('randomized controlled trial' in m for m in mesh_lower):
            return 'rct'
        
        return None
    
    async def search_recent(
        self,
        days_back: int = 30,
        max_results: int = 50
    ) -> List[PubMedArticle]:
        """
        Search for recent articles on fitness topics.

        Args:
            days_back: Number of days to look back
            max_results: Maximum results per topic

        Returns:
            List of PubMedArticle objects
        """
        date_to = datetime.now().strftime('%Y/%m/%d')
        date_from = (datetime.now() - timedelta(days=days_back)).strftime('%Y/%m/%d')

        all_articles = []
        seen_pmids = set()

        study_types = [
            'Randomized Controlled Trial',
            'Meta-Analysis',
            'Systematic Review',
            'Clinical Trial',
            'Controlled Clinical Trial'
        ]

        for term in self.DEFAULT_SEARCH_TERMS:
            try:
                pmids = await self.search(
                    query=term,
                    max_results=max_results,
                    date_from=date_from,
                    date_to=date_to,
                    study_types=study_types
                )

                # Filter out duplicates
                new_pmids = [p for p in pmids if p not in seen_pmids]
                seen_pmids.update(new_pmids)

                if new_pmids:
                    articles = await self.fetch_articles(new_pmids)
                    all_articles.extend(articles)

            except Exception as e:
                print(f"Error searching for term '{term}': {e}")
                continue

        return all_articles

    async def search_with_query(
        self,
        query: str,
        days_back: int = 30,
        max_results: int = 50,
        study_types: Optional[List[str]] = None
    ) -> List[PubMedArticle]:
        """
        Search PubMed with a custom query string.

        This is useful for journal-specific or author-specific searches.

        Args:
            query: Custom PubMed query string
            days_back: Number of days to look back
            max_results: Maximum number of results

        Returns:
            List of PubMedArticle objects
        """
        date_to = datetime.now().strftime('%Y/%m/%d')
        date_from = (datetime.now() - timedelta(days=days_back)).strftime('%Y/%m/%d')

        if study_types is None:
            study_types = [
                'Randomized Controlled Trial',
                'Meta-Analysis',
                'Systematic Review',
                'Clinical Trial'
            ]

        try:
            pmids = await self.search(
                query=query,
                max_results=max_results,
                date_from=date_from,
                date_to=date_to,
                study_types=study_types
            )

            if pmids:
                return await self.fetch_articles(pmids)
            return []

        except Exception as e:
            print(f"Error in custom query search: {e}")
            return []

    async def search_by_journal(
        self,
        journal_name: str,
        days_back: int = 90,
        max_results: int = 20,
        topic_filter: Optional[str] = None
    ) -> List[PubMedArticle]:
        """
        Search for articles from a specific journal.

        Args:
            journal_name: Name of the journal
            days_back: Number of days to look back
            max_results: Maximum number of results
            topic_filter: Optional topic to filter by

        Returns:
            List of PubMedArticle objects
        """
        query = f'"{journal_name}"[journal]'
        if topic_filter:
            query = f"({query}) AND ({topic_filter})"

        return await self.search_with_query(
            query=query,
            days_back=days_back,
            max_results=max_results
        )

    async def search_by_author(
        self,
        author_name: str,
        days_back: int = 365,
        max_results: int = 20
    ) -> List[PubMedArticle]:
        """
        Search for articles by a specific author.

        Args:
            author_name: Author name (e.g., "Schoenfeld BJ" or "Brad Schoenfeld")
            days_back: Number of days to look back (default 1 year for authors)
            max_results: Maximum number of results

        Returns:
            List of PubMedArticle objects
        """
        query = f'"{author_name}"[author]'

        return await self.search_with_query(
            query=query,
            days_back=days_back,
            max_results=max_results
        )