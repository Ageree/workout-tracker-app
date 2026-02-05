"""
Knowledge Base Agent (📚) - Интеграция валидированных claims в БД
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from agents.base_agent import BaseAgent
from services.supabase_client import SupabaseClient, ScientificClaim


class KnowledgeBaseAgent(BaseAgent):
    """
    Knowledge Base Agent responsible for:
    - Processing approved claims
    - Generating embeddings for claims
    - Updating evidence hierarchy
    - Triggering downstream processes
    """
    
    def __init__(
        self,
        supabase: SupabaseClient,
        llm_service: Optional[Any] = None,
        batch_size: int = 10
    ):
        super().__init__(name="KnowledgeBaseAgent", supabase=supabase)
        self.llm = llm_service
        self.batch_size = batch_size
        self.stats['claims_processed'] = 0
        self.stats['embeddings_generated'] = 0
        self.stats['hierarchy_updated'] = 0
    
    async def process(self) -> Dict[str, Any]:
        """
        Main processing: finalize approved claims in knowledge base.
        
        Returns:
            Dictionary with processing results
        """
        self.logger.info("Starting knowledge base integration...")
        
        # Fetch active claims without embeddings
        claims = await self._get_claims_needing_processing(limit=self.batch_size)
        
        if not claims:
            self.logger.info("No claims need processing")
            return {'processed': 0, 'embeddings': 0, 'hierarchy_updates': 0}
        
        self.logger.info(f"Found {len(claims)} claims to process")
        
        results = {
            'processed': 0,
            'embeddings': 0,
            'hierarchy_updates': 0,
            'errors': 0
        }
        
        for claim in claims:
            try:
                # Generate embedding
                embedding_generated = await self._generate_embedding(claim)
                if embedding_generated:
                    results['embeddings'] += 1
                    self.stats['embeddings_generated'] += 1
                
                # Update evidence hierarchy
                hierarchy_updated = await self._update_evidence_hierarchy(claim)
                if hierarchy_updated:
                    results['hierarchy_updates'] += 1
                    self.stats['hierarchy_updated'] += 1
                
                results['processed'] += 1
                self.stats['claims_processed'] += 1
                
            except Exception as e:
                self.logger.error(f"Error processing claim {claim.id}: {e}")
                results['errors'] += 1
        
        self.logger.info(
            f"KB integration complete. Processed {results['processed']} claims, "
            f"generated {results['embeddings']} embeddings, "
            f"updated {results['hierarchy_updates']} hierarchy entries"
        )
        
        return results
    
    async def _get_claims_needing_processing(self, limit: int = 10) -> List[ScientificClaim]:
        """
        Fetch active claims with pending embedding status.
        Uses the get_pending_embeddings RPC function for atomic fetching.
        
        Args:
            limit: Maximum number of claims to fetch
            
        Returns:
            List of claims with pending embedding status
        """
        return await self.supabase.get_pending_embeddings(limit=limit)
    
    async def _generate_embedding(self, claim: ScientificClaim) -> bool:
        """
        Generate and store embedding for a claim.
        
        Args:
            claim: Claim to generate embedding for
        
        Returns:
            True if successful
        """
        if not self.llm:
            self.logger.warning("LLM service not available for embedding generation")
            await self._mark_embedding_failed(claim.id, "LLM service not available")
            return False
        
        if not claim.id:
            return False
        
        try:
            # Generate embedding
            embedding = await self.llm.generate_embedding(claim.claim)
            
            if not embedding:
                await self._mark_embedding_failed(claim.id, "Empty embedding generated")
                return False
            
            # Store embedding in database using RPC function
            success = await self._store_embedding(claim.id, embedding)
            
            if not success:
                await self._mark_embedding_failed(claim.id, "Failed to store embedding")
                return False
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error generating embedding for {claim.id}: {e}")
            await self._mark_embedding_failed(claim.id, str(e))
            return False
    
    async def _mark_embedding_failed(self, claim_id: str, error: str) -> bool:
        """
        Mark embedding generation as failed.
        
        Args:
            claim_id: Claim ID
            error: Error message
            
        Returns:
            True if successful
        """
        try:
            return await self.supabase.update_embedding_status(
                claim_id=claim_id,
                embedding=None,
                status='failed',
                error=error
            )
        except Exception as e:
            self.logger.error(f"Error marking embedding failed for {claim_id}: {e}")
            return False
    
    async def _store_embedding(self, claim_id: str, embedding: List[float]) -> bool:
        """
        Store embedding in the database using RPC function.
        
        Args:
            claim_id: Claim ID
            embedding: Embedding vector
        
        Returns:
            True if successful
        """
        try:
            # Use the new RPC function for atomic update
            return await self.supabase.update_embedding_status(
                claim_id=claim_id,
                embedding=embedding,
                status='completed'
            )
            
        except Exception as e:
            self.logger.error(f"Error storing embedding: {e}")
            return False
    
    async def _update_evidence_hierarchy(self, claim: ScientificClaim) -> bool:
        """
        Update evidence hierarchy for the claim's category.
        
        Args:
            claim: Claim to process
        
        Returns:
            True if successful
        """
        if not claim.id:
            return False
        
        try:
            # Calculate score contribution
            score = self._calculate_hierarchy_score(claim)
            
            # Update or create hierarchy entry
            # Use claim category as topic for simplicity
            # In production, you might extract more specific topics
            success = await self.supabase.update_evidence_hierarchy(
                topic=claim.category,
                category=claim.category,
                score=score
            )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error updating hierarchy: {e}")
            return False
    
    def _calculate_hierarchy_score(self, claim: ScientificClaim) -> float:
        """
        Calculate evidence hierarchy score for a claim.
        
        This score represents the accumulated evidence strength
        for a given topic/category.
        
        Args:
            claim: Claim to calculate score for
        
        Returns:
            Score value
        """
        # Base score from evidence level
        base_score = claim.evidence_level * 0.2  # 0.2 to 1.0
        
        # Adjust by confidence
        score = base_score * claim.confidence_score
        
        # Boost for larger sample sizes
        if claim.sample_size:
            if claim.sample_size >= 1000:
                score *= 1.2
            elif claim.sample_size >= 100:
                score *= 1.1
        
        # Penalty for conflicting evidence
        if claim.conflicting_evidence:
            score *= 0.8
        
        return min(1.0, score)
    
    async def get_kb_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        return {
            'claims_processed': self.stats.get('claims_processed', 0),
            'embeddings_generated': self.stats.get('embeddings_generated', 0),
            'hierarchy_updated': self.stats.get('hierarchy_updated', 0)
        }
    
    async def rebuild_embeddings(self) -> Dict[str, Any]:
        """
        Rebuild embeddings for all active claims.
        
        Returns:
            Results dictionary
        """
        self.logger.info("Starting embedding rebuild...")
        
        claims = await self.supabase.get_all_active_claims(limit=1000)
        
        results = {'total': len(claims), 'success': 0, 'failed': 0}
        
        for claim in claims:
            try:
                success = await self._generate_embedding(claim)
                if success:
                    results['success'] += 1
                else:
                    results['failed'] += 1
            except Exception as e:
                self.logger.error(f"Error rebuilding embedding for {claim.id}: {e}")
                results['failed'] += 1
        
        self.logger.info(
            f"Embedding rebuild complete. Success: {results['success']}, "
            f"Failed: {results['failed']}"
        )
        
        return results