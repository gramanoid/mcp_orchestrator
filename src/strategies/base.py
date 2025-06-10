"""
Base class for orchestration strategies.

This module defines the interface that all orchestration strategies must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

from src.core.task import Task, TaskAnalysis
from src.adapters.base import BaseLLMAdapter, LLMResponse


class BaseOrchestrationStrategy(ABC):
    """
    Abstract base class for orchestration strategies.
    
    Each strategy implements a different approach to selecting and coordinating
    LLMs based on task requirements.
    """
    
    def __init__(self, adapters: Dict[str, BaseLLMAdapter], synthesizer):
        """
        Initialize the strategy with available adapters.
        
        Args:
            adapters: Dictionary of available LLM adapters
            synthesizer: Response synthesizer for combining outputs
        """
        self.adapters = adapters
        self.synthesizer = synthesizer
    
    @abstractmethod
    async def orchestrate(self, task: Task, analysis: TaskAnalysis) -> LLMResponse:
        """
        Execute the orchestration strategy for a given task.
        
        Args:
            task: The task to process
            analysis: Task analysis results
            
        Returns:
            Orchestrated response from one or more LLMs
        """
        pass
    
    @abstractmethod
    def should_activate(self, task_analysis: TaskAnalysis) -> bool:
        """
        Determine if this strategy should be activated for the given task.
        
        Args:
            task_analysis: Analysis of the task
            
        Returns:
            True if this strategy is appropriate for the task
        """
        pass
    
    def compute_weights(self, task: Task) -> Dict[str, float]:
        """
        Compute weights for different models based on task characteristics.
        
        Args:
            task: The task being processed
            
        Returns:
            Dictionary mapping model names to weights
        """
        # Default equal weights
        return {name: 1.0 for name in self.adapters.keys()}
    
    def select_best_for_refinement(self, responses: List[LLMResponse], 
                                  task: Task) -> BaseLLMAdapter:
        """
        Select the best model for refining a synthesized response.
        
        Args:
            responses: List of initial responses
            task: The original task
            
        Returns:
            The adapter best suited for refinement
        """
        # Default to the model with highest confidence
        best_response = max(responses, key=lambda r: r.confidence_score or 0.7)
        
        # Find the corresponding adapter
        for name, adapter in self.adapters.items():
            if name in best_response.model.lower() or best_response.model in str(adapter.config.model_id):
                return adapter
        
        # Fallback to Claude Opus
        return self.adapters.get("claude_opus", list(self.adapters.values())[0])
    
    def is_sufficient(self, response: LLMResponse, task: Task) -> bool:
        """
        Determine if a response is sufficient for the given task.
        
        Args:
            response: The LLM response to evaluate
            task: The original task
            
        Returns:
            True if the response adequately addresses the task
        """
        # Basic sufficiency checks
        if not response.content or len(response.content) < 50:
            return False
        
        # Check confidence if available
        if response.confidence_score and response.confidence_score < 0.6:
            return False
        
        # Check for error indicators
        error_indicators = ["I cannot", "I'm unable", "error occurred", "failed to"]
        content_lower = response.content.lower()
        if any(indicator in content_lower for indicator in error_indicators):
            return False
        
        # Task-specific checks
        if "implement" in task.description.lower() and "```" not in response.content:
            return False  # Implementation tasks should include code
        
        return True
    
    def needs_specialized_expertise(self, response: LLMResponse, task: Task) -> bool:
        """
        Determine if a task needs specialized expertise from external models.
        
        Args:
            response: Initial response to evaluate
            task: The original task
            
        Returns:
            True if specialized expertise would be beneficial
        """
        # Check for complexity indicators in the response
        complexity_indicators = [
            "complex", "challenging", "difficult", "intricate",
            "multiple approaches", "trade-offs", "considerations"
        ]
        
        content_lower = response.content.lower()
        complexity_count = sum(1 for indicator in complexity_indicators 
                             if indicator in content_lower)
        
        if complexity_count >= 2:
            return True
        
        # Check for uncertainty
        uncertainty_indicators = [
            "might", "could", "possibly", "perhaps", "depending on",
            "it depends", "unclear", "ambiguous"
        ]
        
        uncertainty_count = sum(1 for indicator in uncertainty_indicators 
                              if indicator in content_lower)
        
        if uncertainty_count >= 3:
            return True
        
        # Check task keywords
        specialized_keywords = [
            "architecture", "design pattern", "optimization", "performance",
            "scalability", "refactor", "migrate", "integrate"
        ]
        
        task_lower = task.description.lower()
        if any(keyword in task_lower for keyword in specialized_keywords):
            return True
        
        return False