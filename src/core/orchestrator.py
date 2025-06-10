"""
Core orchestrator module for the Multi-Code-LLM Orchestrator.

This module implements the main orchestration logic that coordinates between
different LLMs based on task requirements and selected strategies.
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from src.core.task import Task, TaskAnalyzer, TaskAnalysis, TaskType, ComplexityLevel
from src.core.thinking_modes import ThinkingMode, get_thinking_config, parse_thinking_mode
from src.core.dynamic_context import DynamicContextManager, ToolResponse, RequestStatus
from src.adapters.base import BaseLLMAdapter, LLMResponse, LLMConfig
from src.adapters.claude_adapter import ClaudeAdapter
from src.adapters.claude_direct import ClaudeDirectAdapter
from src.adapters.gemini_adapter import GeminiAdapter
from src.adapters.o3_adapter import O3Adapter
from src.adapters.openrouter_adapter import OpenRouterAdapter
from src.strategies.base import BaseOrchestrationStrategy
from src.strategies.max_quality_council import MaxQualityCouncilStrategy
from src.strategies.progressive_deep_dive import ProgressiveDeepDiveStrategy
from src.prompts import tool_prompts
from src.prompts.model_specific_prompts import get_model_prompt, suggest_model_for_task


logger = logging.getLogger(__name__)


class ResponseSynthesizer:
    """
    Synthesizes responses from multiple LLMs into a coherent output.
    """
    
    def combine(self, responses: List[LLMResponse], strategy: str = "weighted_consensus",
                weights: Optional[Dict[str, float]] = None) -> str:
        """
        Combine multiple LLM responses using the specified strategy.
        
        Args:
            responses: List of LLM responses to combine
            strategy: Combination strategy to use
            weights: Optional weights for each model
            
        Returns:
            Combined response content
        """
        if not responses:
            return ""
        
        if len(responses) == 1:
            return responses[0].content
        
        if strategy == "weighted_consensus":
            return self._weighted_consensus(responses, weights)
        elif strategy == "best_of":
            return self._best_of(responses)
        elif strategy == "merge":
            return self._merge_responses(responses)
        else:
            # Default to first response
            return responses[0].content
    
    def _weighted_consensus(self, responses: List[LLMResponse], 
                          weights: Optional[Dict[str, float]] = None) -> str:
        """Combine responses using weighted consensus."""
        if not weights:
            # Default weights based on confidence scores
            weights = {}
            for resp in responses:
                confidence = resp.confidence_score or 0.7
                weights[resp.model] = confidence
        
        # For now, return the response with highest weight
        # In a more sophisticated implementation, we would analyze and merge content
        best_response = max(responses, key=lambda r: weights.get(r.model, 0.5))
        
        # Add synthesis metadata
        synthesis_note = "\n\n---\n*Synthesized from multiple models with weighted consensus*"
        
        return best_response.content + synthesis_note
    
    def _best_of(self, responses: List[LLMResponse]) -> str:
        """Select the best response based on quality metrics."""
        # Score each response
        scored_responses = []
        for resp in responses:
            score = self._score_response(resp)
            scored_responses.append((score, resp))
        
        # Return highest scoring response
        best_response = max(scored_responses, key=lambda x: x[0])[1]
        return best_response.content
    
    def _merge_responses(self, responses: List[LLMResponse]) -> str:
        """Merge insights from multiple responses."""
        # Extract key sections from each response
        merged_sections = {
            "overview": [],
            "implementation": [],
            "considerations": [],
            "alternatives": []
        }
        
        for resp in responses:
            sections = self._extract_sections(resp.content)
            for key, content in sections.items():
                if content and key in merged_sections:
                    merged_sections[key].append(content)
        
        # Build merged response
        merged_content = []
        
        if merged_sections["overview"]:
            merged_content.append("## Overview")
            merged_content.append(self._deduplicate_content(merged_sections["overview"]))
        
        if merged_sections["implementation"]:
            merged_content.append("\n## Implementation")
            merged_content.append(self._deduplicate_content(merged_sections["implementation"]))
        
        if merged_sections["considerations"]:
            merged_content.append("\n## Considerations")
            for consideration in set(merged_sections["considerations"]):
                merged_content.append(f"- {consideration}")
        
        if merged_sections["alternatives"]:
            merged_content.append("\n## Alternatives")
            merged_content.append(self._deduplicate_content(merged_sections["alternatives"]))
        
        return "\n".join(merged_content)
    
    def _score_response(self, response: LLMResponse) -> float:
        """Score a response based on various quality metrics."""
        score = 0.0
        
        # Base score from confidence
        score += (response.confidence_score or 0.7) * 0.4
        
        # Content length (moderate length preferred)
        content_length = len(response.content)
        if 500 <= content_length <= 5000:
            score += 0.2
        elif content_length > 5000:
            score += 0.1
        
        # Structure indicators
        if "```" in response.content:  # Code blocks
            score += 0.1
        if any(marker in response.content for marker in ["##", "**", "1.", "- "]):
            score += 0.1  # Formatted content
        
        # Model-specific bonuses
        model_bonuses = {
            "o3": 0.1,  # Architecture expertise
            "gemini": 0.1,  # Code precision
            "claude-opus": 0.1  # General excellence
        }
        
        for model_key, bonus in model_bonuses.items():
            if model_key in response.model.lower():
                score += bonus
                break
        
        return min(score, 1.0)
    
    def _extract_sections(self, content: str) -> Dict[str, str]:
        """Extract logical sections from response content."""
        sections = {
            "overview": "",
            "implementation": "",
            "considerations": "",
            "alternatives": ""
        }
        
        # Simple section detection
        lines = content.split('\n')
        current_section = "overview"
        current_content = []
        
        for line in lines:
            line_lower = line.lower()
            
            # Detect section changes
            if any(keyword in line_lower for keyword in ["implementation", "code", "solution"]):
                sections[current_section] = '\n'.join(current_content)
                current_section = "implementation"
                current_content = []
            elif any(keyword in line_lower for keyword in ["consideration", "note", "important"]):
                sections[current_section] = '\n'.join(current_content)
                current_section = "considerations"
                current_content = []
            elif any(keyword in line_lower for keyword in ["alternative", "other", "option"]):
                sections[current_section] = '\n'.join(current_content)
                current_section = "alternatives"
                current_content = []
            else:
                current_content.append(line)
        
        # Save last section
        sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def _deduplicate_content(self, contents: List[str]) -> str:
        """Remove duplicate content while preserving unique insights."""
        # Simple deduplication - in practice, this would be more sophisticated
        unique_contents = []
        seen_hashes = set()
        
        for content in contents:
            content_hash = hash(content.strip().lower())
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_contents.append(content)
        
        return "\n\n".join(unique_contents)


class MCPOrchestrator:
    """
    Main orchestrator that coordinates between different LLMs.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the orchestrator with configuration.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.task_analyzer = TaskAnalyzer()
        self.synthesizer = ResponseSynthesizer()
        
        # Initialize adapters
        self.adapters: Dict[str, BaseLLMAdapter] = {}
        self._initialize_adapters()
        
        # Initialize strategies
        self.strategies: Dict[str, BaseOrchestrationStrategy] = {
            "max_quality_council": MaxQualityCouncilStrategy(self.adapters, self.synthesizer),
            "progressive_deep_dive": ProgressiveDeepDiveStrategy(self.adapters, self.synthesizer)
        }
        
        self.default_strategy = config.get("orchestration", {}).get("default_strategy", "progressive_deep_dive")
        
        # Statistics
        self._request_count = 0
        self._total_cost = 0.0
        self._start_time = datetime.utcnow()
    
    def _initialize_adapters(self):
        """Initialize all LLM adapters."""
        # Claude direct adapter - uses actual Claude instance
        self.adapters["claude_direct"] = ClaudeDirectAdapter()
        
        # Keep legacy adapters for compatibility
        self.adapters["claude_opus"] = self.adapters["claude_direct"]  # Alias
        self.adapters["claude_sonnet"] = self.adapters["claude_direct"]  # Alias
        
        # External adapters via OpenRouter
        openrouter_key = self.config.get("api_keys", {}).get("openrouter")
        
        if openrouter_key:
            # Import OpenRouter adapter
            from src.adapters.openrouter_adapter import OpenRouterAdapter
            
            # Gemini 2.5 Pro adapter - MAX PERFORMANCE
            gemini_config = LLMConfig(
                model_id="google/gemini-2.5-pro-preview",
                api_key=openrouter_key,
                max_tokens=32768,  # Maximum output for Gemini
                temperature=0.1    # Very low temperature for maximum precision
            )
            self.adapters["gemini_pro"] = OpenRouterAdapter(gemini_config)
            
            # o3 via OpenAI (requires separate API key)
            openai_key = os.getenv('OPENAI_API_KEY')
            if openai_key:
                # O3 is initialized with its own configuration in O3Adapter
                self.adapters["o3_architect"] = O3Adapter()
                logger.info("O3 model configured via OpenAI")
        else:
            logger.warning("OpenRouter API key not found. External models unavailable.")
    
    async def orchestrate(self, task: Task, strategy_override: Optional[str] = None) -> LLMResponse:
        """
        Orchestrate a task using the appropriate strategy and LLMs.
        
        Now with:
        - Thinking mode support for token budget control
        - Dynamic context requests for collaborative problem-solving
        - Specialized prompts based on task type
        
        Args:
            task: The task to process
            strategy_override: Optional strategy to use instead of default
            
        Returns:
            Orchestrated response
        """
        try:
            # Parse thinking mode from task description
            thinking_mode = parse_thinking_mode(task.description)
            if not thinking_mode:
                # Default based on task complexity
                thinking_mode = self._get_default_thinking_mode(task)
            
            thinking_config = get_thinking_config(thinking_mode)
            logger.info(f"Using thinking mode: {thinking_mode.value} ({thinking_config.token_budget} tokens)")
            
            # Analyze task
            analysis = self.task_analyzer.analyze(task)
            
            # Apply specialized prompt based on task type
            task = self._apply_specialized_prompt(task, analysis)
            
            # Initialize dynamic context manager
            context_manager = DynamicContextManager()
            
            # Select strategy
            strategy_name = strategy_override or self._select_strategy(task, analysis)
            strategy = self.strategies.get(strategy_name, self.strategies[self.default_strategy])
            
            logger.info(f"Orchestrating task with strategy: {strategy_name}")
            
            # Check cost limits with thinking mode consideration
            if not self._check_cost_limits(thinking_config):
                raise Exception("Cost limit exceeded")
            
            # Configure adapters with thinking mode
            self._configure_adapters_for_thinking(thinking_config)
            
            # Execute orchestration with dynamic context support
            response = await self._orchestrate_with_context(
                strategy, task, analysis, context_manager, thinking_config
            )
            
            # Update statistics
            self._request_count += 1
            if response.cost:
                self._total_cost += response.cost
            
            # Add orchestration metadata
            response.metadata["orchestration"] = {
                "strategy": strategy_name,
                "thinking_mode": thinking_mode.value,
                "token_budget": thinking_config.token_budget,
                "analysis": {
                    "task_type": analysis.task_type.name,
                    "complexity": analysis.complexity.name,
                    "confidence": analysis.confidence_score
                },
                "dynamic_context_requests": len(context_manager.context_history)
            }
            
            # Add usage summary to response
            response = self._add_usage_summary(response)
            
            return response
            
        except Exception as e:
            logger.error(f"Orchestration failed: {e}")
            raise
    
    def _select_strategy(self, task: Task, analysis: TaskAnalysis) -> str:
        """Select the appropriate orchestration strategy."""
        # Check user preferences
        if task.user_preferences.get("quality_mode") == "maximum":
            return "max_quality_council"
        
        if task.user_preferences.get("strategy"):
            return task.user_preferences["strategy"]
        
        # Auto-select based on analysis
        if (analysis.complexity.value >= 4 or
            analysis.requires_multiple_perspectives or
            analysis.task_type in [TaskType.ARCHITECTURE, TaskType.CRITICAL_BUG]):
            return "max_quality_council"
        
        return "progressive_deep_dive"
    
    def _get_default_thinking_mode(self, task: Task) -> ThinkingMode:
        """Get default thinking mode based on task characteristics."""
        # Extract complexity from task context
        complexity = task.session_context.get("complexity", ComplexityLevel.MEDIUM)
        
        if isinstance(complexity, str):
            # Convert string to enum if needed
            complexity = ComplexityLevel[complexity.upper()]
        
        # Map complexity to thinking mode
        if complexity == ComplexityLevel.TRIVIAL:
            return ThinkingMode.MINIMAL
        elif complexity == ComplexityLevel.LOW:
            return ThinkingMode.LOW
        elif complexity == ComplexityLevel.MEDIUM:
            return ThinkingMode.MEDIUM
        elif complexity == ComplexityLevel.HIGH:
            return ThinkingMode.HIGH
        else:  # VERY_HIGH
            return ThinkingMode.MAX
    
    def _apply_specialized_prompt(self, task: Task, analysis: TaskAnalysis) -> Task:
        """Apply specialized prompt based on task type."""
        prompt_map = {
            TaskType.CODE_GENERATION: tool_prompts.ANALYZE_PROMPT,
            TaskType.CODE_REVIEW: tool_prompts.REVIEW_CODE_PROMPT,
            TaskType.BUG_FIX: tool_prompts.DEBUG_ISSUE_PROMPT,
            TaskType.CRITICAL_BUG: tool_prompts.DEBUG_ISSUE_PROMPT,
            TaskType.ARCHITECTURE: tool_prompts.THINK_DEEPER_PROMPT,
            TaskType.DESIGN: tool_prompts.THINK_DEEPER_PROMPT,
            TaskType.EXPLANATION: tool_prompts.CHAT_PROMPT,
            TaskType.DOCUMENTATION: tool_prompts.CHAT_PROMPT
        }
        
        specialized_prompt = prompt_map.get(analysis.task_type, tool_prompts.CHAT_PROMPT)
        
        # Add prompt to task context
        task.session_context["system_prompt"] = specialized_prompt
        task.session_context["task_type"] = analysis.task_type.name
        
        return task
    
    def _configure_adapters_for_thinking(self, thinking_config):
        """Configure all adapters with thinking mode settings."""
        for adapter in self.adapters.values():
            # Update temperature
            adapter.config.temperature = thinking_config.temperature
            # Update max tokens based on thinking budget
            adapter.config.max_tokens = min(
                thinking_config.token_budget,
                adapter.config.max_tokens
            )
    
    async def _orchestrate_with_context(
        self,
        strategy: BaseOrchestrationStrategy,
        task: Task,
        analysis: TaskAnalysis,
        context_manager: DynamicContextManager,
        thinking_config
    ) -> LLMResponse:
        """Execute orchestration with dynamic context support."""
        max_iterations = 3  # Prevent infinite context loops
        iteration = 0
        
        while iteration < max_iterations:
            # Execute strategy
            response = await strategy.orchestrate(task, analysis)
            
            # Parse response for clarification requests
            tool_response = context_manager.parse_llm_response(response.content)
            
            if tool_response.status == RequestStatus.REQUIRES_CLARIFICATION:
                # Handle clarification request
                clarification = tool_response.clarification_request
                logger.info(f"Clarification requested: {clarification.question}")
                
                # Add requested context to task
                if clarification.files_needed:
                    task.code_context = await self._gather_files_context(clarification.files_needed)
                
                # Add clarification to context
                context_manager.add_request(clarification)
                
                # Update task with clarification context
                task.session_context["clarification_history"] = context_manager.context_history
                
                iteration += 1
            else:
                # Success - return response
                return response
        
        # Max iterations reached
        logger.warning("Max clarification iterations reached")
        return response
    
    async def _gather_files_context(self, files_needed: List[str]) -> str:
        """Gather context from requested files."""
        # This would integrate with file reading tools
        # For now, return placeholder
        return f"[Context from files: {', '.join(files_needed)}]"
    
    def _add_usage_summary(self, response: LLMResponse) -> LLMResponse:
        """Add usage summary line to the response."""
        # Extract model usage from metadata
        strategy = response.metadata.get("orchestration", {}).get("strategy", "unknown")
        models_used = response.metadata.get("strategy", {}).get("models_consulted", [])
        
        # Create usage summary
        if not models_used:
            # For progressive strategy, determine which model was used
            if hasattr(response, 'model'):
                models_used = [response.model]
            else:
                models_used = ["claude"]
        
        # Format the summary line
        model_list = ", ".join(models_used) if models_used else "claude"
        cost_str = f"${response.cost:.4f}" if response.cost > 0 else "$0.00"
        
        usage_summary = f"\n\n---\n🤖 Models: {model_list} | 💰 Cost: {cost_str} | 📊 Strategy: {strategy}"
        
        # Add to response content
        response.content += usage_summary
        
        return response
    
    def _check_cost_limits(self, thinking_config=None) -> bool:
        """Check if we're within cost limits."""
        max_cost = self.config.get("cost_management", {}).get("max_cost_per_request", 5.0)
        daily_limit = self.config.get("cost_management", {}).get("daily_limit", 100.0)
        
        # Adjust limits based on thinking mode
        if thinking_config:
            # Higher thinking modes allow higher costs
            mode_multiplier = thinking_config.token_budget / 8192  # Relative to default
            max_cost *= mode_multiplier
        
        # Check daily limit
        if self._total_cost >= daily_limit:
            logger.error(f"Daily cost limit reached: ${self._total_cost:.2f}")
            return False
        
        # Warn if approaching limit
        warning_threshold = self.config.get("cost_management", {}).get("warning_threshold", 0.8)
        if self._total_cost >= daily_limit * warning_threshold:
            logger.warning(f"Approaching daily cost limit: ${self._total_cost:.2f} / ${daily_limit:.2f}")
        
        return True
    
    def get_adapter(self, model_name: str) -> Optional[BaseLLMAdapter]:
        """Get a specific adapter by name."""
        return self.adapters.get(model_name)
    
    async def initialize(self):
        """Initialize the orchestrator and verify all adapters."""
        logger.info("Initializing MCP Orchestrator...")
        
        # Health check all adapters
        health_tasks = []
        for name, adapter in self.adapters.items():
            health_tasks.append(self._check_adapter_health(name, adapter))
        
        results = await asyncio.gather(*health_tasks, return_exceptions=True)
        
        # Log health check results
        for name, result in zip(self.adapters.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"Adapter {name} health check failed: {result}")
            elif result:
                logger.info(f"Adapter {name} is healthy")
            else:
                logger.warning(f"Adapter {name} is not responding")
    
    async def _check_adapter_health(self, name: str, adapter: BaseLLMAdapter) -> bool:
        """Check health of a single adapter."""
        try:
            return await adapter.health_check()
        except Exception as e:
            logger.error(f"Health check failed for {name}: {e}")
            return False
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current orchestrator status and statistics."""
        uptime = (datetime.utcnow() - self._start_time).total_seconds()
        
        # Get adapter statistics
        adapter_stats = {}
        for name, adapter in self.adapters.items():
            adapter_stats[name] = adapter.get_statistics()
        
        return {
            "status": "operational",
            "uptime_seconds": uptime,
            "total_requests": self._request_count,
            "total_cost": self._total_cost,
            "average_cost_per_request": self._total_cost / self._request_count if self._request_count > 0 else 0,
            "available_adapters": list(self.adapters.keys()),
            "available_strategies": list(self.strategies.keys()),
            "default_strategy": self.default_strategy,
            "adapter_statistics": adapter_stats,
            "cost_limits": {
                "per_request": self.config.get("cost_management", {}).get("max_cost_per_request"),
                "daily": self.config.get("cost_management", {}).get("daily_limit"),
                "remaining_today": max(0, self.config.get("cost_management", {}).get("daily_limit", 100) - self._total_cost)
            }
        }
    
    def get_total_cost(self) -> float:
        """Get total cost incurred by this orchestrator instance."""
        return self._total_cost
    
    async def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up orchestrator resources...")
        
        # Close all adapter sessions
        cleanup_tasks = []
        for adapter in self.adapters.values():
            cleanup_tasks.append(adapter.close())
        
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        logger.info(f"Orchestrator shutdown. Total cost: ${self._total_cost:.2f}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get the current status and statistics of the orchestrator."""
        runtime = (datetime.utcnow() - self._start_time).total_seconds()
        
        status = {
            "status": "active",
            "runtime_seconds": runtime,
            "request_count": self._request_count,
            "total_cost": self._total_cost,
            "models_available": list(self.adapters.keys()),
            "strategies": list(self.strategies.keys()),
            "default_strategy": self.default_strategy,
            "config": {
                "max_cost_per_request": self.config.get("orchestration", {}).get("max_cost_per_request", 1.0),
                "daily_limit": self.config.get("orchestration", {}).get("daily_limit", 50.0)
            }
        }
        
        # Check adapter health
        adapter_status = {}
        for name, adapter in self.adapters.items():
            try:
                # Simple health check - just verify adapter exists
                adapter_status[name] = "healthy" if adapter else "unhealthy"
            except Exception:
                adapter_status[name] = "error"
        
        status["adapter_status"] = adapter_status
        
        return status