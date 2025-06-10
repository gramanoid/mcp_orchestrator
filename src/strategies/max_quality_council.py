"""
Max Quality Council orchestration strategy.

This strategy consults multiple expert models in parallel for critical tasks,
synthesizing their responses for optimal quality.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple

from src.strategies.base import BaseOrchestrationStrategy
from src.core.task import Task, TaskAnalysis, TaskType, ComplexityLevel, ImpactLevel
from src.adapters.base import BaseLLMAdapter, LLMResponse


logger = logging.getLogger(__name__)


class MaxQualityCouncilStrategy(BaseOrchestrationStrategy):
    """
    Orchestration strategy that consults multiple LLMs in parallel.
    
    This strategy is designed for maximum quality output by:
    1. Querying multiple expert models in parallel
    2. Using maximum reasoning capabilities for each model
    3. Synthesizing responses using weighted consensus
    4. Refining the final output with the best-performing model
    """
    
    def __init__(self, adapters: Dict[str, BaseLLMAdapter], synthesizer):
        """Initialize with adapters and synthesizer."""
        super().__init__(adapters, synthesizer)
        self.parallel_timeout = 60  # seconds
        
    def should_activate(self, task_analysis: TaskAnalysis) -> bool:
        """
        Determine if this strategy should be used based on task analysis.
        
        This strategy activates for:
        - High complexity tasks
        - Critical bugs or architectural tasks
        - Tasks with major impact
        - Tasks requiring multiple perspectives
        """
        return any([
            task_analysis.complexity.value >= ComplexityLevel.HIGH.value,
            task_analysis.task_type in [TaskType.ARCHITECTURE, TaskType.CRITICAL_BUG, TaskType.DESIGN],
            task_analysis.estimated_impact >= ImpactLevel.MAJOR,
            task_analysis.requires_multiple_perspectives,
            task_analysis.has_architectural_implications
        ])
    
    async def orchestrate(self, task: Task, analysis: TaskAnalysis) -> LLMResponse:
        """
        Execute the Max Quality Council strategy.
        
        Phases:
        1. Parallel consultation with maximum reasoning
        2. Cross-validation and synthesis
        3. Refinement with best performer
        """
        logger.info("Executing Max Quality Council strategy")
        
        # Phase 1: Parallel consultation
        responses = await self._parallel_consultation(task, analysis)
        
        if not responses:
            raise Exception("No responses received from LLM council")
        
        # If only one response (e.g., external models unavailable), return it
        if len(responses) == 1:
            logger.warning("Only one model available for council strategy")
            return responses[0]
        
        # Phase 2: Synthesis
        weights = self._compute_model_weights(task, analysis, responses)
        synthesized_content = self.synthesizer.combine(
            responses,
            strategy="weighted_consensus",
            weights=weights
        )
        
        # Phase 3: Refinement
        best_model = self._select_best_model(responses, weights)
        refined_response = await self._refine_synthesis(
            best_model, 
            synthesized_content, 
            responses, 
            task
        )
        
        # Add strategy metadata
        refined_response.metadata["strategy"] = {
            "name": "max_quality_council",
            "models_consulted": [r.model for r in responses],
            "synthesis_method": "weighted_consensus",
            "refinement_model": best_model.config.model_id
        }
        
        return refined_response
    
    async def _parallel_consultation(self, task: Task, 
                                   analysis: TaskAnalysis) -> List[LLMResponse]:
        """
        Query multiple models in parallel with maximum reasoning.
        
        Args:
            task: The task to process
            analysis: Task analysis results
            
        Returns:
            List of responses from different models
        """
        # Prepare query configurations for each model
        query_configs = []
        
        # Always include Claude Opus with deep reasoning
        if "claude_opus" in self.adapters:
            query_configs.append((
                self.adapters["claude_opus"],
                {"thinking_mode": "deep", "analysis": analysis}
            ))
        
        # Include Gemini for complex edits or polyglot tasks
        if "gemini_pro" in self.adapters:
            query_configs.append((
                self.adapters["gemini_pro"],
                {"thinking_tokens": 32000, "temperature": 0.7, "analysis": analysis}
            ))
        
        # Include GPT-4 as additional perspective
        if "gpt4_fallback" in self.adapters:
            query_configs.append((
                self.adapters["gpt4_fallback"],
                {"temperature": 0.7, "analysis": analysis}
            ))
        
        # Include O3 for architectural tasks
        if "o3_architect" in self.adapters and analysis.task_type in [TaskType.ARCHITECTURE, TaskType.DESIGN]:
            query_configs.append((
                self.adapters["o3_architect"],
                {"reasoning_depth": "maximum", "architect_mode": True, "analysis": analysis}
            ))
        
        # Execute queries in parallel
        logger.info(f"Consulting {len(query_configs)} models in parallel")
        
        tasks = []
        for adapter, params in query_configs:
            tasks.append(self._query_with_timeout(adapter, task, params))
        
        # Gather results with timeout
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out errors
        responses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                model_name = query_configs[i][0].config.model_id
                logger.error(f"Model {model_name} failed: {result}")
            else:
                responses.append(result)
        
        return responses
    
    async def _query_with_timeout(self, adapter: BaseLLMAdapter, task: Task,
                                params: Dict[str, Any]) -> LLMResponse:
        """Query a model with timeout protection."""
        try:
            return await asyncio.wait_for(
                adapter.query(task, **params),
                timeout=self.parallel_timeout
            )
        except asyncio.TimeoutError:
            raise Exception(f"Model {adapter.config.model_id} timed out")
    
    def _should_include_gemini(self, task: Task, analysis: TaskAnalysis) -> bool:
        """Determine if Gemini should be included in the council."""
        # Include for complex edits, refactoring, or multi-language tasks
        return (
            analysis.task_type in [TaskType.COMPLEX_EDIT, TaskType.REFACTORING, 
                                 TaskType.BUG_FIX, TaskType.OPTIMIZATION] or
            len(analysis.languages_detected) > 1 or
            analysis.complexity.value >= ComplexityLevel.HIGH.value
        )
    
    def _should_include_o3(self, task: Task, analysis: TaskAnalysis) -> bool:
        """Determine if O3 should be included in the council."""
        # Include for architectural and design tasks
        return (
            analysis.task_type in [TaskType.ARCHITECTURE, TaskType.DESIGN] or
            analysis.has_architectural_implications or
            "architect" in task.description.lower() or
            "design" in task.description.lower()
        )
    
    def _compute_model_weights(self, task: Task, analysis: TaskAnalysis,
                             responses: List[LLMResponse]) -> Dict[str, float]:
        """
        Compute weights for each model based on task and response quality.
        
        Args:
            task: The original task
            analysis: Task analysis results
            responses: Model responses
            
        Returns:
            Dictionary of model weights
        """
        weights = {}
        
        for response in responses:
            base_weight = 1.0
            
            # Adjust weight based on model expertise
            if "gemini" in response.model.lower() and analysis.task_type in [
                TaskType.COMPLEX_EDIT, TaskType.REFACTORING
            ]:
                base_weight *= 1.3  # Gemini excels at precise edits
            
            elif "o3" in response.model.lower() and analysis.task_type in [
                TaskType.ARCHITECTURE, TaskType.DESIGN
            ]:
                base_weight *= 1.3  # O3 excels at architecture
            
            elif "claude-opus" in response.model.lower():
                base_weight *= 1.2  # Claude Opus general excellence
            
            # Adjust based on response confidence
            if response.confidence_score:
                base_weight *= (0.5 + response.confidence_score * 0.5)
            
            # Adjust based on thinking tokens used
            if response.thinking_tokens_used:
                thinking_ratio = response.thinking_tokens_used / 10000  # Normalize
                base_weight *= (1 + min(thinking_ratio * 0.2, 0.4))  # Up to 40% boost
            
            weights[response.model] = base_weight
        
        # Normalize weights
        total = sum(weights.values())
        if total > 0:
            weights = {k: v/total for k, v in weights.items()}
        
        return weights
    
    def _select_best_model(self, responses: List[LLMResponse],
                          weights: Dict[str, float]) -> BaseLLMAdapter:
        """Select the best model for refinement based on weights and performance."""
        # Find response with highest weight
        best_response = max(responses, key=lambda r: weights.get(r.model, 0))
        
        # Find corresponding adapter
        for name, adapter in self.adapters.items():
            if (name in best_response.model.lower() or 
                best_response.model in str(adapter.config.model_id)):
                return adapter
        
        # Default to Claude Opus
        return self.adapters.get("claude_opus", list(self.adapters.values())[0])
    
    async def _refine_synthesis(self, best_model: BaseLLMAdapter,
                              synthesized_content: str,
                              original_responses: List[LLMResponse],
                              task: Task) -> LLMResponse:
        """
        Refine the synthesized response using the best-performing model.
        
        Args:
            best_model: The model to use for refinement
            synthesized_content: The synthesized content
            original_responses: Original responses from all models
            task: The original task
            
        Returns:
            Refined response
        """
        # Create refinement task
        refinement_prompt = f"""Based on the following synthesized response from multiple AI models, 
please provide a refined, coherent, and comprehensive solution:

Original Task: {task.description}

Synthesized Response:
{synthesized_content}

Please:
1. Ensure all key insights are preserved
2. Improve clarity and structure
3. Resolve any contradictions
4. Add any missing critical details
5. Maintain technical accuracy"""
        
        refinement_task = Task(
            description=refinement_prompt,
            code_context=task.code_context,
            file_paths=task.file_paths,
            user_preferences=task.user_preferences,
            session_context=task.session_context
        )
        
        # Query with high-quality parameters
        refinement_params = best_model.get_max_reasoning_params()
        refinement_params["temperature"] = 0.3  # Lower temperature for refinement
        
        return await best_model.query(refinement_task, **refinement_params)