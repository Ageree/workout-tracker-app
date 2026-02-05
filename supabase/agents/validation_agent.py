"""
Validation Agent (✅) - Проверка качества и достоверности claims

Enhanced with:
- Auto-validation for trusted sources with high evidence
- Trusted journal/author checking
- Streamlined approval for authoritative sources
"""

from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass
from datetime import datetime
import re

from agents.base_agent import BaseAgent
from services.supabase_client import SupabaseClient, ScientificClaim
from services.llm_service import LLMService


@dataclass
class ValidationResult:
    """Result of claim validation."""
    claim_id: str
    is_valid: bool
    validation_score: float
    rejection_reasons: List[str]
    duplicate_of: Optional[str]
    conflicts_with: List[str]
    auto_validated: bool = False  # True if auto-validated from trusted source


class ValidationAgent(BaseAgent):
    """
    Validation Agent responsible for:
    - Checking for duplicate claims (semantic similarity)
    - Detecting conflicts with existing claims
    - Validating claim quality and evidence level
    - Approving or rejecting claims
    - Auto-validating claims from trusted sources
    """

    # Study designs that qualify for auto-validation
    AUTO_VALIDATE_STUDY_DESIGNS = {'meta_analysis', 'systematic_review'}

    # Minimum evidence level for auto-validation
    AUTO_VALIDATE_MIN_EVIDENCE = 4

    def __init__(
        self,
        supabase: SupabaseClient,
        llm_service: Optional[LLMService] = None,
        batch_size: int = 10,
        similarity_threshold: float = 0.85,
        min_evidence_level: int = 2,
        enable_auto_validation: bool = True
    ):
        super().__init__(name="ValidationAgent", supabase=supabase)
        self.llm = llm_service
        self.batch_size = batch_size
        self.similarity_threshold = similarity_threshold
        self.min_evidence_level = min_evidence_level
        self.enable_auto_validation = enable_auto_validation
        self.stats['claims_validated'] = 0
        self.stats['claims_approved'] = 0
        self.stats['claims_rejected'] = 0
        self.stats['claims_auto_validated'] = 0

        # Cached trusted journals (loaded from DB)
        self._trusted_journals: Set[str] = set()
        self._trusted_journals_loaded = False
    
    async def _load_trusted_journals(self) -> None:
        """Load trusted journals from database for auto-validation."""
        if self._trusted_journals_loaded:
            return

        try:
            journals = await self.supabase.get_trusted_journals()
            for journal in journals:
                # Add normalized name
                name = journal.get('normalized_name', '').lower()
                if name:
                    self._trusted_journals.add(name)
                # Add short name
                short_name = journal.get('short_name', '')
                if short_name:
                    self._trusted_journals.add(short_name.lower())
                # Add full name
                full_name = journal.get('name', '').lower()
                if full_name:
                    self._trusted_journals.add(full_name)

            self._trusted_journals_loaded = True
            self.logger.info(f"Loaded {len(self._trusted_journals)} trusted journal names")
        except Exception as e:
            self.logger.warning(f"Failed to load trusted journals: {e}")
            self._trusted_journals_loaded = True

    def _is_trusted_journal(self, journal_name: Optional[str]) -> bool:
        """Check if a journal is in the trusted list."""
        if not journal_name:
            return False
        normalized = journal_name.lower().strip()
        # Check exact match
        if normalized in self._trusted_journals:
            return True
        # Check partial match
        for trusted in self._trusted_journals:
            if trusted in normalized or normalized in trusted:
                return True
        return False

    def _is_auto_validatable(self, claim: ScientificClaim) -> bool:
        """
        Check if claim qualifies for auto-validation.

        Auto-validation criteria:
        1. Has a DOI (verifiable source)
        2. High evidence level (4+)
        3. Study design is meta-analysis or systematic review
        4. From a trusted journal

        Args:
            claim: Scientific claim to check

        Returns:
            True if claim can be auto-validated
        """
        if not self.enable_auto_validation:
            return False

        # Must have DOI
        if not claim.source_doi:
            return False

        # Must have high evidence level
        if claim.evidence_level < self.AUTO_VALIDATE_MIN_EVIDENCE:
            return False

        # Must be meta-analysis or systematic review
        if claim.study_design not in self.AUTO_VALIDATE_STUDY_DESIGNS:
            return False

        # Must be from trusted journal (check source_title or source_url for journal)
        # Note: We check source_title as it often contains journal info
        # In a real implementation, we'd have a source_journal field
        source_journal = getattr(claim, 'source_journal', None)
        if source_journal and self._is_trusted_journal(source_journal):
            return True

        # Check if source_title contains a trusted journal name
        if claim.source_title:
            for trusted in self._trusted_journals:
                if trusted in claim.source_title.lower():
                    return True

        return False

    async def process(self) -> Dict[str, Any]:
        """
        Main processing: validate draft claims.

        Returns:
            Dictionary with validation results
        """
        self.logger.info("Starting claim validation...")

        # Load trusted journals for auto-validation
        await self._load_trusted_journals()

        # Fetch draft claims
        draft_claims = await self._get_draft_claims(limit=self.batch_size)

        if not draft_claims:
            self.logger.info("No draft claims to validate")
            return {'validated': 0, 'approved': 0, 'rejected': 0, 'auto_validated': 0}

        self.logger.info(f"Found {len(draft_claims)} draft claims to validate")

        results = {
            'validated': 0,
            'approved': 0,
            'rejected': 0,
            'auto_validated': 0,
            'details': []
        }

        for claim in draft_claims:
            try:
                # Check if claim qualifies for auto-validation
                if self._is_auto_validatable(claim):
                    validation_result = ValidationResult(
                        claim_id=claim.id or "",
                        is_valid=True,
                        validation_score=0.95,  # High score for auto-validated
                        rejection_reasons=[],
                        duplicate_of=None,
                        conflicts_with=[],
                        auto_validated=True
                    )
                    await self._approve_claim(claim, validation_result, auto_validated=True)
                    results['approved'] += 1
                    results['auto_validated'] += 1
                    results['details'].append({
                        'claim_id': claim.id,
                        'action': 'auto_approved',
                        'score': validation_result.validation_score,
                        'reason': 'Trusted source with high evidence'
                    })
                    self.stats['claims_approved'] += 1
                    self.stats['claims_auto_validated'] += 1
                    self.logger.debug(f"Auto-validated claim {claim.id}")
                else:
                    # Standard validation
                    validation_result = await self._validate_claim(claim)

                    if validation_result.is_valid:
                        # Approve claim
                        await self._approve_claim(claim, validation_result)
                        results['approved'] += 1
                        results['details'].append({
                            'claim_id': claim.id,
                            'action': 'approved',
                            'score': validation_result.validation_score
                        })
                        self.stats['claims_approved'] += 1
                    else:
                        # Reject claim
                        await self._reject_claim(claim, validation_result)
                        results['rejected'] += 1
                        results['details'].append({
                            'claim_id': claim.id,
                            'action': 'rejected',
                            'reasons': validation_result.rejection_reasons
                        })
                        self.stats['claims_rejected'] += 1

                results['validated'] += 1
                self.stats['claims_validated'] += 1

            except Exception as e:
                self.logger.error(f"Error validating claim {claim.id}: {e}")
                continue

        self.logger.info(
            f"Validation complete. Validated {results['validated']} claims: "
            f"{results['approved']} approved ({results['auto_validated']} auto), "
            f"{results['rejected']} rejected"
        )

        return results
    
    async def _get_draft_claims(self, limit: int = 10) -> List[ScientificClaim]:
        """Fetch draft claims from database."""
        # For now, we'll fetch all active claims and filter by status
        # In production, add a specific query for draft status
        all_claims = await self.supabase.get_all_active_claims(limit=limit * 2)
        
        # Filter for draft status (we need to add status filtering to the client)
        # For now, return all as drafts for demonstration
        return [c for c in all_claims if c.status == 'draft'][:limit]
    
    async def _validate_claim(self, claim: ScientificClaim) -> ValidationResult:
        """
        Validate a single claim.
        
        Args:
            claim: Claim to validate
        
        Returns:
            ValidationResult
        """
        rejection_reasons = []
        duplicate_of = None
        conflicts_with = []
        
        # 1. Check evidence level
        if claim.evidence_level < self.min_evidence_level:
            rejection_reasons.append(
                f"Evidence level {claim.evidence_level} below minimum {self.min_evidence_level}"
            )
        
        # 2. Check for duplicates using embeddings
        similar_claims = await self._find_similar_claims(claim)
        
        for similar in similar_claims:
            similarity = similar.get('similarity', 0)
            if similarity > 0.95:
                # High similarity - likely duplicate
                duplicate_of = similar.get('id')
                rejection_reasons.append(f"Duplicate of claim {duplicate_of}")
                break
            elif similarity > self.similarity_threshold:
                # Moderate similarity - check for conflict
                is_conflict = await self._check_conflict(claim, similar)
                if is_conflict:
                    conflicts_with.append(similar.get('id'))
        
        # 3. Validate with LLM if available
        if self.llm and not duplicate_of:
            llm_validation = await self.llm.validate_claim(
                claim=claim.claim,
                category=claim.category,
                evidence_level=claim.evidence_level,
                study_design=claim.study_design or 'unknown',
                sample_size=claim.sample_size,
                effect_size=claim.effect_size,
                similar_claims=similar_claims
            )
            
            if not llm_validation.get('is_valid', True):
                rejection_reasons.extend(llm_validation.get('rejection_reasons', []))
            
            # Check for duplicates/conflicts from LLM
            if llm_validation.get('duplicate_of'):
                duplicate_of = llm_validation['duplicate_of']
                rejection_reasons.append(f"Duplicate of claim {duplicate_of}")
            
            conflicts_with.extend(llm_validation.get('conflicts_with', []))
        
        # 4. Calculate validation score
        validation_score = self._calculate_validation_score(
            claim, rejection_reasons, similar_claims
        )
        
        # Determine if valid
        is_valid = (
            len(rejection_reasons) == 0 and
            validation_score >= 0.6 and
            duplicate_of is None
        )
        
        return ValidationResult(
            claim_id=claim.id or "",
            is_valid=is_valid,
            validation_score=validation_score,
            rejection_reasons=rejection_reasons,
            duplicate_of=duplicate_of,
            conflicts_with=list(set(conflicts_with))  # Remove duplicates
        )
    
    async def _find_similar_claims(self, claim: ScientificClaim) -> List[Dict[str, Any]]:
        """Find similar claims using semantic search."""
        # Generate embedding for the claim
        if not self.llm:
            return []
        
        embedding = await self.llm.generate_embedding(claim.claim)
        if not embedding:
            return []
        
        # Search for similar claims
        similar = await self.supabase.find_similar_claims(
            embedding=embedding,
            threshold=self.similarity_threshold - 0.1,  # Slightly lower threshold for search
            limit=5
        )
        
        # Filter out the claim itself
        return [s for s in similar if s.get('id') != claim.id]
    
    async def _check_conflict(
        self,
        claim: ScientificClaim,
        other_claim: Dict[str, Any]
    ) -> bool:
        """
        Check if two claims conflict.
        
        Args:
            claim: New claim
            other_claim: Existing claim
        
        Returns:
            True if conflict detected
        """
        if not self.llm:
            # Simple heuristic: different evidence levels for same claim
            other_evidence = other_claim.get('evidence_level', 3)
            if abs(claim.evidence_level - other_evidence) >= 2:
                return True
            return False
        
        # Use LLM for conflict detection
        conflict_result = await self.llm.detect_conflict(
            claim_a=claim.claim,
            evidence_level_a=claim.evidence_level,
            study_design_a=claim.study_design or 'unknown',
            claim_b=other_claim.get('claim', ''),
            evidence_level_b=other_claim.get('evidence_level', 3),
            study_design_b=other_claim.get('study_design', 'unknown')
        )
        
        return conflict_result.get('conflict_detected', False)
    
    def _calculate_validation_score(
        self,
        claim: ScientificClaim,
        rejection_reasons: List[str],
        similar_claims: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate overall validation score.
        
        Returns:
            Score between 0 and 1
        """
        score = claim.confidence_score
        
        # Boost for higher evidence level
        evidence_boost = (claim.evidence_level - 1) * 0.05
        score += evidence_boost
        
        # Boost for sample size
        if claim.sample_size:
            if claim.sample_size >= 100:
                score += 0.1
            elif claim.sample_size >= 50:
                score += 0.05
        
        # Penalty for rejection reasons
        score -= len(rejection_reasons) * 0.2
        
        # Penalty for conflicts
        score -= len(similar_claims) * 0.05
        
        # Clamp to [0, 1]
        return max(0.0, min(1.0, score))
    
    async def _approve_claim(
        self,
        claim: ScientificClaim,
        validation: ValidationResult,
        auto_validated: bool = False
    ) -> None:
        """Approve a claim and update its status."""
        updates = {
            'status': 'active',
            'confidence_score': validation.validation_score,
            'conflicting_evidence': len(validation.conflicts_with) > 0,
            'updated_at': 'now()'
        }

        # Mark as auto-validated if applicable
        if auto_validated or validation.auto_validated:
            updates['auto_validated'] = True
            updates['trusted_source'] = True

        if claim.id:
            await self.supabase.update_claim(claim.id, updates)

            # Create conflict relationships if any
            for conflict_id in validation.conflicts_with:
                await self.supabase.create_relationship({
                    'id': None,
                    'source_claim_id': claim.id,
                    'target_claim_id': conflict_id,
                    'relationship_type': 'conflicts_with',
                    'confidence': 0.7,
                    'notes': 'Detected during validation'
                })
    
    async def _reject_claim(
        self,
        claim: ScientificClaim,
        validation: ValidationResult
    ) -> None:
        """Reject a claim and update its status."""
        updates = {
            'status': 'deprecated',
            'confidence_score': validation.validation_score,
            'updated_at': 'now()'
        }
        
        if claim.id:
            await self.supabase.update_claim(claim.id, updates)
    
    async def get_validation_stats(self) -> Dict[str, Any]:
        """Get statistics about validation process."""
        total = self.stats.get('claims_validated', 0)
        approved = self.stats.get('claims_approved', 0)
        rejected = self.stats.get('claims_rejected', 0)
        auto_validated = self.stats.get('claims_auto_validated', 0)

        return {
            'total_validated': total,
            'approved': approved,
            'rejected': rejected,
            'auto_validated': auto_validated,
            'approval_rate': approved / max(1, total),
            'auto_validation_rate': auto_validated / max(1, approved) if approved > 0 else 0
        }