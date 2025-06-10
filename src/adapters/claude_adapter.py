"""
Claude adapter for internal Claude models.

This adapter provides integration with Claude 3 Opus and Sonnet models,
leveraging their native capabilities within the Claude Code environment.
"""

from typing import Dict, List, Optional, Any
import json
import asyncio
from datetime import datetime

from src.adapters.base import BaseLLMAdapter, LLMResponse, LLMConfig
from src.core.task import Task, TaskAnalysis


class ClaudeAdapter(BaseLLMAdapter):
    """
    Adapter for Claude models (Opus and Sonnet).
    
    This adapter is designed to work with Claude's internal API,
    maximizing the use of deep reasoning capabilities.
    """
    
    # Pricing per million tokens (as of 2024)
    PRICING = {
        "claude-3-opus-20240229": {
            "input": 15.00,
            "output": 75.00
        },
        "claude-3-sonnet-20240229": {
            "input": 3.00,
            "output": 15.00
        }
    }
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize Claude adapter with default or custom configuration."""
        if config is None:
            config = LLMConfig(
                model_id="claude-3-opus-20240229",
                api_endpoint="internal",  # Uses internal Claude API
                max_tokens=8192
            )
        super().__init__(config)
        self.thinking_mode = "deep"  # Default to deep thinking mode
        
    async def query(self, task: Task, **kwargs) -> LLMResponse:
        """
        Query Claude with a task, maximizing reasoning capabilities.
        
        Args:
            task: The task to process
            **kwargs: Additional parameters including:
                - thinking_mode: "fast" or "deep" (default: "deep")
                - max_tokens: Override default max tokens
                - temperature: Override default temperature
                
        Returns:
            LLMResponse with Claude's output
        """
        # Extract parameters
        thinking_mode = kwargs.get("thinking_mode", self.thinking_mode)
        max_tokens = kwargs.get("max_tokens", self.config.max_tokens)
        temperature = kwargs.get("temperature", self.config.temperature)
        
        # Prepare messages
        messages = self.format_messages(task, kwargs.get("analysis"))
        
        # Build request payload
        payload = {
            "model": self.config.model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": self._build_system_prompt(task, thinking_mode)
        }
        
        # Add thinking mode specific parameters
        if thinking_mode == "deep":
            payload.update({
                "thinking_preference": "maximum",
                "reasoning_effort": "high",
                "analysis_depth": "comprehensive"
            })
        
        # Track performance
        with self.track_performance():
            # Since this is internal to Claude Code, we simulate the API call
            response = await self._internal_query(payload)
        
        # Extract and process response
        content = self.extract_content(response)
        usage = response.get("usage", {})
        
        # Calculate cost
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        thinking_tokens = usage.get("thinking_tokens", 0)
        cost = self.estimate_cost(thinking_tokens, output_tokens)
        
        self._total_cost += cost
        
        return LLMResponse(
            content=content,
            model=self.config.model_id,
            thinking_tokens_used=thinking_tokens,
            completion_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens + thinking_tokens,
            latency_ms=response.get("latency_ms"),
            cost=cost,
            confidence_score=self._extract_confidence(response),
            metadata={
                "thinking_mode": thinking_mode,
                "model_version": response.get("model_version"),
                "stop_reason": response.get("stop_reason")
            }
        )
    
    def format_messages(self, task: Task, analysis: Optional[TaskAnalysis] = None) -> List[Dict[str, str]]:
        """
        Format task into Claude-compatible messages.
        
        Args:
            task: The task to format
            analysis: Optional task analysis results
            
        Returns:
            List of message dictionaries
        """
        messages = []
        
        # Build the main user message
        user_content = f"Task: {task.description}"
        
        if task.code_context:
            user_content += f"\n\nCode Context:\n```\n{task.code_context}\n```"
        
        if task.file_paths:
            user_content += f"\n\nRelevant Files: {', '.join(task.file_paths)}"
        
        if analysis:
            user_content += f"\n\nTask Analysis:\n"
            user_content += f"- Type: {analysis.task_type.name}\n"
            user_content += f"- Complexity: {analysis.complexity.name}\n"
            user_content += f"- Languages: {', '.join(analysis.languages_detected)}\n"
            if analysis.frameworks_detected:
                user_content += f"- Frameworks: {', '.join(analysis.frameworks_detected)}\n"
        
        messages.append({
            "role": "user",
            "content": user_content
        })
        
        # Add any session context as assistant message if relevant
        if task.session_context and task.session_context.get("previous_interactions"):
            messages.insert(0, {
                "role": "assistant",
                "content": "I understand the context from our previous interactions."
            })
        
        return messages
    
    def estimate_cost(self, thinking_tokens: int, completion_tokens: int) -> float:
        """
        Estimate the cost of a Claude API call.
        
        Args:
            thinking_tokens: Number of thinking tokens (counted as input)
            completion_tokens: Number of completion tokens
            
        Returns:
            Estimated cost in USD
        """
        pricing = self.PRICING.get(self.config.model_id, self.PRICING["claude-3-opus-20240229"])
        
        # Thinking tokens are billed as input tokens
        input_cost = (thinking_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]
        
        return input_cost + output_cost
    
    def get_max_reasoning_params(self) -> Dict[str, Any]:
        """Get Claude-specific parameters for maximum reasoning."""
        return {
            "thinking_mode": "deep",
            "thinking_preference": "maximum",
            "reasoning_effort": "high",
            "analysis_depth": "comprehensive",
            "temperature": 0.7,  # Balanced for creativity with reasoning
            "max_tokens": 8192
        }
    
    def _build_system_prompt(self, task: Task, thinking_mode: str) -> str:
        """
        Build a system prompt optimized for the task and thinking mode.
        
        Args:
            task: The task being processed
            thinking_mode: Either "fast" or "deep"
            
        Returns:
            System prompt string
        """
        base_prompt = """You are Claude, an AI assistant with advanced reasoning capabilities.
