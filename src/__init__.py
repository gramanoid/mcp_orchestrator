"""
Multi-Code-LLM Orchestrator (MCP)

A sophisticated system for orchestrating multiple state-of-the-art LLMs
to provide superior coding assistance.
"""

__version__ = "1.0.0"
__author__ = "Claude Code"

from src.core.orchestrator import MCPOrchestrator
from src.core.task import Task, TaskType, ComplexityLevel
from src.strategies import MaxQualityCouncilStrategy, ProgressiveDeepDiveStrategy

__all__ = [
    "MCPOrchestrator",
    "Task",
    "TaskType",
    "ComplexityLevel",
    "MaxQualityCouncilStrategy",
    "ProgressiveDeepDiveStrategy"
]