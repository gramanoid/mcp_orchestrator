"""
O3 adapter for OpenAI's O3 model via direct OpenAI API.

This adapter specializes in architectural design and high-level code structure,
leveraging O3's advanced reasoning capabilities.
"""

import os
import json
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.adapters.base import BaseLLMAdapter, LLMResponse, LLMConfig
from src.core.task import Task, TaskAnalysis, TaskType


class O3Adapter(BaseLLMAdapter):
    """
    Adapter for O3 model via OpenAI API.
    
    This model excels at architectural design and high-level planning.
    """
    
    # O3 pricing
    PRICING = {
        "input": 20.00,     # per million tokens
        "output": 100.00,   # per million tokens
    }
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize O3 adapter with OpenAI configuration."""
        if config is None:
            # Get API key from environment
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
                
            config = LLMConfig(
                model_id="o3-mini",  # Using o3-mini as it's available
                api_endpoint="https://api.openai.com/v1/chat/completions",
                api_key=api_key,
                max_tokens=16384,
                temperature=0.2,  # Low temperature for precise reasoning
                timeout_seconds=300
            )
        super().__init__(config)
        self.reasoning_efforts = ["low", "medium", "high"]
        self.default_reasoning = "high"
        
    async def query(self, task: Task, **kwargs) -> LLMResponse:
        """Query O3 with architectural focus."""
        start_time = datetime.now()
        
        # Extract parameters
        reasoning_effort = kwargs.get("reasoning_effort", self.default_reasoning)
        temperature = kwargs.get("temperature", self.config.temperature)
        
        # Build messages
        messages = self._build_messages(task, kwargs.get("analysis"))
        
        # Make request
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": self.config.model_id,
                    "messages": messages,
                    "max_completion_tokens": self.config.max_tokens,
                    "reasoning_effort": reasoning_effort
                }
                
                async with session.post(
                    self.config.api_endpoint,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"OpenAI API error ({response.status}): {error_text}")
                    
                    data = await response.json()
                    
                    # Extract response
                    content = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})
                    
                    # Calculate cost
                    input_tokens = usage.get("prompt_tokens", 0)
                    output_tokens = usage.get("completion_tokens", 0)
                    reasoning_tokens = usage.get("reasoning_tokens", 0)
                    
                    total_input = input_tokens + reasoning_tokens
                    cost = (
                        (total_input / 1_000_000) * self.PRICING["input"] +
                        (output_tokens / 1_000_000) * self.PRICING["output"]
                    )
                    
                    # Track metrics
                    self._request_count += 1
                    self._total_cost += cost
                    
                    return LLMResponse(
                        content=content,
                        model=self.config.model_id,
                        thinking_tokens_used=reasoning_tokens,
                        completion_tokens=output_tokens,
                        total_tokens=total_input + output_tokens,
                        cost=cost,
                        latency_ms=(datetime.now() - start_time).total_seconds() * 1000,
                        metadata={
                            "reasoning_effort": reasoning_effort,
                            "temperature": temperature
                        }
                    )
                    
        except Exception as e:
            self.logger.error(f"O3 query failed: {e}")
            raise
            
    def _build_messages(self, task: Task, analysis: Optional[TaskAnalysis] = None) -> List[Dict[str, str]]:
        """Build messages optimized for O3's architectural capabilities."""
        messages = []
        
        # System message
        system_content = """You are an expert software architect who excels at:
- High-level system design and architecture
- Identifying optimal design patterns and abstractions
- Planning scalable, maintainable solutions
- Making pragmatic architectural trade-offs

Provide comprehensive architectural guidance with clear reasoning."""
        
        messages.append({"role": "system", "content": system_content})
        
        # User message
        user_content = f"Task: {task.description}"
        
        if task.code_context:
            user_content += f"\n\nCode Context:\n{task.code_context}"
            
        if analysis:
            user_content += f"\n\nAnalysis: Task type is {analysis.task_type.name} with {analysis.complexity.name} complexity."
            
        messages.append({"role": "user", "content": user_content})
        
        return messages
        
    async def health_check(self) -> bool:
        """Check if O3 API is accessible."""
        try:
            # Simple test with minimal tokens
            test_response = await self.query(
                Task(description="test", session_context={}),
                reasoning_effort="low",
                max_tokens=1
            )
            return True
        except:
            return False
            
    def get_max_reasoning_params(self) -> Dict[str, Any]:
        """Get parameters for maximum reasoning quality."""
        return {
            "reasoning_effort": "high",
            "temperature": 0.1,
            "max_tokens": self.config.max_tokens
        }
    
    def format_messages(self, task: Task, analysis: Optional[TaskAnalysis] = None) -> List[Dict[str, str]]:
        """Format messages for O3 - implements abstract method."""
        return self._build_messages(task, analysis)
        
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate cost for O3 usage - implements abstract method."""
        # O3 costs include reasoning tokens as input
        total_input = prompt_tokens  # Reasoning tokens included in prompt
        cost = (
            (total_input / 1_000_000) * self.PRICING["input"] +
            (completion_tokens / 1_000_000) * self.PRICING["output"]
        )
        return cost