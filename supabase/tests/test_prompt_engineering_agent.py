"""Tests for Prompt Engineering Agent."""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from agents.prompt_engineering_agent import (
    PromptEngineeringAgent,
    KnowledgeSummary
)
from services.supabase_client import PromptVersion


class TestPromptEngineeringAgent:
    """Test PromptEngineeringAgent."""
    
    @pytest.fixture
    def mock_supabase(self):
        """Create mock Supabase client."""
        mock = Mock()
        mock.get_claims_by_category_with_filters = AsyncMock(return_value=[])
        mock.get_active_prompt = AsyncMock(return_value=None)
        mock.get_latest_prompt_version = AsyncMock(return_value=None)
        mock.save_prompt_version = AsyncMock()
        mock.activate_prompt_version = AsyncMock()
        return mock
    
    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM service."""
        return Mock()
    
    @pytest.fixture
    def agent(self, mock_supabase, mock_llm):
        """Create agent instance."""
        return PromptEngineeringAgent(
            supabase=mock_supabase,
            llm_service=mock_llm,
            categories=['strength_training', 'nutrition']
        )
    
    @pytest.mark.asyncio
    async def test_analyze_knowledge_empty(self, agent, mock_supabase):
        """Test knowledge analysis with no claims."""
        mock_supabase.get_claims_by_category_with_filters.return_value = []
        
        summary = await agent._analyze_knowledge('strength_training')
        
        assert summary.total_claims == 0
        assert summary.avg_evidence_level == 0
        assert summary.top_claims == []
    
    @pytest.mark.asyncio
    async def test_analyze_knowledge_with_claims(self, agent, mock_supabase):
        """Test knowledge analysis with claims."""
        mock_claims = [
            Mock(id='1', claim='Claim 1', evidence_level=4, confidence_score=0.9, category='strength_training'),
            Mock(id='2', claim='Claim 2', evidence_level=3, confidence_score=0.8, category='strength_training'),
        ]
        mock_supabase.get_claims_by_category_with_filters.return_value = mock_claims
        
        summary = await agent._analyze_knowledge('strength_training')
        
        assert summary.total_claims == 2
        assert summary.avg_evidence_level == 3.5
        assert len(summary.top_claims) == 2
    
    @pytest.mark.asyncio
    async def test_should_update_prompt_no_current(self, agent, mock_supabase):
        """Test should update when no current prompt."""
        mock_supabase.get_active_prompt.return_value = None
        
        summary = KnowledgeSummary(
            category='test',
            total_claims=10,
            avg_evidence_level=3,
            avg_confidence=0.8,
            top_claims=[],
            conflicting_areas=[],
            knowledge_gaps=[]
        )
        
        result = await agent._should_update_prompt('test', summary)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_should_update_prompt_significant_changes(self, agent, mock_supabase):
        """Test should update when significant changes detected."""
        current_prompt = PromptVersion(
            id='test-id',
            category='test',
            prompt_text='test',
            version=1,
            knowledge_snapshot={
                'total_claims': 10,
                'avg_evidence_level': 2.0,
                'conflicting_areas': []
            },
            performance_score=None,
            is_active=True,
            created_at=datetime.now(),
            metadata={}
        )
        mock_supabase.get_active_prompt.return_value = current_prompt
        
        # More claims (20% increase)
        summary = KnowledgeSummary(
            category='test',
            total_claims=15,  # > 10 * 1.2
            avg_evidence_level=3.0,
            avg_confidence=0.8,
            top_claims=[],
            conflicting_areas=[],
            knowledge_gaps=[]
        )
        
        result = await agent._should_update_prompt('test', summary)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_should_not_update_prompt(self, agent, mock_supabase):
        """Test should not update when no significant changes."""
        current_prompt = PromptVersion(
            id='test-id',
            category='test',
            prompt_text='test',
            version=1,
            knowledge_snapshot={
                'total_claims': 10,
                'avg_evidence_level': 3.0,
                'conflicting_areas': []
            },
            performance_score=None,
            is_active=True,
            created_at=datetime.now(),
            metadata={}
        )
        mock_supabase.get_active_prompt.return_value = current_prompt
        
        summary = KnowledgeSummary(
            category='test',
            total_claims=10,
            avg_evidence_level=3.0,
            avg_confidence=0.8,
            top_claims=[],
            conflicting_areas=[],
            knowledge_gaps=[]
        )
        
        result = await agent._should_update_prompt('test', summary)
        assert result is False
    
    def test_format_evidence_section(self, agent):
        """Test evidence section formatting."""
        summary = KnowledgeSummary(
            category='test',
            total_claims=50,
            avg_evidence_level=3.5,
            avg_confidence=0.85,
            top_claims=[
                {'id': '1', 'claim': 'Test claim', 'evidence_level': 5, 'confidence': 0.95}
            ],
            conflicting_areas=[],
            knowledge_gaps=[]
        )
        
        section = agent._format_evidence_section(summary)
        
        assert '50' in section
        assert '3.5/5' in section
        assert 'Test claim' in section
        assert '95%' in section
    
    @pytest.mark.asyncio
    async def test_validate_prompt_valid(self, agent):
        """Test prompt validation - valid case."""
        prompt = """
        You are a fitness coach powered by scientific research.
        
        Evidence base:
        Total scientific claims: 100
        Average evidence level: 3.5/5
        
        Guidelines:
        1. Always cite evidence
        2. Be scientific
        """
        
        result = await agent._validate_prompt(prompt)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_prompt_too_short(self, agent):
        """Test prompt validation - too short."""
        prompt = "Short"
        
        result = await agent._validate_prompt(prompt)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_prompt_missing_sections(self, agent):
        """Test prompt validation - missing required sections."""
        prompt = "a" * 200  # Long enough but missing required sections
        
        result = await agent._validate_prompt(prompt)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_generate_prompt(self, agent):
        """Test prompt generation."""
        summary = KnowledgeSummary(
            category='strength_training',
            total_claims=50,
            avg_evidence_level=4.0,
            avg_confidence=0.9,
            top_claims=[
                {'id': '1', 'claim': 'Progressive overload increases strength', 'evidence_level': 5, 'confidence': 0.95}
            ],
            conflicting_areas=['optimal training frequency'],
            knowledge_gaps=['long-term effects']
        )
        
        prompt = await agent._generate_prompt('strength_training', summary)
        
        assert 'strength training coach' in prompt.lower()
        assert '50' in prompt
        assert '4.0/5' in prompt
        assert 'Progressive overload' in prompt
        assert 'optimal training frequency' in prompt
        assert 'long-term effects' in prompt
    
    @pytest.mark.asyncio
    async def test_save_prompt_version(self, agent, mock_supabase):
        """Test saving prompt version."""
        mock_supabase.get_latest_prompt_version.return_value = None
        mock_supabase.save_prompt_version.return_value = PromptVersion(
            id='new-id',
            category='test',
            prompt_text='test prompt',
            version=1,
            knowledge_snapshot={'total_claims': 10},
            performance_score=None,
            is_active=False,
            created_at=datetime.now(),
            metadata={}
        )
        
        summary = KnowledgeSummary(
            category='test',
            total_claims=10,
            avg_evidence_level=3.0,
            avg_confidence=0.8,
            top_claims=[],
            conflicting_areas=[],
            knowledge_gaps=[]
        )
        
        version = await agent._save_prompt_version('test', 'test prompt', summary)
        
        assert version.version == 1
        assert version.category == 'test'
        mock_supabase.save_prompt_version.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_should_activate_first_version(self, agent):
        """Test activation for first version."""
        version = PromptVersion(
            id='test-id',
            category='test',
            prompt_text='test',
            version=1,
            knowledge_snapshot={},
            performance_score=None,
            is_active=False,
            created_at=datetime.now(),
            metadata={}
        )
        
        result = await agent._should_activate(version)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_should_activate_newer_version(self, agent, mock_supabase):
        """Test activation for newer version."""
        mock_supabase.get_active_prompt.return_value = PromptVersion(
            id='current-id',
            category='test',
            prompt_text='current',
            version=1,
            knowledge_snapshot={},
            performance_score=None,
            is_active=True,
            created_at=datetime.now(),
            metadata={}
        )
        
        version = PromptVersion(
            id='new-id',
            category='test',
            prompt_text='new',
            version=2,
            knowledge_snapshot={},
            performance_score=None,
            is_active=False,
            created_at=datetime.now(),
            metadata={}
        )
        
        result = await agent._should_activate(version)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_should_not_activate_older_version(self, agent, mock_supabase):
        """Test no activation for older version."""
        mock_supabase.get_active_prompt.return_value = PromptVersion(
            id='current-id',
            category='test',
            prompt_text='current',
            version=3,
            knowledge_snapshot={},
            performance_score=None,
            is_active=True,
            created_at=datetime.now(),
            metadata={}
        )
        
        version = PromptVersion(
            id='old-id',
            category='test',
            prompt_text='old',
            version=2,
            knowledge_snapshot={},
            performance_score=None,
            is_active=False,
            created_at=datetime.now(),
            metadata={}
        )
        
        result = await agent._should_activate(version)
        assert result is False
    
    def test_identify_knowledge_gaps(self, agent):
        """Test knowledge gap identification."""
        # Too few claims
        claims = [Mock(evidence_level=4)]
        gaps = agent._identify_knowledge_gaps('test', claims)
        assert any('Limited research' in g for g in gaps)
        
        # Low evidence level
        claims = [Mock(evidence_level=1) for _ in range(15)]
        gaps = agent._identify_knowledge_gaps('test', claims)
        assert any('lower-quality studies' in g for g in gaps)
        
        # Good quality
        claims = [Mock(evidence_level=4) for _ in range(15)]
        gaps = agent._identify_knowledge_gaps('test', claims)
        assert len(gaps) == 0
    
    def test_claim_to_dict(self, agent):
        """Test claim to dict conversion."""
        claim = Mock(
            id='test-id',
            claim='Test claim text',
            evidence_level=4,
            confidence_score=0.9,
            category='test_category'
        )
        
        result = agent._claim_to_dict(claim)
        
        assert result['id'] == 'test-id'
        assert result['claim'] == 'Test claim text'
        assert result['evidence_level'] == 4
        assert result['confidence'] == 0.9
        assert result['category'] == 'test_category'
    
    @pytest.mark.asyncio
    async def test_process_integration(self, agent, mock_supabase):
        """Test full process method."""
        # Setup mocks
        mock_supabase.get_claims_by_category_with_filters.return_value = []
        mock_supabase.get_active_prompt.return_value = None
        mock_supabase.get_latest_prompt_version.return_value = None
        
        saved_version = PromptVersion(
            id='new-id',
            category='strength_training',
            prompt_text='test',
            version=1,
            knowledge_snapshot={},
            performance_score=None,
            is_active=False,
            created_at=datetime.now(),
            metadata={}
        )
        mock_supabase.save_prompt_version.return_value = saved_version
        mock_supabase.activate_prompt_version.return_value = None
        
        results = await agent.process()
        
        assert results['categories_processed'] == 2
        assert results['prompts_generated'] == 2
        assert results['prompts_activated'] == 2
        assert len(results['errors']) == 0
    
    @pytest.mark.asyncio
    async def test_process_with_errors(self, agent, mock_supabase):
        """Test process method with errors."""
        # Make first category fail
        mock_supabase.get_claims_by_category_with_filters.side_effect = [
            Exception("DB Error"),  # First category fails
            []  # Second category succeeds
        ]
        mock_supabase.get_active_prompt.return_value = None
        mock_supabase.get_latest_prompt_version.return_value = None
        
        saved_version = PromptVersion(
            id='new-id',
            category='nutrition',
            prompt_text='test',
            version=1,
            knowledge_snapshot={},
            performance_score=None,
            is_active=False,
            created_at=datetime.now(),
            metadata={}
        )
        mock_supabase.save_prompt_version.return_value = saved_version
        
        results = await agent.process()
        
        assert results['categories_processed'] == 1  # Only one succeeded
        assert results['prompts_generated'] == 1
        assert len(results['errors']) == 1
        assert results['errors'][0]['category'] == 'strength_training'