You are operating within the Claude Code environment to help with software engineering tasks."""
        
        if thinking_mode == "deep":
            base_prompt += """

For this task, you should:
1. Thoroughly analyze all aspects of the problem
2. Consider multiple approaches and their trade-offs
3. Think step-by-step through the implementation
4. Anticipate potential issues and edge cases
5. Provide comprehensive, well-reasoned solutions

Take your time to think deeply about the best solution."""
        
        # Add task-specific guidance
        if task.user_preferences.get("emphasis"):
            base_prompt += f"\n\nUser emphasis: {task.user_preferences['emphasis']}"
        
        return base_prompt
    
    async def _internal_query(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate internal Claude API query.
        
        In the actual implementation, this would interface with Claude's
        internal API. For now, we'll structure it to match expected format.
        
        Args:
            payload: Request payload
            
        Returns:
            Simulated API response
        """
        # This is a placeholder for the actual internal API call
        # In production, this would interface with Claude's actual internal API
        
        import time
        start_time = time.time()
        
        # Simulate processing time
        await asyncio.sleep(0.1)  # Minimal delay for simulation
        
        # Build response structure
        response = {
            "id": f"msg_{datetime.utcnow().isoformat()}",
            "model": payload["model"],
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "This is where Claude's actual response would be."
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": self.calculate_tokens(str(payload["messages"])),
                "completion_tokens": 100,  # Placeholder
                "thinking_tokens": 500 if payload.get("thinking_preference") == "maximum" else 50,
                "total_tokens": 0  # Will be calculated
            },
            "latency_ms": (time.time() - start_time) * 1000,
            "model_version": "claude-3-opus-20240229",
            "stop_reason": "stop_sequence"
        }
        
        # Calculate total tokens
        usage = response["usage"]
        usage["total_tokens"] = (usage["prompt_tokens"] + 
                               usage["completion_tokens"] + 
                               usage["thinking_tokens"])
        
        return response
    
    def _extract_confidence(self, response: Dict[str, Any]) -> Optional[float]:
        """
        Extract confidence score from Claude's response if available.
        
        Args:
            response: API response
            
        Returns:
            Confidence score between 0 and 1, or None if not available
        """
        # Claude might include confidence in metadata or special tags
        metadata = response.get("metadata", {})
        if "confidence" in metadata:
            return metadata["confidence"]
        
        # Check for confidence indicators in the response content
        content = self.extract_content(response)
        if "confidence:" in content.lower():
            # Simple extraction - in practice, this would be more sophisticated
            import re
            match = re.search(r'confidence:\s*(\d+\.?\d*)%?', content, re.I)
            if match:
                confidence = float(match.group(1))
                return confidence / 100 if confidence > 1 else confidence
        
        return None
    
    async def optimize_for_task(self, task: Task, analysis: TaskAnalysis) -> Dict[str, Any]:
        """
        Optimize adapter parameters based on task analysis.
        
        Args:
            task: The task to optimize for
            analysis: Task analysis results
            
        Returns:
            Optimized parameters dictionary
        """
        params = self.get_max_reasoning_params()
        
        # Adjust based on task type
        if analysis.task_type.name in ["DOCUMENTATION", "EXPLANATION"]:
            params["temperature"] = 0.3  # More focused
            params["max_tokens"] = 4096  # Shorter responses OK
        elif analysis.task_type.name in ["CODE_GENERATION", "ARCHITECTURE"]:
            params["temperature"] = 0.7  # Balanced creativity
            params["max_tokens"] = 8192  # Longer responses needed
        
        # Adjust based on complexity
        if analysis.complexity.value <= 2:  # Low complexity
            params["thinking_mode"] = "fast"
            params["thinking_preference"] = "balanced"
        
        return params