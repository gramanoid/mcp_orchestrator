"""
Progressive Deep Dive orchestration strategy.

This strategy starts with efficient internal models and progressively engages
more powerful external models as needed.
"""

import logging
from typing import Dict, Optional, Any, List

from src.strategies.base import BaseOrchestrationStrategy
from src.core.task import Task, TaskAnalysis, TaskType, ComplexityLevel
from src.adapters.base import BaseLLMAdapter, LLMResponse


logger = logging.getLogger(__name__)


class ProgressiveDeepDiveStrategy(BaseOrchestrationStrategy):
    """
    Orchestration strategy that progressively engages more powerful models.
    
    This strategy is designed for efficiency by:
    1. Starting with fast internal models
    2. Evaluating response quality
    3. Escalating to more powerful models only when needed
    4. Synthesizing insights when multiple models are used
    """
    
    def __init__(self, adapters: Dict[str, BaseLLMAdapter], synthesizer):
        """Initialize with adapters and synthesizer."""
        super().__init__(adapters, synthesizer)
        self.escalation_threshold = 0.6  # Quality threshold for escalation
        
    def should_activate(self, task_analysis: TaskAnalysis) -> bool:
        """
        Determine if this strategy should be used.
        
        This is the default strategy for most tasks, especially:
        - Low to medium complexity tasks
        - Tasks without critical impact
        - Tasks that don't require multiple perspectives
        """
        # This is the default strategy, so it can handle any task
        # but is especially suited for simpler tasks
        return (
            task_analysis.complexity <= ComplexityLevel.MEDIUM or
            not task_analysis.requires_multiple_perspectives
        )
    
    async def orchestrate(self, task: Task, analysis: TaskAnalysis) -> LLMResponse:
        """
        Execute the Progressive Deep Dive strategy.
        
        Stages:
        1. Quick assessment with Claude Sonnet
        2. Deep analysis with Claude Opus if needed
        3. Specialized expertise from external models if required
        """
        logger.info("Executing Progressive Deep Dive strategy")
        
        # Stage 1: Quick assessment
        if "claude_sonnet" in self.adapters:
            initial_response = await self._stage1_quick_assessment(task, analysis)
            
            if self.is_sufficient(initial_response, task):
                logger.info("Stage 1 response sufficient, returning early")
                initial_response.metadata["strategy"] = {
                    "name": "progressive_deep_dive",
                    "stages_used": 1,
                    "final_model": "claude_sonnet"
                }
                return initial_response
        else:
            initial_response = None
        
        # Stage 2: Deep analysis with Claude Opus
        opus_response = await self._stage2_deep_analysis(task, analysis, initial_response)
        
        if not self.needs_specialized_expertise(opus_response, task):
            logger.info("Stage 2 response sufficient, no external models needed")
            opus_response.metadata["strategy"] = {
                "name": "progressive_deep_dive",
                "stages_used": 2,
                "final_model": "claude_opus"
            }
            return opus_response
        
        # Stage 3: Engage specialized external models
        final_response = await self._stage3_specialized_expertise(
            task, analysis, opus_response
        )
        
        final_response.metadata["strategy"] = {
            "name": "progressive_deep_dive",
            "stages_used": 3,
            "models_used": self._get_models_used(initial_response, opus_response, final_response)
        }
        
        return final_response
    
    async def _stage1_quick_assessment(self, task: Task, 
                                     analysis: TaskAnalysis) -> LLMResponse:
        """
        Stage 1: Quick assessment with Claude Sonnet.
        
        Args:
            task: The task to process
            analysis: Task analysis results
            
        Returns:
            Initial response from Claude Sonnet
        """
        logger.info("Stage 1: Quick assessment with Claude Sonnet")
        
        sonnet = self.adapters["claude_sonnet"]
        
        # Use fast mode for initial assessment
        params = {
            "thinking_mode": "fast",
            "max_tokens": 4096,
            "temperature": 0.5,
            "analysis": analysis
        }
        
        return await sonnet.query(task, **params)
    
    async def _stage2_deep_analysis(self, task: Task, analysis: TaskAnalysis,
                                   initial_response: Optional[LLMResponse]) -> LLMResponse:
        """
        Stage 2: Deep analysis with Claude Opus.
        
        Args:
            task: The task to process
            analysis: Task analysis results
            initial_response: Response from stage 1 (if any)
            
        Returns:
            Response from Claude Opus
        """
        logger.info("Stage 2: Deep analysis with Claude Opus")
        
        if "claude_opus" not in self.adapters:
            # Fallback to initial response or raise error
            if initial_response:
                return initial_response
            raise Exception("Claude Opus not available and no initial response")
        
        opus = self.adapters["claude_opus"]
        
        # Prepare enhanced task if we have initial response
        if initial_response:
            enhanced_task = self._enhance_task_with_initial_insights(
                task, initial_response
            )
        else:
            enhanced_task = task
        
        # Use deep reasoning mode
        params = {
            "thinking_mode": "deep",
            "max_tokens": 8192,
            "temperature": 0.7,
            "analysis": analysis
        }
        
        return await opus.query(enhanced_task, **params)
    
    async def _stage3_specialized_expertise(self, task: Task, analysis: TaskAnalysis,
                                          opus_response: LLMResponse) -> LLMResponse:
        """
        Stage 3: Engage specialized external models.
        
        Args:
            task: The task to process
            analysis: Task analysis results
            opus_response: Response from Claude Opus
            
        Returns:
            Final response, potentially synthesized from multiple models
        """
        logger.info("Stage 3: Engaging specialized external models")
        
        # Determine which specialist to engage
        specialist_response = None
        
        if self._needs_code_edit_specialist(task, analysis):
            specialist_response = await self._query_gemini_specialist(task, analysis, opus_response)
        elif self._needs_architecture_specialist(task, analysis):
            specialist_response = await self._query_o3_specialist(task, analysis, opus_response)
        
        if not specialist_response:
            # No specialist available or needed
            return opus_response
        
        # Synthesize internal and external insights
        return await self._synthesize_progressive_insights(
            opus_response, specialist_response, task
        )
    
    def _enhance_task_with_initial_insights(self, task: Task, 
                                          initial_response: LLMResponse) -> Task:
        """
        Enhance the task description with insights from initial response.
        
        Args:
            task: Original task
            initial_response: Initial response to incorporate
            
        Returns:
            Enhanced task
        """
        enhanced_description = f"""{task.description}

Initial Analysis:
{initial_response.content[:500]}...

Please provide a more comprehensive and detailed solution, addressing any limitations or areas that need deeper exploration."""
        
        return Task(
            description=enhanced_description,
            code_context=task.code_context,
            file_paths=task.file_paths,
            user_preferences=task.user_preferences,
            session_context=task.session_context
        )
    
    def _needs_code_edit_specialist(self, task: Task, analysis: TaskAnalysis) -> bool:
        """Determine if Gemini code edit specialist is needed."""
        if "gemini_polyglot" not in self.adapters:
            return False
        
        return (
            analysis.task_type in [TaskType.COMPLEX_EDIT, TaskType.REFACTORING,
                                 TaskType.BUG_FIX, TaskType.OPTIMIZATION] and
            (analysis.complexity.value >= ComplexityLevel.HIGH.value or
             len(analysis.languages_detected) > 1 or
             analysis.estimated_lines_affected > 100)
        )
    
    def _needs_architecture_specialist(self, task: Task, analysis: TaskAnalysis) -> bool:
        """Determine if O3 architecture specialist is needed."""
        if "o3_architect" not in self.adapters:
            return False
        
        return (
            analysis.task_type in [TaskType.ARCHITECTURE, TaskType.DESIGN] or
            analysis.has_architectural_implications or
            any(keyword in task.description.lower() 
                for keyword in ["architecture", "design", "structure", "pattern"])
        )
    
    async def _query_gemini_specialist(self, task: Task, analysis: TaskAnalysis,
                                     opus_response: LLMResponse) -> LLMResponse:
        """Query Gemini for specialized code editing expertise."""
        logger.info("Querying Gemini specialist for code editing")
        
        gemini = self.adapters["gemini_polyglot"]
        
        # Enhance task with Opus insights
        specialist_task = Task(
            description=f"""{task.description}

Current approach:
{self._extract_key_points(opus_response.content)}

Please provide precise code modifications using diff-fenced format where applicable.""",
            code_context=task.code_context,
            file_paths=task.file_paths,
            user_preferences=task.user_preferences,
            session_context=task.session_context
        )
        
        params = {
            "thinking_tokens": 32000,  # Maximum thinking
            "edit_format": "diff-fenced",
            "temperature": 0.5,
            "analysis": analysis
        }
        
        return await gemini.query(specialist_task, **params)
    
    async def _query_o3_specialist(self, task: Task, analysis: TaskAnalysis,
                                 opus_response: LLMResponse) -> LLMResponse:
        """Query O3 for specialized architectural expertise."""
        logger.info("Querying O3 specialist for architectural design")
        
        o3 = self.adapters["o3_architect"]
        
        # Enhance task with Opus insights
        specialist_task = Task(
            description=f"""{task.description}

Initial technical approach:
{self._extract_key_points(opus_response.content)}

Please provide a comprehensive architectural design with clear component structure and interfaces.""",
            code_context=task.code_context,
            file_paths=task.file_paths,
            user_preferences=task.user_preferences,
            session_context=task.session_context
        )
        
        params = {
            "reasoning_depth": "maximum",
            "architect_mode": True,
            "output_format": "architect",
            "temperature": 0.5,
            "analysis": analysis
        }
        
        return await o3.query(specialist_task, **params)
    
    async def _synthesize_progressive_insights(self, internal_response: LLMResponse,
                                             specialist_response: LLMResponse,
                                             task: Task) -> LLMResponse:
        """
        Synthesize insights from internal and specialist models.
        
        Args:
            internal_response: Response from Claude Opus
            specialist_response: Response from specialist model
            task: Original task
            
        Returns:
            Synthesized response
        """
        logger.info("Synthesizing progressive insights")
        
        # Use the synthesizer to merge responses
        synthesized_content = self.synthesizer.combine(
            [internal_response, specialist_response],
            strategy="merge"
        )
        
        # Create a synthesized response object
        return LLMResponse(
            content=synthesized_content,
            model=f"{internal_response.model} + {specialist_response.model}",
            thinking_tokens_used=(internal_response.thinking_tokens_used or 0) + 
                               (specialist_response.thinking_tokens_used or 0),
            completion_tokens=(internal_response.completion_tokens or 0) + 
                            (specialist_response.completion_tokens or 0),
            total_tokens=(internal_response.total_tokens or 0) + 
                        (specialist_response.total_tokens or 0),
            cost=(internal_response.cost or 0) + (specialist_response.cost or 0),
            confidence_score=max(
                internal_response.confidence_score or 0.7,
                specialist_response.confidence_score or 0.7
            ),
            metadata={
                "synthesis": True,
                "models_involved": [internal_response.model, specialist_response.model],
                "internal_metadata": internal_response.metadata,
                "specialist_metadata": specialist_response.metadata
            }
        )
    
    def _extract_key_points(self, content: str, max_length: int = 500) -> str:
        """Extract key points from response content."""
        # Find the most relevant section
        sections = content.split('\n\n')
        
        # Prioritize sections with implementation details
        for section in sections:
            if any(keyword in section.lower() 
                   for keyword in ["implementation", "approach", "solution", "code"]):
                return section[:max_length] + "..." if len(section) > max_length else section
        
        # Default to first substantial section
        for section in sections:
            if len(section) > 100:
                return section[:max_length] + "..." if len(section) > max_length else section
        
        # Fallback to beginning
        return content[:max_length] + "..." if len(content) > max_length else content
    
    def _get_models_used(self, initial: Optional[LLMResponse], 
                        opus: LLMResponse, 
                        final: LLMResponse) -> List[str]:
        """Get list of all models used in the progressive strategy."""
        models = []
        
        if initial:
            models.append(initial.model)
        
        models.append(opus.model)
        
        # Check if final is different from opus (specialist was used)
        if final.model != opus.model:
            if " + " in final.model:
                # Synthesized response
                models.extend(final.model.split(" + "))
            else:
                models.append(final.model)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_models = []
        for model in models:
            if model not in seen:
                seen.add(model)
                unique_models.append(model)
        
        return unique_models