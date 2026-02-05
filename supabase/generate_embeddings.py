#!/usr/bin/env python3
"""
Script to generate embeddings for scientific knowledge claims in Supabase.
Uses OpenAI API to generate embeddings and updates the database.

Usage:
    export OPENAI_API_KEY="your-key"
    export SUPABASE_URL="your-url"
    export SUPABASE_SERVICE_KEY="your-service-key"
    python generate_embeddings.py

Or with command line arguments:
    python generate_embeddings.py --openai-key "key" --supabase-url "url" --supabase-key "key"
"""

import os
import sys
import argparse
import asyncio
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

import httpx
from openai import AsyncOpenAI


@dataclass
class KnowledgeClaim:
    """Represents a scientific knowledge claim from the database."""
    id: str
    claim: str
    category: str
    evidence_level: int
    has_embedding: bool


class SupabaseClient:
    """Client for Supabase REST API."""
    
    def __init__(self, url: str, service_key: str):
        self.url = url.rstrip('/')
        self.service_key = service_key
        self.headers = {
            'apikey': service_key,
            'Authorization': f'Bearer {service_key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal'
        }
    
    async def get_claims_without_embeddings(self, limit: int = 100) -> List[KnowledgeClaim]:
        """Fetch claims that need embeddings generated."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.url}/rest/v1/scientific_knowledge",
                headers=self.headers,
                params={
                    'select': 'id,claim,category,evidence_level,embedding',
                    'embedding': 'is.null',
                    'status': 'eq.active',
                    'limit': limit
                }
            )
            response.raise_for_status()
            data = response.json()
            
            return [
                KnowledgeClaim(
                    id=item['id'],
                    claim=item['claim'],
                    category=item['category'],
                    evidence_level=item['evidence_level'],
                    has_embedding=item.get('embedding') is not None
                )
                for item in data
            ]
    
    async def get_all_claims(self, limit: int = 1000) -> List[KnowledgeClaim]:
        """Fetch all claims."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.url}/rest/v1/scientific_knowledge",
                headers=self.headers,
                params={
                    'select': 'id,claim,category,evidence_level,embedding',
                    'limit': limit
                }
            )
            response.raise_for_status()
            data = response.json()
            
            return [
                KnowledgeClaim(
                    id=item['id'],
                    claim=item['claim'],
                    category=item['category'],
                    evidence_level=item['evidence_level'],
                    has_embedding=item.get('embedding') is not None
                )
                for item in data
            ]
    
    async def update_embedding(self, claim_id: str, embedding: List[float]) -> bool:
        """Update the embedding for a specific claim."""
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.url}/rest/v1/scientific_knowledge",
                headers=self.headers,
                params={'id': f'eq.{claim_id}'},
                json={'embedding': embedding}
            )
            
            if response.status_code == 204:
                return True
            else:
                print(f"Error updating claim {claim_id}: {response.status_code} - {response.text}")
                return False


class EmbeddingGenerator:
    """Generates embeddings using OpenAI API."""
    
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
    
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text."""
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None
    
    async def generate_embeddings_batch(
        self, 
        texts: List[str], 
        batch_size: int = 100
    ) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts in batches."""
        results = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size} ({len(batch)} items)")
            
            try:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=batch
                )
                batch_embeddings = [item.embedding for item in response.data]
                results.extend(batch_embeddings)
            except Exception as e:
                print(f"Error processing batch: {e}")
                # Add None for each failed item in batch
                results.extend([None] * len(batch))
        
        return results


async def generate_embeddings_for_all(
    supabase: SupabaseClient,
    openai: EmbeddingGenerator,
    batch_size: int = 50,
    dry_run: bool = False
):
    """Generate embeddings for all claims without embeddings."""
    print("Fetching claims without embeddings...")
    claims = await supabase.get_claims_without_embeddings(limit=1000)
    
    if not claims:
        print("No claims found that need embeddings.")
        return
    
    print(f"Found {len(claims)} claims without embeddings")
    
    if dry_run:
        print("DRY RUN: Would process the following claims:")
        for claim in claims[:5]:
            print(f"  - {claim.claim[:80]}...")
        if len(claims) > 5:
            print(f"  ... and {len(claims) - 5} more")
        return
    
    # Process in batches
    total_processed = 0
    total_failed = 0
    
    for i in range(0, len(claims), batch_size):
        batch = claims[i:i + batch_size]
        print(f"\nProcessing batch {i//batch_size + 1}/{(len(claims) + batch_size - 1)//batch_size}")
        
        # Generate embeddings for batch
        texts = [claim.claim for claim in batch]
        embeddings = await openai.generate_embeddings_batch(texts, batch_size=len(batch))
        
        # Update database
        for claim, embedding in zip(batch, embeddings):
            if embedding:
                success = await supabase.update_embedding(claim.id, embedding)
                if success:
                    total_processed += 1
                    print(f"  ✓ Updated: {claim.claim[:60]}...")
                else:
                    total_failed += 1
            else:
                total_failed += 1
                print(f"  ✗ Failed: {claim.claim[:60]}...")
        
        # Small delay to avoid rate limits
        await asyncio.sleep(0.5)
    
    print(f"\n{'='*50}")
    print(f"Completed: {total_processed} processed, {total_failed} failed")


