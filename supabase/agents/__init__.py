"""
Agent Swarm for Knowledge Base Expansion

This package contains agents for automated collection, validation,
and integration of scientific research into the knowledge base.
"""

from .base_agent import BaseAgent
from .research_agent import ResearchAgent
from .extraction_agent import ExtractionAgent
from .validation_agent import ValidationAgent
from .kb_agent import KnowledgeBaseAgent
from .conflict_agent import ConflictAgent

__all__ = [
    'BaseAgent',
    'ResearchAgent',
    'ExtractionAgent',
    'ValidationAgent',
    'KnowledgeBaseAgent',
    'ConflictAgent',
]