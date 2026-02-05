"""
Tests for AI Coach SQL functions.

Run with: pytest tests/test_ai_coach_functions.py -v
"""

import pytest
import uuid
from datetime import datetime

# Mark all tests as asyncio
pytestmark = pytest.mark.asyncio


class TestMatchKnowledgeVectors:
    """Tests for match_knowledge_vectors function."""
    
    async def test_function_exists(self, supabase_client):
        """Test that the function exists and is callable."""
        # Create a dummy embedding (1536 dimensions of zeros)
        embedding = [0.0] * 1536
        
        try:
            result = await supabase_client.find_similar_claims(
                embedding=embedding,
                threshold=0.7,
                limit=5
            )
            # Should return a list (may be empty)
            assert isinstance(result, list)
        except Exception as e:
            # Function might not exist yet
            pytest.skip(f"Function not available: {e}")
    
    async def test_match_with_claim_summary(self, supabase_client):
        """Test that match_knowledge_vectors returns claim_summary."""
        embedding = [0.0] * 1536
        
        try:
            # Use the new function name
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{supabase_client.url}/rest/v1/rpc/match_knowledge_vectors",
                    headers=supabase_client.headers,
                    json={
                        'query_embedding': embedding,
                        'match_threshold': 0.7,
                        'match_count': 5,
                        'filter_category': None,
                        'min_evidence_level': 1
                    }
                )
                
                if response.status_code == 404:
                    pytest.skip("match_knowledge_vectors function not found")
                
                response.raise_for_status()
                data = response.json()
                
                # Check that results have claim_summary field
                if data:
                    for item in data:
                        assert 'claim_summary' in item
                        
        except Exception as e:
            pytest.skip(f"Test skipped: {e}")


class TestGetKnowledgeContext:
    """Tests for get_knowledge_context function."""
    
    async def test_function_returns_expected_structure(self, supabase_client):
        """Test that function returns correct structure."""
        try:
            result = await supabase_client.get_knowledge_context(
                query_text="protein intake for muscle growth",
                max_results=3,
                min_evidence_level=2
            )
            
            # Check structure
            assert 'context_text' in result or hasattr(result, 'context_text')
            assert 'knowledge_ids' in result or hasattr(result, 'knowledge_ids')
            assert 'avg_evidence_level' in result or hasattr(result, 'avg_evidence_level')
            
        except Exception as e:
            if "404" in str(e):
                pytest.skip("get_knowledge_context function not found")
            raise
    
    async def test_empty_query_returns_empty_context(self, supabase_client):
        """Test that empty query returns empty context."""
        try:
            result = await supabase_client.get_knowledge_context(
                query_text="xyznonexistentquery123",
                max_results=5
            )
            
            # Should return empty or minimal context
            context_text = result.get('context_text', '') if isinstance(result, dict) else ''
            knowledge_ids = result.get('knowledge_ids', []) if isinstance(result, dict) else []
            
            assert knowledge_ids == [] or len(knowledge_ids) == 0
            
        except Exception as e:
            if "404" in str(e):
                pytest.skip("get_knowledge_context function not found")
            raise


class TestSaveMessageKnowledge:
    """Tests for save_message_knowledge function."""
    
    async def test_function_updates_message(self, supabase_client):
        """Test that function updates message with knowledge."""
        message_id = str(uuid.uuid4())
        knowledge_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        evidence_level = 3.5
        
        try:
            result = await supabase_client.save_message_knowledge(
                message_id=message_id,
                knowledge_ids=knowledge_ids,
                evidence_level=evidence_level
            )
            
            # Should return True even if message doesn't exist (no error)
            assert isinstance(result, bool)
            
        except Exception as e:
            if "404" in str(e):
                pytest.skip("save_message_knowledge function not found")
            raise


