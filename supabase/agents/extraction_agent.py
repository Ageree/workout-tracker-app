"""
Extraction Agent (📖) - Извлечение scientific claims из исследований
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from agents.base_agent import BaseAgent
from services.supabase_client import SupabaseClient, ResearchQueueItem, ScientificClaim
from services.llm_service import LLMService, ExtractedClaim


@dataclass
class ExtractionResult:
    """Result of claim extraction."""
    queue_item_id: str
    claims: List[ExtractedClaim]
    success: bool
    error_message: Optional[str] = None


class ExtractionAgent(BaseAgent):
    """
    Extraction Agent responsible for:
    - Fetching pending papers from research queue
    - Extracting scientific claims using LLM
    - Updating queue status
    - Passing claims to validation
    """
    
    def __init__(
        self,
        supabase: SupabaseClient,
        llm_service: Optional[LLMService] = None,
        batch_size: int = 5
    ):
        super().__init__(name="ExtractionAgent", supabase=supabase)
        self.llm = llm_service
        self.batch_size = batch_size
        self.stats['papers_processed'] = 0
        self.stats['claims_extracted'] = 0
    
    async def process(self) -> Dict[str, Any]:
        """
        Main processing: extract claims from pending papers.
        
        Returns:
            Dictionary with extraction results
        """
        self.logger.info("Starting claim extraction...")
        
        # Fetch pending items
        pending_items = await self.supabase.get_pending_queue_items(
            limit=self.batch_size
        )
        
        if not pending_items:
            self.logger.info("No pending items in queue")
            return {'processed': 0, 'claims_found': 0, 'errors': 0}
        
        self.logger.info(f"Found {len(pending_items)} pending items")
        
        results = {
            'processed': 0,
            'claims_found': 0,
            'errors': 0,
            'details': []
        }
        
        for item in pending_items:
            try:
                # Update status to processing
                await self.supabase.update_queue_status(item.id, 'processing')
                
                # Extract claims
                extraction_result = await self._extract_from_item(item)
                
                if extraction_result.success:
                    # Store claims for validation (in memory or temp storage)
                    await self._store_extracted_claims(item, extraction_result.claims)
                    
                    # Update status to completed (claims ready for validation)
                    await self.supabase.update_queue_status(item.id, 'completed')
                    
                    results['processed'] += 1
                    results['claims_found'] += len(extraction_result.claims)
                    results['details'].append({
                        'item_id': item.id,
                        'title': item.title[:50] + '...',
                        'claims': len(extraction_result.claims)
                    })
                    
                    self.stats['papers_processed'] += 1
                    self.stats['claims_extracted'] += len(extraction_result.claims)
                else:
                    # Mark as failed
                    await self.supabase.update_queue_status(
                        item.id,
                        'failed',
                        extraction_result.error_message
                    )
                    results['errors'] += 1
                
            except Exception as e:
                self.logger.error(f"Error processing item {item.id}: {e}")
                await self.supabase.update_queue_status(item.id, 'failed', str(e))
                results['errors'] += 1
        
        self.logger.info(
            f"Extraction complete. Processed {results['processed']} papers, "
            f"found {results['claims_found']} claims, {results['errors']} errors"
        )
        
        return results
    
    async def _extract_from_item(self, item: ResearchQueueItem) -> ExtractionResult:
        """
        Extract claims from a research queue item.
        
        Args:
            item: Research queue item
        
        Returns:
            ExtractionResult with claims or error
        """
        # Check if LLM service is available
        if not self.llm:
            return ExtractionResult(
                queue_item_id=item.id,
                claims=[],
                success=False,
                error_message="LLM service not configured"
            )
        
        # Check if we have abstract
        if not item.abstract:
            return ExtractionResult(
                queue_item_id=item.id,
                claims=[],
                success=True,  # Not an error, just no data
                error_message="No abstract available"
            )
        
        try:
            # Extract claims using LLM
            claims = await self.llm.extract_claims(
                title=item.title,
                authors=item.authors,
                abstract=item.abstract
            )
            
            return ExtractionResult(
                queue_item_id=item.id,
                claims=claims,
                success=True
            )
            
        except Exception as e:
            self.logger.error(f"Extraction failed for {item.id}: {e}")
            return ExtractionResult(
                queue_item_id=item.id,
                claims=[],
                success=False,
                error_message=str(e)
            )
    
    async def _store_extracted_claims(
        self,
        item: ResearchQueueItem,
        claims: List[ExtractedClaim]
    ) -> None:
        """
        Store extracted claims temporarily or pass to validation.
        
        For now, we'll store them in a temporary table or queue.
        In production, this could be a message queue or temp storage.
        """
        # For this implementation, we'll store claims with a special status
        # indicating they need validation
        
        for claim in claims:
            try:
                # Create a draft claim in the database
                # These will be picked up by the Validation Agent
                scientific_claim = ScientificClaim(
                    id=None,
                    claim=claim.claim,
                    claim_summary=claim.claim_summary,
                    category=claim.category,
                    evidence_level=claim.evidence_level,
                    confidence_score=claim.confidence * 0.8,  # Initial confidence
                    status='draft',  # Draft status - needs validation
                    source_doi=item.doi,
                    source_url=item.url,
                    source_title=item.title,
                    source_authors=item.authors,
                    publication_date=item.publication_date,
                    sample_size=claim.sample_size,
                    study_design=claim.study_design,
                    population=claim.population,
                    effect_size=claim.effect_size,
                    key_findings=claim.key_findings,
                    limitations=claim.limitations,
                    conflicting_evidence=False
                )
                
                # Insert into database
                await self.supabase.insert_claim(scientific_claim)
                
            except Exception as e:
                self.logger.error(f"Error storing claim: {e}")
                continue
    
    async def get_extraction_stats(self) -> Dict[str, Any]:
        """Get statistics about extraction process."""
        return {
            'papers_processed': self.stats.get('papers_processed', 0),
            'claims_extracted': self.stats.get('claims_extracted', 0),
            'average_claims_per_paper': (
                self.stats.get('claims_extracted', 0) / 
                max(1, self.stats.get('papers_processed', 1))
            )
        }