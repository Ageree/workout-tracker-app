"""
LLM Service for Extraction and Validation Agents.
Supports OpenAI GPT-4o, Anthropic Claude, and Kimi (Moonshot AI).
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import json
import httpx
import os


@dataclass
class ExtractedClaim:
    """Represents a claim extracted from a research paper."""
    claim: str
    claim_summary: str
    evidence_level: int
    sample_size: Optional[int]
    effect_size: Optional[str]
    study_design: str
    population: Optional[str]
    key_findings: List[str]
    limitations: Optional[str]
    category: str
    confidence: float


class LLMService:
    """Service for LLM operations using OpenAI or Anthropic APIs."""
    
    # Extraction prompt template
    EXTRACTION_PROMPT = """You are a scientific research assistant specializing in exercise science, sports medicine, and fitness research.

Analyze the following research paper and extract scientific claims. For each significant claim found, provide:

1. **Claim**: The main scientific claim in Russian (concise, factual statement)
2. **Claim Summary**: A brief 1-2 sentence summary in Russian
3. **Evidence Level**: Rate 1-5 where:
   - 1 = Expert opinion, case study
   - 2 = Cross-sectional, observational
   - 3 = Cohort or case-control
   - 4 = Randomized Controlled Trial (RCT)
   - 5 = Systematic review or meta-analysis
4. **Sample Size**: Number of participants (if mentioned)
5. **Effect Size**: Effect size or magnitude of results (e.g., "d=0.8", "15% increase", "p<0.001")
6. **Study Design**: One of: meta_analysis, systematic_review, rct, cohort, case_control, cross_sectional, case_study, expert_opinion
7. **Population**: Study population (e.g., "trained athletes", "sedentary adults", "elderly")
8. **Key Findings**: Array of 2-4 key findings in Russian
9. **Limitations**: Study limitations mentioned or implied
10. **Category**: One of: hypertrophy, strength, endurance, nutrition, recovery, injury_prevention, technique, programming, supplements, general
11. **Confidence**: Your confidence in this extraction (0.0-1.0)

Paper Title: {title}
Authors: {authors}
Abstract: {abstract}

Respond ONLY with a JSON array of claims. Each claim should be an object with the fields above.
If no significant claims can be extracted, return an empty array [].

Example response format:
[
  {{
    "claim": "Прогрессивная нагрузка увеличивает гипертрофию мышц",
    "claim_summary": "Исследование показало, что постепенное увеличение веса стимулирует рост мышц",
    "evidence_level": 4,
    "sample_size": 45,
    "effect_size": "d=0.65",
    "study_design": "rct",
    "population": "trained men",
    "key_findings": [
      "Увеличение силы на 15% за 12 недель",
      "Гипертрофия type II волокон"
    ],
    "limitations": "Small sample size, short duration",
    "category": "hypertrophy",
    "confidence": 0.92
  }}
]"""

    # Validation prompt template
    VALIDATION_PROMPT = """You are a scientific validation expert. Evaluate the following scientific claim for quality and validity.

Claim: {claim}
Category: {category}
Evidence Level: {evidence_level}
Study Design: {study_design}
Sample Size: {sample_size}
Effect Size: {effect_size}

Existing Similar Claims:
{similar_claims}

Evaluate and respond with JSON:
{{
  "is_valid": true/false,
  "validation_score": 0.0-1.0,
  "rejection_reasons": ["reason1", "reason2"] (empty if valid),
  "suggested_improvements": ["improvement1"] (optional),
  "duplicate_of": "claim_id" (null if not duplicate),
  "conflicts_with": ["claim_id1", "claim_id2"] (empty if no conflicts)
}}

Validation criteria:
- Evidence level should match study design
- Sample size should be appropriate for the claim
- Effect size should be reported if claiming significant results
- Should not be duplicate of existing claims (similarity > 0.9)
- Should not contradict higher-evidence claims without strong justification"""

    # Conflict detection prompt
    CONFLICT_PROMPT = """Compare these two scientific claims and determine if they conflict with each other.

Claim A: {claim_a}
Evidence Level A: {evidence_level_a}
Study Design A: {study_design_a}

Claim B: {claim_b}
Evidence Level B: {evidence_level_b}
Study Design B: {study_design_b}

