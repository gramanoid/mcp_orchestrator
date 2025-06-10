"""
Orchestration strategies for coordinating multiple LLMs.
"""

from src.strategies.max_quality_council import MaxQualityCouncilStrategy
from src.strategies.progressive_deep_dive import ProgressiveDeepDiveStrategy

__all__ = ['MaxQualityCouncilStrategy', 'ProgressiveDeepDiveStrategy']