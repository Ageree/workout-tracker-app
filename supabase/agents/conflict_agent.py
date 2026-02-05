"""
Conflict Agent (🔄) - Выявление и разрешение конфликтующих claims
"""

from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass
from collections import defaultdict

from agents.base_agent import BaseAgent
from services.supabase_client import SupabaseClient, ScientificClaim, KnowledgeRelationship
from services.llm_service import LLMService


@dataclass
class ConflictDetectionResult:
    """Result of conflict detection."""
    claim_id: str
    conflicts_found: List[Dict[str, Any]]
    resolution_suggested: Optional[str]


class ConflictAgent(BaseAgent):
    """
    Conflict Agent responsible for:
    - Detecting conflicts between claims
    - Analyzing conflicting evidence
    - Creating knowledge relationships
    - Flagging claims with conflicts
    """
    
    def __init__(
        self,
        supabase: SupabaseClient,
        llm_service: Optional[LLMService] = None,
        batch_size: int = 10,
        similarity_threshold: float = 0.75
    ):
        super().__init__(name="ConflictAgent", supabase=supabase)
        self.llm = llm_service
        self.batch_size = batch_size
        self.similarity_threshold = similarity_threshold
        self.stats['conflicts_detected'] = 0
        self.stats['relationships_created'] = 0
        self.stats['claims_flagged'] = 0
    
    async def process(self) -> Dict[str, Any]:
        """
        Main processing: detect conflicts in recent claims.
        
        Returns:
            Dictionary with conflict detection results
        """
        self.logger.info("Starting conflict detection...")
        
        # Fetch recently added claims that haven't been checked
        claims = await self._get_claims_to_check(limit=self.batch_size)
        
        if not claims:
            self.logger.info("No claims to check for conflicts")
            return {'checked': 0, 'conflicts_found': 0, 'relationships_created': 0}
        
        self.logger.info(f"Checking {len(claims)} claims for conflicts")
        
        results = {
            'checked': 0,
            'conflicts_found': 0,
            'relationships_created': 0,
            'claims_flagged': 0
        }
        
        for claim in claims:
            try:
                # Find potential conflicts
                conflicts = await self._find_conflicts(claim)
                
                if conflicts:
                    # Create relationships for conflicts
                    for conflict in conflicts:
                        await self._create_conflict_relationship(claim, conflict)
                        results['relationships_created'] += 1
                        self.stats['relationships_created'] += 1
                    
                    # Flag claim as having conflicts
                    await self._flag_claim_conflicts(claim, conflicts)
                    results['claims_flagged'] += 1
                    self.stats['claims_flagged'] += 1
                    
                    results['conflicts_found'] += len(conflicts)
                    self.stats['conflicts_detected'] += len(conflicts)
                
                results['checked'] += 1
                
            except Exception as e:
                self.logger.error(f"Error checking conflicts for {claim.id}: {e}")
                continue
        
        self.logger.info(
            f"Conflict detection complete. Checked {results['checked']} claims, "
            f"found {results['conflicts_found']} conflicts, "
            f"created {results['relationships_created']} relationships"
        )
        
        return results
    
    async def _get_claims_to_check(self, limit: int = 10) -> List[ScientificClaim]:
        """
        Fetch claims that need conflict checking.
        
        These are typically:
        - Recently added active claims
        - Claims not yet checked for conflicts
        - Claims in categories with known conflicts
        """
        # Fetch active claims
        all_claims = await self.supabase.get_all_active_claims(limit=limit * 2)
        
        # Filter for those that haven't been checked
        # In production, add a 'conflict_checked_at' field
        return [c for c in all_claims if not c.conflicting_evidence][:limit]
    
    async def _find_conflicts(self, claim: ScientificClaim) -> List[Dict[str, Any]]:
        """
        Find claims that conflict with the given claim.
        
        Args:
            claim: Claim to check
        
        Returns:
            List of conflicting claims with details
        """
        conflicts = []
        
        # 1. Find semantically similar claims
        similar_claims = await self._find_similar_claims(claim)
        
        # 2. Check each for actual conflict
        for similar in similar_claims:
            is_conflict = await self._analyze_conflict(claim, similar)
            
            if is_conflict:
                conflicts.append({
                    'claim_id': similar.get('id'),
                    'claim': similar.get('claim'),
                    'evidence_level': similar.get('evidence_level'),
                    'confidence': similar.get('similarity', 0),
                    'type': 'semantic_conflict'
                })
        
        # 3. Check for evidence level conflicts
        evidence_conflicts = await self._check_evidence_conflicts(claim)
        conflicts.extend(evidence_conflicts)
        
        return conflicts
    
    async def _find_similar_claims(self, claim: ScientificClaim) -> List[Dict[str, Any]]:
        """Find claims similar to the given claim."""
        if not self.llm:
            return []
        
        # Generate embedding
        embedding = await self.llm.generate_embedding(claim.claim)
        if not embedding:
            return []
        
        # Search for similar claims
        similar = await self.supabase.find_similar_claims(
            embedding=embedding,
            threshold=self.similarity_threshold,
            limit=10
        )
        
        # Filter out the claim itself
        return [s for s in similar if s.get('id') != claim.id]
    
    async def _analyze_conflict(
        self,
        claim: ScientificClaim,
        other: Dict[str, Any]
    ) -> bool:
        """
        Analyze if two claims actually conflict.
        
        Args:
            claim: First claim
            other: Second claim
        
        Returns:
            True if conflict detected
        """
        # Quick heuristic checks first
        
        # Same evidence level - probably not a conflict, just replication
        if claim.evidence_level == other.get('evidence_level'):
            return False
        
        # If LLM available, use it for detailed analysis
        if self.llm:
            conflict_result = await self.llm.detect_conflict(
                claim_a=claim.claim,
                evidence_level_a=claim.evidence_level,
                study_design_a=claim.study_design or 'unknown',
                claim_b=other.get('claim', ''),
                evidence_level_b=other.get('evidence_level', 3),
                study_design_b=other.get('study_design', 'unknown')
            )
            
            return conflict_result.get('conflict_detected', False)
        
        # Simple heuristic: different conclusions with similar topics
        # This is a fallback when LLM is not available
        return self._heuristic_conflict_check(claim, other)
    
    def _heuristic_conflict_check(
        self,
        claim: ScientificClaim,
        other: Dict[str, Any]
    ) -> bool:
        """
        Simple heuristic conflict detection.
        
        Args:
            claim: First claim
            other: Second claim
        
        Returns:
            True if potential conflict
        """
        # Check for negation words
        negation_words = ['not', 'no', 'never', 'without', 'не', 'нет']
        
        claim_lower = claim.claim.lower()
        other_lower = other.get('claim', '').lower()
        
        claim_has_negation = any(word in claim_lower for word in negation_words)
        other_has_negation = any(word in other_lower for word in negation_words)
        
        # If one has negation and other doesn't, might be conflict
        if claim_has_negation != other_has_negation:
            # Check if they share key terms
            claim_words = set(claim_lower.split())
            other_words = set(other_lower.split())
            shared = claim_words & other_words
            
            # If significant overlap, likely conflict
            if len(shared) >= 3:
                return True
        
        return False
    
    async def _check_evidence_conflicts(
        self,
        claim: ScientificClaim
    ) -> List[Dict[str, Any]]:
        """
        Check for conflicts based on evidence levels.
        
        This identifies cases where a high-evidence claim contradicts
        the current claim.
        
        Args:
            claim: Claim to check
        
        Returns:
            List of evidence-based conflicts
        """
        conflicts = []
        
        # Get all claims in the same category
        category_claims = await self.supabase.get_claims_by_category(
            claim.category,
            limit=100
        )
        
        for other in category_claims:
            if other.id == claim.id:
                continue
            
            # If other claim has higher evidence and contradicts
            if other.evidence_level > claim.evidence_level:
                # Check for semantic similarity (would need embedding comparison)
                # For now, use a simple check
                if self._claims_related(claim, other):
                    conflicts.append({
                        'claim_id': other.id,
                        'claim': other.claim,
                        'evidence_level': other.evidence_level,
                        'confidence': 0.6,
                        'type': 'evidence_conflict'
                    })
        
        return conflicts
    
    def _claims_related(self, claim1: ScientificClaim, claim2: ScientificClaim) -> bool:
        """Check if two claims are related (simple heuristic)."""
        # Same category
        if claim1.category != claim2.category:
            return False
        
        # Share key terms
        words1 = set(claim1.claim.lower().split())
        words2 = set(claim2.claim.lower().split())
        shared = words1 & words2
        
        # If significant word overlap
        return len(shared) >= 2
    
    async def _create_conflict_relationship(
        self,
        claim: ScientificClaim,
        conflict: Dict[str, Any]
    ) -> bool:
        """
        Create a relationship record for the conflict.
        
        Args:
            claim: Source claim
            conflict: Conflicting claim details
        
        Returns:
            True if successful
        """
        if not claim.id or not conflict.get('claim_id'):
            return False
        
        relationship = KnowledgeRelationship(
            id=None,
            source_claim_id=claim.id,
            target_claim_id=conflict['claim_id'],
            relationship_type='contradicts',
            confidence=conflict.get('confidence', 0.5),
            notes=f"Detected conflict: {conflict.get('type', 'unknown')}"
        )
        
        try:
            await self.supabase.create_relationship(relationship)
            return True
        except Exception as e:
            self.logger.error(f"Error creating relationship: {e}")
            return False
    
    async def _flag_claim_conflicts(
        self,
        claim: ScientificClaim,
        conflicts: List[Dict[str, Any]]
    ) -> bool:
        """
        Flag a claim as having conflicting evidence.
        
        Args:
            claim: Claim to flag
            conflicts: List of conflicts found
        
        Returns:
            True if successful
        """
        if not claim.id:
            return False
        
        try:
            updates = {
                'conflicting_evidence': True,
                'updated_at': 'now()'
            }
            
            return await self.supabase.update_claim(claim.id, updates)
            
        except Exception as e:
            self.logger.error(f"Error flagging claim: {e}")
            return False
    
    async def get_conflict_stats(self) -> Dict[str, Any]:
        """Get conflict detection statistics."""
        return {
            'conflicts_detected': self.stats.get('conflicts_detected', 0),
            'relationships_created': self.stats.get('relationships_created', 0),
            'claims_flagged': self.stats.get('claims_flagged', 0)
        }
    
    async def analyze_conflict_network(self) -> Dict[str, Any]:
        """
        Analyze the network of conflicting claims.
        
        Returns:
            Network analysis results
        """
        # Fetch all active claims
        claims = await self.supabase.get_all_active_claims(limit=1000)
        
        # Build conflict graph
        conflict_graph = defaultdict(list)
        
        for claim in claims:
            if claim.conflicting_evidence:
                relationships = await self.supabase.get_relationships_for_claim(claim.id or "")
                for rel in relationships:
                    if rel.relationship_type == 'contradicts':
                        conflict_graph[claim.id].append(rel.target_claim_id)
        
        # Calculate metrics
        total_conflicting = len(conflict_graph)
        total_conflicts = sum(len(v) for v in conflict_graph.values()) // 2  # Divide by 2 (bidirectional)
        
        # Find most conflicted claims
        most_conflicted = sorted(
            conflict_graph.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:5]
        
        return {
            'total_conflicting_claims': total_conflicting,
            'total_conflict_relationships': total_conflicts,
            'most_conflicted_claims': [
                {'claim_id': c[0], 'conflict_count': len(c[1])}
                for c in most_conflicted
            ]
        }