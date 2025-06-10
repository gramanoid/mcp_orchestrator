"""
OpenRouter adapter for external models (Gemini, GPT-4, etc).

This adapter handles all OpenRouter API calls with proper error handling
and request formatting.
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
import aiohttp

from src.adapters.base import BaseLLMAdapter, LLMResponse, LLMConfig
from src.core.task import Task


class OpenRouterAdapter(BaseLLMAdapter):
    """Adapter for models accessed via OpenRouter."""
    
    def __init__(self, config: LLMConfig):
        """Initialize with OpenRouter configuration."""
        super().__init__(config)
        self.api_endpoint = "https://openrouter.ai/api/v1/chat/completions"
        
    async def query(self, task: Task, **kwargs) -> LLMResponse:
        """Query model via OpenRouter API."""
        # Build messages
        messages = [
            {
                "role": "system",
                "content": "You are a helpful AI assistant providing code review and analysis."
            },
            {
                "role": "user", 
                "content": self._build_prompt(task)
            }
        ]
        
        # Build request payload with MAX PERFORMANCE settings
        payload = {
            "model": self.config.model_id,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            # Model-specific parameters for maximum thinking
            "top_p": 0.95,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        }
        
        # Add model-specific thinking parameters
        if "gemini" in self.config.model_id:
            payload["thinking_tokens"] = 32768  # Maximum thinking for Gemini
        elif "o3" in self.config.model_id:
            payload["reasoning_effort"] = "high"  # Maximum reasoning for O3
        
        # Make API request
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/mcp-orchestrator",
            "X-Title": "MCP Orchestrator"
        }
        
        # Track performance
        with self.track_performance():
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_endpoint,
                    json=payload,
                    headers=headers
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"API error ({response.status}): {error_text}")
                    
                    result = await response.json()
        
        # Extract response
        content = result["choices"][0]["message"]["content"]
        usage = result.get("usage", {})
        
        # Calculate cost based on model
        cost = self._calculate_cost(
            self.config.model_id,
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0)
        )
        
        return LLMResponse(
            content=content,
            model=self.config.model_id,
            thinking_tokens_used=0,
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            latency_ms=result.get("latency_ms", 0),
            cost=cost,
            confidence_score=0.85,
            metadata={
                "provider": "openrouter",
                "model_id": self.config.model_id
            }
        )
    
    def _build_prompt(self, task: Task) -> str:
        """Build prompt for the model."""
        prompt_parts = [f"Task: {task.description}"]
        
        if task.code_context:
            prompt_parts.append(f"\nCode:\n{task.code_context}")
            
        return "\n".join(prompt_parts)
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on model pricing."""
        # OpenRouter pricing (approximate)
        pricing = {
            "google/gemini-2.5-pro-preview": {"input": 0.000075, "output": 0.0003},
            "openai/gpt-4.1": {"input": 0.03, "output": 0.06},
            "openai/o4-mini-high": {"input": 0.015, "output": 0.06}
        }
        
        model_pricing = pricing.get(model, {"input": 0.01, "output": 0.03})
        
        input_cost = (input_tokens / 1000) * model_pricing["input"]
        output_cost = (output_tokens / 1000) * model_pricing["output"]
        
        return input_cost + output_cost
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate the cost of a request."""
        return self._calculate_cost(self.config.model_id, input_tokens, output_tokens)
    
    def format_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Format messages for OpenRouter API."""
        # OpenRouter uses standard OpenAI format
        return messages
    
    async def _make_request(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Make request to OpenRouter API."""
        payload = {
            "model": self.config.model_id,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "top_p": 0.95,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        }
        
        # Add model-specific parameters
        if "gemini" in self.config.model_id:
            payload["thinking_tokens"] = 32768
        elif "o3" in self.config.model_id:
            payload["reasoning_effort"] = "high"
            
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/mcp-orchestrator",
            "X-Title": "MCP Orchestrator"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.api_endpoint, json=payload, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API error ({response.status}): {error_text}")
                    
                result = await response.json()
                
        return {
            "content": result["choices"][0]["message"]["content"],
            "usage": result.get("usage", {})
        }