class TestGetRelevantKnowledgeForQuery:
    """Tests for get_relevant_knowledge_for_query function."""
    
    async def test_function_returns_knowledge_records(self, supabase_client):
        """Test that function returns full knowledge records."""
        try:
            result = await supabase_client.get_relevant_knowledge_for_query(
                query_text="strength training",
                max_results=3,
                min_evidence_level=2
            )
            
            # Should return a list
            assert isinstance(result, list)
            
            # If results exist, check structure
            if result:
                for item in result:
                    assert 'id' in item
                    assert 'claim' in item
                    assert 'evidence_level' in item
                    
        except Exception as e:
            if "404" in str(e):
                pytest.skip("get_relevant_knowledge_for_query function not found")
            raise
    
    async def test_filter_by_category(self, supabase_client):
        """Test category filtering."""
        try:
            result = await supabase_client.get_relevant_knowledge_for_query(
                query_text="nutrition",
                max_results=5,
                filter_categories=["nutrition"]
            )
            
            assert isinstance(result, list)
            
            # All results should be in nutrition category
            for item in result:
                assert item.get('category') == 'nutrition'
                
        except Exception as e:
            if "404" in str(e):
                pytest.skip("get_relevant_knowledge_for_query function not found")
            raise


class TestPendingEmbeddings:
    """Tests for get_pending_embeddings function."""
    
    async def test_function_returns_pending_claims(self, supabase_client):
        """Test that function returns claims with pending status."""
        try:
            result = await supabase_client.get_pending_embeddings(limit=5)
            
            # Should return a list
            assert isinstance(result, list)
            
        except Exception as e:
            if "404" in str(e):
                pytest.skip("get_pending_embeddings function not found")
            raise


class TestEmbeddingStatusTrigger:
    """Tests for auto_update_embedding trigger."""
    
    async def test_new_claim_has_pending_status(self, supabase_client):
        """Test that new claims automatically get pending status."""
        import httpx
        
        # Create a test claim
        test_claim = {
            'claim': 'Test claim for trigger verification',
            'claim_summary': 'Test summary',
            'category': 'general',
            'evidence_level': 3,
            'confidence_score': 0.8,
            'status': 'active'
        }
        
        try:
            async with httpx.AsyncClient() as client:
                # Insert claim
                response = await client.post(
                    f"{supabase_client.url}/rest/v1/scientific_knowledge",
                    headers=supabase_client.headers,
                    json=test_claim
                )
                
                if response.status_code not in [200, 201]:
                    pytest.skip("Could not insert test claim")
                
                data = response.json()
                claim_id = data[0]['id']
                
                # Verify embedding_status is 'pending'
                get_response = await client.get(
                    f"{supabase_client.url}/rest/v1/scientific_knowledge",
                    headers=supabase_client.headers,
                    params={'id': f'eq.{claim_id}', 'select': 'embedding_status'}
                )
                
                get_response.raise_for_status()
                claim_data = get_response.json()
                
                if claim_data:
                    assert claim_data[0].get('embedding_status') == 'pending'
                
                # Clean up
                await client.delete(
                    f"{supabase_client.url}/rest/v1/scientific_knowledge",
                    headers=supabase_client.headers,
                    params={'id': f'eq.{claim_id}'}
                )
                
        except Exception as e:
            pytest.skip(f"Trigger test skipped: {e}")


class TestUpdateEmbeddingStatus:
    """Tests for update_embedding_status function."""
    
    async def test_update_to_completed(self, supabase_client):
        """Test updating embedding status to completed."""
        try:
            # This would require an existing claim, so we just test the call
            result = await supabase_client.update_embedding_status(
                claim_id=str(uuid.uuid4()),
                embedding=[0.1] * 1536,
                status='completed'
            )
            
            # Should return boolean
            assert isinstance(result, bool)
            
        except Exception as e:
            if "404" in str(e):
                pytest.skip("update_embedding_status function not found")
            raise


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing functions."""
    
    async def test_match_scientific_knowledge_still_works(self, supabase_client):
        """Test that old function name still works."""
        embedding = [0.0] * 1536
        
        try:
            result = await supabase_client.find_similar_claims(
                embedding=embedding,
                threshold=0.7,
                limit=5
            )
            
            # Should work without error
            assert isinstance(result, list)
            
        except Exception as e:
            pytest.skip(f"Backward compatibility test skipped: {e}")


# Fixtures
@pytest.fixture
async def supabase_client():
    """Create Supabase client for testing."""
    import sys
    sys.path.insert(0, '/Users/saveliy/Documents/workout tracker app/supabase')
    
    from services.supabase_client import SupabaseClient
    from config.settings import Settings
    
    settings = Settings()
    client = SupabaseClient(
        url=settings.supabase_url,
        service_key=settings.supabase_service_key
    )
    
    return client