Respond with JSON:
{{
  "conflict_detected": true/false,
  "conflict_type": "direct" | "partial" | "none",
  "confidence": 0.0-1.0,
  "explanation": "Explanation of the conflict or why there's no conflict",
  "resolution_suggestion": "How to resolve if conflict exists"
}}"""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
        kimi_api_key: Optional[str] = None,
        default_provider: str = 'openai',
        model: Optional[str] = None
    ):
        """
        Initialize LLM service.
        
        Args:
            openai_api_key: OpenAI API key
            anthropic_api_key: Anthropic API key
            kimi_api_key: Kimi (Moonshot AI) API key
            default_provider: Default provider ('openai', 'anthropic', or 'kimi')
            model: Model name (defaults to provider's default)
        """
        self.openai_api_key = openai_api_key
        self.anthropic_api_key = anthropic_api_key
        self.kimi_api_key = kimi_api_key or os.getenv('KIMI_API_KEY')
        self.default_provider = default_provider
        
        # Set default model based on provider
        if model:
            self.model = model
        elif default_provider == 'kimi':
            self.model = 'kimi-k2.5'
        elif default_provider == 'openai':
            self.model = 'gpt-4o'
        else:
            self.model = 'claude-3-sonnet-20240229'
    
    async def _call_openai(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 2000
    ) -> str:
        """Call OpenAI API."""
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not provided")
        
        url = "https://api.openai.com/v1/chat/completions"
        
        headers = {
            'Authorization': f'Bearer {self.openai_api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': 'You are a scientific research assistant. Respond only with valid JSON.'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': temperature,
            'max_tokens': max_tokens
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content']
    
    async def _call_anthropic(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 2000
    ) -> str:
        """Call Anthropic API."""
        if not self.anthropic_api_key:
            raise ValueError("Anthropic API key not provided")
        
        url = "https://api.anthropic.com/v1/messages"
        
        headers = {
            'x-api-key': self.anthropic_api_key,
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01'
        }
        
        payload = {
            'model': self.model,
            'max_tokens': max_tokens,
            'temperature': temperature,
            'system': 'You are a scientific research assistant. Respond only with valid JSON.',
            'messages': [
                {'role': 'user', 'content': prompt}
            ]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()
            return data['content'][0]['text']
    
    async def _call_kimi(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 2000
    ) -> str:
        """Call Kimi (Moonshot AI) API using OpenAI-compatible interface."""
        if not self.kimi_api_key:
            raise ValueError("Kimi API key not provided")
        
        # Kimi uses OpenAI-compatible API
        url = "https://api.moonshot.cn/v1/chat/completions"
        
        headers = {
            'Authorization': f'Bearer {self.kimi_api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': 'You are a scientific research assistant. Respond only with valid JSON.'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': temperature,
            'max_tokens': max_tokens
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content']

    async def _call_llm(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 2000
    ) -> str:
        """Call the configured LLM provider."""
        if self.default_provider == 'openai':
            return await self._call_openai(prompt, temperature, max_tokens)
        elif self.default_provider == 'kimi':
            return await self._call_kimi(prompt, temperature, max_tokens)
        else:
            return await self._call_anthropic(prompt, temperature, max_tokens)
    
    def _clean_json_response(self, response: str) -> str:
        """Clean JSON response from markdown formatting."""
        response = response.strip()
        
        # Remove markdown code blocks
        if response.startswith('```json'):
            response = response[7:]
        elif response.startswith('```'):
            response = response[3:]
        
        if response.endswith('```'):
            response = response[:-3]
        
        return response.strip()
    
    async def extract_claims(
        self,
        title: str,
        authors: List[str],
        abstract: Optional[str]
    ) -> List[ExtractedClaim]:
        """
        Extract claims from a research paper.
        
        Args:
            title: Paper title
            authors: List of authors
            abstract: Paper abstract
        
        Returns:
            List of ExtractedClaim objects
        """
        if not abstract:
            return []
        
        prompt = self.EXTRACTION_PROMPT.format(
            title=title,
            authors=', '.join(authors) if authors else 'Unknown',
            abstract=abstract[:4000]  # Limit abstract length
        )
        
        try:
            response = await self._call_llm(prompt, temperature=0.1, max_tokens=3000)
            response = self._clean_json_response(response)
            
            data = json.loads(response)
            
            if not isinstance(data, list):
                print(f"Unexpected response format: {type(data)}")
                return []
            
            claims = []
            for item in data:
                try:
                    claim = ExtractedClaim(
                        claim=item.get('claim', ''),
                        claim_summary=item.get('claim_summary', ''),
                        evidence_level=item.get('evidence_level', 3),
                        sample_size=item.get('sample_size'),
                        effect_size=item.get('effect_size'),
                        study_design=item.get('study_design', 'unknown'),
                        population=item.get('population'),
                        key_findings=item.get('key_findings', []),
                        limitations=item.get('limitations'),
                        category=item.get('category', 'general'),
                        confidence=item.get('confidence', 0.5)
                    )
                    if claim.claim:  # Only add if claim text exists
                        claims.append(claim)
                except Exception as e:
                    print(f"Error parsing claim: {e}")
                    continue
            
            return claims
            
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Response: {response[:500]}")
            return []
        except Exception as e:
            print(f"Error extracting claims: {e}")
            return []
    
    async def validate_claim(
        self,
        claim: str,
        category: str,
        evidence_level: int,
        study_design: str,
        sample_size: Optional[int],
        effect_size: Optional[str],
        similar_claims: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate a scientific claim.
        
        Args:
            claim: The claim text
            category: Claim category
            evidence_level: Evidence level (1-5)
            study_design: Study design type
            sample_size: Sample size
            effect_size: Effect size
            similar_claims: List of similar existing claims
        
        Returns:
            Validation result dictionary
        """
        similar_text = "\n".join([
            f"- {c.get('claim', '')} (ID: {c.get('id', 'unknown')})"
            for c in similar_claims[:5]
        ]) or "None found"
        
        prompt = self.VALIDATION_PROMPT.format(
            claim=claim,
            category=category,
            evidence_level=evidence_level,
            study_design=study_design,
            sample_size=sample_size or 'Not specified',
            effect_size=effect_size or 'Not specified',
            similar_claims=similar_text
        )
        
        try:
            response = await self._call_llm(prompt, temperature=0.1, max_tokens=1500)
            response = self._clean_json_response(response)
            
            return json.loads(response)
            
        except Exception as e:
            print(f"Error validating claim: {e}")
            return {
                'is_valid': False,
                'validation_score': 0.0,
                'rejection_reasons': [f'Validation error: {str(e)}'],
                'duplicate_of': None,
                'conflicts_with': []
            }
    
    async def detect_conflict(
        self,
        claim_a: str,
        evidence_level_a: int,
        study_design_a: str,
        claim_b: str,
        evidence_level_b: int,
        study_design_b: str
    ) -> Dict[str, Any]:
        """
        Detect conflict between two claims.
        
        Args:
            claim_a: First claim text
            evidence_level_a: Evidence level of first claim
            study_design_a: Study design of first claim
            claim_b: Second claim text
            evidence_level_b: Evidence level of second claim
            study_design_b: Study design of second claim
        
        Returns:
            Conflict detection result
        """
        prompt = self.CONFLICT_PROMPT.format(
            claim_a=claim_a,
            evidence_level_a=evidence_level_a,
            study_design_a=study_design_a,
            claim_b=claim_b,
            evidence_level_b=evidence_level_b,
            study_design_b=study_design_b
        )
        
        try:
            response = await self._call_llm(prompt, temperature=0.1, max_tokens=1000)
            response = self._clean_json_response(response)
            
            return json.loads(response)
            
        except Exception as e:
            print(f"Error detecting conflict: {e}")
            return {
                'conflict_detected': False,
                'conflict_type': 'none',
                'confidence': 0.0,
                'explanation': f'Error: {str(e)}',
                'resolution_suggestion': None
            }
    
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text using OpenAI API.
        Note: Kimi doesn't have embedding API, so we use OpenAI for embeddings.
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding vector or None
        """
        if not self.openai_api_key:
            return None
        
        url = "https://api.openai.com/v1/embeddings"
        
        headers = {
            'Authorization': f'Bearer {self.openai_api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': 'text-embedding-3-small',
            'input': text[:8000]  # Limit text length
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return data['data'][0]['embedding']
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None
    
    def set_provider(self, provider: str, model: Optional[str] = None) -> None:
        """
        Change the LLM provider at runtime.
        
        Args:
            provider: Provider name ('openai', 'anthropic', or 'kimi')
            model: Optional model name override
        """
        self.default_provider = provider
        if model:
            self.model = model
        elif provider == 'kimi':
            self.model = 'kimi-k2.5'
        elif provider == 'openai':
            self.model = 'gpt-4o'
        else:
            self.model = 'claude-3-sonnet-20240229'