async def verify_embeddings(supabase: SupabaseClient):
    """Verify the state of embeddings in the database."""
    print("\nVerifying embeddings in database...")
    claims = await supabase.get_all_claims(limit=1000)
    
    with_embedding = sum(1 for c in claims if c.has_embedding)
    without_embedding = len(claims) - with_embedding
    
    print(f"\n{'='*50}")
    print(f"Total claims: {len(claims)}")
    print(f"With embeddings: {with_embedding}")
    print(f"Without embeddings: {without_embedding}")
    print(f"Coverage: {with_embedding/len(claims)*100:.1f}%" if claims else "N/A")
    
    # Show category breakdown
    categories = {}
    for claim in claims:
        cat = claim.category
        if cat not in categories:
            categories[cat] = {'total': 0, 'with_emb': 0}
        categories[cat]['total'] += 1
        if claim.has_embedding:
            categories[cat]['with_emb'] += 1
    
    print(f"\nBreakdown by category:")
    for cat, stats in sorted(categories.items()):
        pct = stats['with_emb']/stats['total']*100 if stats['total'] > 0 else 0
        print(f"  {cat}: {stats['with_emb']}/{stats['total']} ({pct:.0f}%)")


async def test_semantic_search(supabase: SupabaseClient, openai: EmbeddingGenerator, query: str):
    """Test semantic search with a query."""
    print(f"\nTesting semantic search with query: '{query}'")
    
    # Generate embedding for query
    query_embedding = await openai.generate_embedding(query)
    if not query_embedding:
        print("Failed to generate query embedding")
        return
    
    # Call search function via RPC
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{supabase.url}/rest/v1/rpc/search_knowledge",
            headers=supabase.headers,
            json={
                'query_embedding': query_embedding,
                'match_threshold': 0.7,
                'match_count': 5,
                'filter_category': None,
                'min_evidence_level': 1
            }
        )
        
        if response.status_code == 200:
            results = response.json()
            print(f"\nFound {len(results)} results:")
            for i, result in enumerate(results, 1):
                similarity = result.get('similarity', 0)
                claim = result.get('claim', '')
                category = result.get('category', '')
                evidence = result.get('evidence_level', 0)
                print(f"\n{i}. [{category}] (similarity: {similarity:.3f}, evidence: {evidence}/5)")
                print(f"   {claim[:100]}...")
        else:
            print(f"Error: {response.status_code} - {response.text}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate embeddings for scientific knowledge claims'
    )
    parser.add_argument(
        '--openai-key',
        default=os.getenv('OPENAI_API_KEY'),
        help='OpenAI API key (or set OPENAI_API_KEY env var)'
    )
    parser.add_argument(
        '--supabase-url',
        default=os.getenv('SUPABASE_URL'),
        help='Supabase URL (or set SUPABASE_URL env var)'
    )
    parser.add_argument(
        '--supabase-key',
        default=os.getenv('SUPABASE_SERVICE_KEY'),
        help='Supabase service role key (or set SUPABASE_SERVICE_KEY env var)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify embedding coverage and exit'
    )
    parser.add_argument(
        '--test-search',
        metavar='QUERY',
        help='Test semantic search with a query'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=50,
        help='Batch size for embedding generation (default: 50)'
    )
    
    args = parser.parse_args()
    
    # Validate required arguments
    missing = []
    if not args.openai_key:
        missing.append('OpenAI API key (--openai-key or OPENAI_API_KEY)')
    if not args.supabase_url:
        missing.append('Supabase URL (--supabase-url or SUPABASE_URL)')
    if not args.supabase_key:
        missing.append('Supabase service key (--supabase-key or SUPABASE_SERVICE_KEY)')
    
    if missing:
        print("Error: Missing required arguments:")
        for m in missing:
            print(f"  - {m}")
        sys.exit(1)
    
    # Initialize clients
    supabase = SupabaseClient(args.supabase_url, args.supabase_key)
    openai = EmbeddingGenerator(args.openai_key)
    
    # Run appropriate command
    if args.verify:
        asyncio.run(verify_embeddings(supabase))
    elif args.test_search:
        asyncio.run(test_semantic_search(supabase, openai, args.test_search))
    else:
        asyncio.run(generate_embeddings_for_all(
            supabase, 
            openai, 
            batch_size=args.batch_size,
            dry_run=args.dry_run
        ))
        
        # Show verification after generation
        if not args.dry_run:
            asyncio.run(verify_embeddings(supabase))


if __name__ == '__main__':
    main()
