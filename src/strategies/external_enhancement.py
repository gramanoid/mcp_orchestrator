"""
External Enhancement Strategy - Uses only external models (Gemini, O3).

This strategy gets perspectives from external models to enhance Claude's responses.
"""

import logging
from typing import Dict, Optional, Any, List

from src.strategies.base import BaseOrchestrationStrategy
from src.core.task import Task, TaskAnalysis, TaskType, ComplexityLevel
from src.adapters.base import BaseLLMAdapter, LLMResponse


logger = logging.getLogger(__name__)


class ExternalEnhancementStrategy(BaseOrchestrationStrategy):
    """
    Strategy that uses only external models (Gemini, O3) to enhance Claude's responses.
    
    Since the user is already talking to Claude, this strategy:
    1. Sends the task to Gemini 2.5 Pro for additional perspective
    2. Optionally sends to O3 for architecture/system design insights
    3. Synthesizes the external perspectives
    """
    
    def __init__(self, adapters: Dict[str, BaseLLMAdapter], synthesizer):
        """Initialize with external adapters only."""
        super().__init__(adapters, synthesizer)
        
    def should_activate(self, task_analysis: TaskAnalysis) -> bool:
        """This is the default strategy for all MCP tool requests."""
        return True
    
    async def orchestrate(self, task: Task, analysis: TaskAnalysis) -> LLMResponse:
        """
        Get external model perspectives on the task.
        
        Flow:
        1. Always use Gemini 2.5 Pro for general analysis
        2. Add O3 for architecture/system design tasks
        3. Return synthesized external perspectives
        """
        logger.info("Getting external model perspectives")
        
        responses = []
        models_used = []
        
        # Always use Gemini for its large context and different perspective
        if "gemini_pro" in self.adapters:
            logger.info("Getting Gemini 2.5 Pro perspective")
            gemini_response = await self.adapters["gemini_pro"].query(task)
            responses.append(gemini_response)
            models_used.append("google/gemini-2.5-pro-preview")
        
        # Use O3 for architecture, system design, or complex reasoning
        should_use_o3 = (
            analysis.task_type == TaskType.ARCHITECTURE or
            analysis.complexity.value >= ComplexityLevel.HIGH.value or
            "architecture" in task.description.lower() or
            "design" in task.description.lower() or
            "system" in task.description.lower() or
            "decision" in task.description.lower()
        )
        
        if should_use_o3 and "o3_architect" in self.adapters:
            logger.info("Getting O3 perspective for architecture/design insights")
            o3_response = await self.adapters["o3_architect"].query(task)
            responses.append(o3_response)
            models_used.append("o3-mini")
        
        # If we have multiple responses, synthesize them
        if len(responses) > 1:
            logger.info(f"Synthesizing {len(responses)} external perspectives")
            final_response = self.synthesizer.synthesize(responses)
            final_response.metadata["models_used"] = models_used
            final_response.metadata["strategy"] = "external_enhancement"
        elif responses:
            # Single response - just return it
            final_response = responses[0]
            final_response.metadata["models_used"] = models_used
            final_response.metadata["strategy"] = "external_enhancement"
        else:
            # No external models available
            logger.warning("No external models available")
            return LLMResponse(
                content="External models (Gemini, O3) are not available. Please check API keys.",
                model="none",
                total_tokens=0,
                cost=0.0,
                metadata={
                    "error": "no_external_models",
                    "strategy": "external_enhancement"
                }
            )
        
        return final_response
    
    def is_sufficient(self, response: LLMResponse, task: Task) -> bool:
        """External responses are always returned as-is."""
        return True
    
    def needs_specialized_expertise(self, response: LLMResponse, task: Task) -> bool:
        """Not used in this strategy."""
        return False
    
    def _get_models_used(self, *responses) -> List[str]:
        """Extract unique models used."""
        models = []
        for response in responses:
            if response and response.model not in models:
                models.append(response.model)
        return models