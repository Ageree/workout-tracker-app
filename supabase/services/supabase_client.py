"""
Supabase Client wrapper for Agent Swarm.

Features:
- Unified date handling for PostgreSQL compatibility
- Retry logic for database operations
- Proper type conversions
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import date
import httpx
import logging

from utils.date_utils import format_date_for_db, parse_date_safe

logger = logging.getLogger(__name__)


@dataclass
class ResearchQueueItem:
    """Represents a research paper in the queue."""
    id: str
    title: str
    authors: List[str]
    abstract: Optional[str]
    doi: Optional[str]
    url: Optional[str]
    publication_date: Optional[date]
    source_type: str
    status: str
    priority: int
    raw_data: Dict[str, Any]


@dataclass
class ScientificClaim:
    """Represents a scientific claim."""
    id: Optional[str]
    claim: str
    claim_summary: Optional[str]
    category: str
    evidence_level: int
    confidence_score: float
    status: str
    source_doi: Optional[str]
    source_url: Optional[str]
    source_title: Optional[str]
    source_authors: List[str]
    publication_date: Optional[date]
    sample_size: Optional[int]
    study_design: Optional[str]
    population: Optional[str]
    effect_size: Optional[str]
    key_findings: List[str]
    limitations: Optional[str]
    conflicting_evidence: bool


@dataclass
class KnowledgeRelationship:
    """Represents a relationship between claims."""
    id: Optional[str]
    source_claim_id: str
    target_claim_id: str
    relationship_type: str  # 'contradicts', 'supports', 'related'
    confidence: float
    notes: Optional[str]


@dataclass
class PromptVersion:
    """Represents a versioned system prompt."""
    id: Optional[str]
    category: str
    prompt_text: str
    version: int
    knowledge_snapshot: Dict[str, Any]
    performance_score: Optional[float]
    is_active: bool
    created_at: Optional[date]
    metadata: Dict[str, Any]


class SupabaseClient:
    """Client for Supabase REST API with agent-specific operations."""
    
    def __init__(self, url: str, service_key: str):
        self.url = url.rstrip('/')
        self.service_key = service_key
        self.headers = {
            'apikey': service_key,
            'Authorization': f'Bearer {service_key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
    
    # ==================== Research Queue Operations ====================
    
    async def get_pending_queue_items(self, limit: int = 10) -> List[ResearchQueueItem]:
        """Fetch pending items from research queue."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.url}/rest/v1/research_queue",
                headers=self.headers,
                params={
                    'status': 'eq.pending',
                    'order': 'priority.desc,created_at.asc',
                    'limit': limit
                }
            )
            response.raise_for_status()
            data = response.json()
            
            return [
                ResearchQueueItem(
                    id=item['id'],
                    title=item['title'],
                    authors=item.get('authors', []),
                    abstract=item.get('abstract'),
                    doi=item.get('doi'),
                    url=item.get('url'),
                    publication_date=item.get('publication_date'),
                    source_type=item['source_type'],
                    status=item['status'],
                    priority=item.get('priority', 5),
                    raw_data=item.get('raw_data', {})
                )
                for item in data
            ]
    
    async def update_queue_status(
        self, 
        item_id: str, 
        status: str, 
        error_message: Optional[str] = None
    ) -> bool:
        """Update the status of a queue item."""
        async with httpx.AsyncClient() as client:
            payload = {'status': status}
            if error_message:
                payload['error_message'] = error_message
            if status in ['completed', 'rejected', 'failed']:
                payload['processed_at'] = 'now()'
            
            response = await client.patch(
                f"{self.url}/rest/v1/research_queue",
                headers=self.headers,
                params={'id': f'eq.{item_id}'},
                json=payload
            )
            return response.status_code in [200, 204]
    
    async def add_to_queue(self, item: ResearchQueueItem) -> Optional[str]:
        """Add a new item to the research queue."""
        async with httpx.AsyncClient() as client:
            # Use unified date formatting
            pub_date = format_date_for_db(item.publication_date)
            
            payload = {
                'title': item.title,
                'authors': item.authors,
                'abstract': item.abstract,
                'doi': item.doi,
                'url': item.url,
                'publication_date': pub_date,
                'source_type': item.source_type,
                'status': 'pending',
                'priority': item.priority,
                'raw_data': item.raw_data
            }
            
            response = await client.post(
                f"{self.url}/rest/v1/research_queue",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                return data[0]['id'] if data else None
            return None
    
    # ==================== Scientific Knowledge Operations ====================
    
    async def get_claims_by_category(self, category: str, limit: int = 100) -> List[ScientificClaim]:
        """Fetch claims by category."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.url}/rest/v1/scientific_knowledge",
                headers=self.headers,
                params={
                    'category': f'eq.{category}',
                    'status': 'eq.active',
                    'limit': limit
                }
            )
            response.raise_for_status()
            return [self._parse_claim(item) for item in response.json()]
    
    async def get_all_active_claims(self, limit: int = 1000) -> List[ScientificClaim]:
        """Fetch all active claims."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.url}/rest/v1/scientific_knowledge",
                headers=self.headers,
                params={
                    'status': 'eq.active',
                    'limit': limit
                }
            )
            response.raise_for_status()
            return [self._parse_claim(item) for item in response.json()]
    
    async def insert_claim(self, claim: ScientificClaim) -> Optional[str]:
        """Insert a new scientific claim."""
        async with httpx.AsyncClient() as client:
            # Use unified date formatting
            pub_date = format_date_for_db(claim.publication_date)
            
            payload = {
                'claim': claim.claim,
                'claim_summary': claim.claim_summary,
                'category': claim.category,
                'evidence_level': claim.evidence_level,
                'confidence_score': claim.confidence_score,
                'status': claim.status,
                'source_doi': claim.source_doi,
                'source_url': claim.source_url,
                'source_title': claim.source_title,
                'source_authors': claim.source_authors,
                'publication_date': pub_date,
                'sample_size': claim.sample_size,
                'study_design': claim.study_design,
                'population': claim.population,
                'effect_size': claim.effect_size,
                'key_findings': claim.key_findings,
                'limitations': claim.limitations,
                'conflicting_evidence': claim.conflicting_evidence
            }
            
            response = await client.post(
                f"{self.url}/rest/v1/scientific_knowledge",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                return data[0]['id'] if data else None
            return None
    
    async def update_claim(self, claim_id: str, updates: Dict[str, Any]) -> bool:
        """Update a claim."""
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.url}/rest/v1/scientific_knowledge",
                headers=self.headers,
                params={'id': f'eq.{claim_id}'},
                json=updates
            )
            return response.status_code in [200, 204]
    
    async def find_similar_claims(
        self,
        embedding: List[float],
        threshold: float = 0.7,
        limit: int = 5,
        category: Optional[str] = None,
        min_evidence_level: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Find claims with similar embeddings using pgvector.
        
        Args:
            embedding: Query embedding vector (1536 dimensions)
            threshold: Minimum similarity threshold (0-1)
            limit: Maximum number of results
            category: Optional category filter
            min_evidence_level: Minimum evidence level (1-5)
            
        Returns:
            List of similar claims with similarity scores
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/rest/v1/rpc/match_scientific_knowledge",
                headers=self.headers,
                json={
                    'query_embedding': embedding,
                    'match_threshold': threshold,
                    'match_count': limit,
                    'filter_category': category,
                    'min_evidence_level': min_evidence_level
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def find_similar_claims_detailed(
        self,
        embedding: List[float],
        threshold: float = 0.7,
        limit: int = 5,
        category: Optional[str] = None,
        min_evidence_level: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Find similar claims with detailed information.
        
        Args:
            embedding: Query embedding vector
            threshold: Minimum similarity threshold
            limit: Maximum number of results
            category: Optional category filter
            min_evidence_level: Minimum evidence level
            
        Returns:
            List of claims with detailed fields
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/rest/v1/rpc/match_scientific_knowledge_detailed",
                headers=self.headers,
                json={
                    'query_embedding': embedding,
                    'match_threshold': threshold,
                    'match_count': limit,
                    'filter_category': category,
                    'min_evidence_level': min_evidence_level
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def find_similar_to_claim(
        self,
        claim_id: str,
        threshold: float = 0.8,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find claims similar to a given claim by ID.
        
        Args:
            claim_id: ID of the reference claim
            threshold: Minimum similarity threshold
            limit: Maximum number of results
            
        Returns:
            List of similar claims
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/rest/v1/rpc/find_similar_claims",
                headers=self.headers,
                json={
                    'claim_id': claim_id,
                    'match_threshold': threshold,
                    'match_count': limit
                }
            )
            response.raise_for_status()
            return response.json()
    
    def _parse_claim(self, item: Dict[str, Any]) -> ScientificClaim:
        """Parse a claim from database response."""
        # Use unified date parsing for publication_date
        pub_date = parse_date_safe(item.get('publication_date'))
        
        return ScientificClaim(
            id=item.get('id'),
            claim=item['claim'],
            claim_summary=item.get('claim_summary'),
            category=item['category'],
            evidence_level=item['evidence_level'],
            confidence_score=item.get('confidence_score', 0.5),
            status=item['status'],
            source_doi=item.get('source_doi'),
            source_url=item.get('source_url'),
            source_title=item.get('source_title'),
            source_authors=item.get('source_authors', []),
            publication_date=pub_date,
            sample_size=item.get('sample_size'),
            study_design=item.get('study_design'),
            population=item.get('population'),
            effect_size=item.get('effect_size'),
            key_findings=item.get('key_findings', []),
            limitations=item.get('limitations'),
            conflicting_evidence=item.get('conflicting_evidence', False)
        )
    
    # ==================== Knowledge Relationships ====================
    
    async def create_relationship(self, relationship: KnowledgeRelationship) -> Optional[str]:
        """Create a relationship between claims."""
        async with httpx.AsyncClient() as client:
            payload = {
                'source_claim_id': relationship.source_claim_id,
                'target_claim_id': relationship.target_claim_id,
                'relationship_type': relationship.relationship_type,
                'confidence': relationship.confidence,
                'notes': relationship.notes
            }
            
            response = await client.post(
                f"{self.url}/rest/v1/knowledge_relationships",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                return data[0]['id'] if data else None
            return None
    
    async def get_relationships_for_claim(self, claim_id: str) -> List[KnowledgeRelationship]:
        """Get all relationships for a claim."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.url}/rest/v1/knowledge_relationships",
                headers=self.headers,
                params={
                    'or': f'(source_claim_id.eq.{claim_id},target_claim_id.eq.{claim_id})'
                }
            )
            response.raise_for_status()
            
            return [
                KnowledgeRelationship(
                    id=item['id'],
                    source_claim_id=item['source_claim_id'],
                    target_claim_id=item['target_claim_id'],
                    relationship_type=item['relationship_type'],
                    confidence=item['confidence'],
                    notes=item.get('notes')
                )
                for item in response.json()
            ]
    
    # ==================== Evidence Hierarchy ====================
    
    async def update_evidence_hierarchy(self, topic: str, category: str, score: float) -> bool:
        """Update or insert evidence hierarchy score."""
        async with httpx.AsyncClient() as client:
            # Try to update existing
            response = await client.patch(
                f"{self.url}/rest/v1/evidence_hierarchy",
                headers=self.headers,
                params={
                    'topic': f'eq.{topic}',
                    'category': f'eq.{category}'
                },
                json={
                    'total_score': score,
                    'updated_at': 'now()'
                }
            )
            
            if response.status_code == 204:
                return True
            
            # If no update, insert new
            response = await client.post(
                f"{self.url}/rest/v1/evidence_hierarchy",
                headers=self.headers,
                json={
                    'topic': topic,
                    'category': category,
                    'total_score': score
                }
            )
            return response.status_code in [200, 201]
    
    # ==================== Prompt Version Operations ====================
    
    async def get_claims_by_category_with_filters(
        self,
        category: str,
        min_evidence_level: int = 1,
        min_confidence: float = 0.0,
        limit: int = 50
    ) -> List[ScientificClaim]:
        """Fetch claims by category with filters."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.url}/rest/v1/scientific_knowledge",
                headers=self.headers,
                params={
                    'category': f'eq.{category}',
                    'evidence_level': f'gte.{min_evidence_level}',
                    'confidence_score': f'gte.{min_confidence}',
                    'status': 'eq.validated',
                    'limit': limit,
                    'order': 'evidence_level.desc,confidence_score.desc'
                }
            )
            response.raise_for_status()
            data = response.json()
            return [self._parse_claim(item) for item in data]
    
    async def get_active_prompt(self, category: str) -> Optional[PromptVersion]:
        """Get active prompt for category."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/rest/v1/rpc/get_active_system_prompt",
                headers=self.headers,
                json={'p_category': category}
            )
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return None
            
            return PromptVersion(
                id=data['id'],
                category=category,
                prompt_text=data['prompt_text'],
                version=data['version'],
                knowledge_snapshot=data['knowledge_snapshot'],
                performance_score=None,
                is_active=True,
                created_at=parse_date_safe(data['created_at']),
                metadata={}
            )
    
    async def get_latest_prompt_version(self, category: str) -> Optional[PromptVersion]:
        """Get latest prompt version for category."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/rest/v1/rpc/get_system_prompt_version",
                headers=self.headers,
                json={'p_category': category}
            )
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return None
            
            return PromptVersion(
                id=data['id'],
                category=category,
                prompt_text=data['prompt_text'],
                version=data['version'],
                knowledge_snapshot=data['knowledge_snapshot'],
                performance_score=None,
                is_active=data['is_active'],
                created_at=parse_date_safe(data['created_at']),
                metadata={}
            )
    
    async def save_prompt_version(self, prompt: PromptVersion) -> PromptVersion:
        """Save new prompt version."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/rest/v1/system_prompt_versions",
                headers=self.headers,
                json={
                    'category': prompt.category,
                    'prompt_text': prompt.prompt_text,
                    'version': prompt.version,
                    'knowledge_snapshot': prompt.knowledge_snapshot,
                    'performance_score': prompt.performance_score,
                    'is_active': prompt.is_active,
                    'metadata': prompt.metadata
                }
            )
            response.raise_for_status()
            data = response.json()[0]
            
            prompt.id = data['id']
            prompt.created_at = parse_date_safe(data['created_at'])
            return prompt
    
    async def activate_prompt_version(self, prompt_id: str):
        """Activate a prompt version."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/rest/v1/rpc/activate_prompt_version",
                headers=self.headers,
                json={'p_prompt_id': prompt_id}
            )
            response.raise_for_status()
    
    # ==================== AI Coach Functions ====================
    
    async def get_pending_embeddings(self, limit: int = 10) -> List[ScientificClaim]:
        """
        Fetch claims with pending embedding status using RPC function.
        This atomically locks the records for processing.
        
        Args:
            limit: Maximum number of claims to fetch
            
        Returns:
            List of claims with pending embedding status
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/rest/v1/rpc/get_pending_embeddings",
                headers=self.headers,
                json={'max_results': limit}
            )
            response.raise_for_status()
            data = response.json()
            
            return [
                ScientificClaim(
                    id=item['id'],
                    claim=item['claim'],
                    claim_summary=item.get('claim_summary'),
                    category=item['category'],
                    evidence_level=item['evidence_level'],
                    confidence_score=0.5,  # Default for pending claims
                    status='active',
                    source_doi=None,
                    source_url=None,
                    source_title=None,
                    source_authors=[],
                    publication_date=None,
                    sample_size=None,
                    study_design=None,
                    population=None,
                    effect_size=None,
                    key_findings=[],
                    limitations=None,
                    conflicting_evidence=False
                )
                for item in data
            ]
    
    async def update_embedding_status(
        self,
        claim_id: str,
        embedding: Optional[List[float]] = None,
        status: str = 'completed',
        error: Optional[str] = None
    ) -> bool:
        """
        Update embedding and status for a claim using RPC function.
        
        Args:
            claim_id: Claim ID
            embedding: Embedding vector (None if failed)
            status: New status ('completed' or 'failed')
            error: Error message if failed
            
        Returns:
            True if successful
        """
        async with httpx.AsyncClient() as client:
            payload = {
                'p_claim_id': claim_id,
                'p_status': status
            }
            
            if embedding is not None:
                payload['p_embedding'] = embedding
            
            response = await client.post(
                f"{self.url}/rest/v1/rpc/update_embedding_status",
                headers=self.headers,
                json=payload
            )
            return response.status_code in [200, 204]
    
    async def get_knowledge_context(
        self,
        query_text: str,
        max_results: int = 5,
        min_evidence_level: int = 2
    ) -> Dict[str, Any]:
        """
        Get knowledge context for AI prompt using RPC function.
        
        Args:
            query_text: User query text
            max_results: Maximum number of knowledge items
            min_evidence_level: Minimum evidence level
            
        Returns:
            Dictionary with context_text, knowledge_ids, avg_evidence_level
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/rest/v1/rpc/get_knowledge_context",
                headers=self.headers,
                json={
                    'query_text': query_text,
                    'max_results': max_results,
                    'min_evidence_level': min_evidence_level
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def save_message_knowledge(
        self,
        message_id: str,
        knowledge_ids: List[str],
        evidence_level: float
    ) -> bool:
        """
        Save knowledge usage for a message using RPC function.
        
        Args:
            message_id: Chat message ID
            knowledge_ids: List of knowledge IDs used
            evidence_level: Average evidence level
            
        Returns:
            True if successful
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/rest/v1/rpc/save_message_knowledge",
                headers=self.headers,
                json={
                    'p_message_id': message_id,
                    'p_knowledge_ids': knowledge_ids,
                    'p_evidence_level': evidence_level
                }
            )
            return response.status_code in [200, 204]
    
    async def get_relevant_knowledge_for_query(
        self,
        query_text: str,
        max_results: int = 5,
        min_evidence_level: int = 2,
        filter_categories: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get relevant knowledge for UI display using RPC function.
        
        Args:
            query_text: User query text
            max_results: Maximum number of results
            min_evidence_level: Minimum evidence level
            filter_categories: Optional list of categories to filter
            
        Returns:
            List of knowledge records with relevance scores
        """
        async with httpx.AsyncClient() as client:
            payload = {
                'query_text': query_text,
                'max_results': max_results,
                'min_evidence_level': min_evidence_level
            }
            
            if filter_categories is not None:
                payload['filter_categories'] = filter_categories
            
            response = await client.post(
                f"{self.url}/rest/v1/rpc/get_relevant_knowledge_for_query",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()

    # ==================== Trusted Sources Operations ====================

    async def get_trusted_authors(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get list of trusted authors from database.

        Args:
            active_only: Only return active authors

        Returns:
            List of trusted author records
        """
        async with httpx.AsyncClient() as client:
            params = {}
            if active_only:
                params['is_active'] = 'eq.true'

            response = await client.get(
                f"{self.url}/rest/v1/trusted_authors",
                headers=self.headers,
                params=params
            )
            if response.status_code == 200:
                return response.json()
            return []

    async def get_trusted_journals(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get list of trusted journals from database.

        Args:
            active_only: Only return active journals

        Returns:
            List of trusted journal records
        """
        async with httpx.AsyncClient() as client:
            params = {}
            if active_only:
                params['is_active'] = 'eq.true'

            response = await client.get(
                f"{self.url}/rest/v1/trusted_journals",
                headers=self.headers,
                params=params
            )
            if response.status_code == 200:
                return response.json()
            return []

    async def check_trusted_author(self, author_name: str) -> Dict[str, Any]:
        """
        Check if an author is in the trusted authors list.

        Args:
            author_name: Author name to check

        Returns:
            Dictionary with is_trusted, priority_boost, author_id
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/rest/v1/rpc/is_trusted_author",
                headers=self.headers,
                json={'author_name': author_name}
            )
            if response.status_code == 200:
                data = response.json()
                if data:
                    return data[0] if isinstance(data, list) else data
            return {'is_trusted': False, 'priority_boost': 0, 'author_id': None}

    async def check_trusted_journal(self, journal_name: str) -> Dict[str, Any]:
        """
        Check if a journal is in the trusted journals list.

        Args:
            journal_name: Journal name to check

        Returns:
            Dictionary with is_trusted, priority_boost, journal_id
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.url}/rest/v1/rpc/is_trusted_journal",
                headers=self.headers,
                json={'journal_name': journal_name}
            )
            if response.status_code == 200:
                data = response.json()
                if data:
                    return data[0] if isinstance(data, list) else data
            return {'is_trusted': False, 'priority_boost': 0, 'journal_id': None}

    async def get_trusted_knowledge(
        self,
        limit: int = 100,
        category: Optional[str] = None
    ) -> List[ScientificClaim]:
        """
        Get knowledge entries marked as trusted sources.

        Args:
            limit: Maximum number of results
            category: Optional category filter

        Returns:
            List of trusted ScientificClaim objects
        """
        async with httpx.AsyncClient() as client:
            params = {
                'trusted_source': 'eq.true',
                'status': 'eq.active',
                'limit': limit,
                'order': 'evidence_level.desc'
            }
            if category:
                params['category'] = f'eq.{category}'

            response = await client.get(
                f"{self.url}/rest/v1/scientific_knowledge",
                headers=self.headers,
                params=params
            )
            if response.status_code == 200:
                return [self._parse_claim(item) for item in response.json()]
            return []