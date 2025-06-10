"""
Thinking modes for controlling LLM reasoning depth and token usage.

Inspired by Beehive Innovations' Gemini MCP server approach.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class ThinkingMode(Enum):
    """Thinking modes with associated token budgets."""
    MINIMAL = "minimal"     # 128 tokens - Simple tasks
    LOW = "low"            # 2,048 tokens - Basic reasoning
    MEDIUM = "medium"      # 8,192 tokens - Standard tasks (default)
    HIGH = "high"          # 16,384 tokens - Complex problems
    MAX = "max"            # 32,768 tokens - Exhaustive reasoning


@dataclass
class ThinkingConfig:
    """Configuration for a thinking mode."""
    mode: ThinkingMode
    token_budget: int
    temperature: float
    description: str
    use_cases: list[str]


# Thinking mode configurations
THINKING_CONFIGS: Dict[ThinkingMode, ThinkingConfig] = {
    ThinkingMode.MINIMAL: ThinkingConfig(
        mode=ThinkingMode.MINIMAL,
        token_budget=128,
        temperature=0.1,
        description="Minimal thinking for simple, straightforward tasks",
        use_cases=[
            "Code formatting",
            "Simple syntax checks",
            "Basic explanations",
            "Quick validations"
        ]
    ),
    ThinkingMode.LOW: ThinkingConfig(
        mode=ThinkingMode.LOW,
        token_budget=2048,
        temperature=0.2,
        description="Low thinking for basic reasoning tasks",
        use_cases=[
            "Simple bug fixes",
            "Basic code reviews",
            "Straightforward refactoring",
            "Documentation updates"
        ]
    ),
    ThinkingMode.MEDIUM: ThinkingConfig(
        mode=ThinkingMode.MEDIUM,
        token_budget=8192,
        temperature=0.3,
        description="Medium thinking for standard development tasks (default)",
        use_cases=[
            "Feature implementation",
            "Code analysis",
            "Architecture decisions",
            "Performance optimization"
        ]
    ),
    ThinkingMode.HIGH: ThinkingConfig(
        mode=ThinkingMode.HIGH,
        token_budget=16384,
        temperature=0.4,
        description="High thinking for complex problems requiring thorough analysis",
        use_cases=[
            "Security audits",
            "Complex debugging",
            "System design",
            "Critical code reviews"
        ]
    ),
    ThinkingMode.MAX: ThinkingConfig(
        mode=ThinkingMode.MAX,
        token_budget=32768,
        temperature=0.5,
        description="Maximum thinking for exhaustive reasoning (default for deep analysis)",
        use_cases=[
            "Architecture overhauls",
            "Critical security analysis",
            "Complex system debugging",
            "Comprehensive code audits"
        ]
    )
}


def parse_thinking_mode(text: str) -> Optional[ThinkingMode]:
    """
    Parse thinking mode from natural language.
    
    Examples:
        "use minimal thinking" -> ThinkingMode.MINIMAL
        "with high thinking mode" -> ThinkingMode.HIGH
        "thinking mode max" -> ThinkingMode.MAX
    """
    text_lower = text.lower()
    
    # Direct mode mentions
    for mode in ThinkingMode:
        if mode.value in text_lower:
            return mode
    
    # Alternative phrasings
    if any(phrase in text_lower for phrase in ["minimum", "simple", "quick"]):
        return ThinkingMode.MINIMAL
    elif any(phrase in text_lower for phrase in ["basic", "standard"]):
        return ThinkingMode.LOW
    elif any(phrase in text_lower for phrase in ["normal", "regular", "default"]):
        return ThinkingMode.MEDIUM
    elif any(phrase in text_lower for phrase in ["deep", "thorough", "comprehensive"]):
        return ThinkingMode.HIGH
    elif any(phrase in text_lower for phrase in ["maximum", "exhaustive", "complete"]):
        return ThinkingMode.MAX
    
    return None


def get_thinking_config(mode: Optional[ThinkingMode] = None) -> ThinkingConfig:
    """Get thinking configuration for a mode (defaults to MEDIUM)."""
    if mode is None:
        mode = ThinkingMode.MEDIUM
    return THINKING_CONFIGS[mode]


def calculate_token_cost_ratio(mode1: ThinkingMode, mode2: ThinkingMode) -> float:
    """Calculate the cost ratio between two thinking modes."""
    config1 = get_thinking_config(mode1)
    config2 = get_thinking_config(mode2)
    return config1.token_budget / config2.token_budget