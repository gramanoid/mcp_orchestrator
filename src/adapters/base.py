"""
Base adapter class for LLM integrations.

This module provides the abstract base class that all LLM adapters must implement,
ensuring consistent interface and behavior across different models.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import asyncio
import json
import logging
import time
from contextlib import contextmanager

from src.core.task import Task, TaskAnalysis


@dataclass
class LLMResponse:
    """
    Standardized response format from LLM adapters.
    
    Attributes:
        content: The main response content
        model: The model that generated the response
        thinking_tokens_used: Number of thinking/reasoning tokens used
        completion_tokens: Number of completion tokens used
        total_tokens: Total tokens used
        latency_ms: Response latency in milliseconds
        cost: Estimated cost of the API call
        confidence_score: Model's confidence in the response (if available)
        metadata: Additional model-specific metadata
    """
    content: str
    model: str
    thinking_tokens_used: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    latency_ms: Optional[float] = None
    cost: Optional[float] = None
    confidence_score: Optional[float] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class LLMConfig:
    """Configuration for an LLM adapter."""
    model_id: str
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    max_tokens: int = 8192
    temperature: float = 0.7
    timeout_seconds: int = 120
    retry_attempts: int = 3
    custom_headers: Dict[str, str] = None
    
    def __post_init__(self):
        if self.custom_headers is None:
            self.custom_headers = {}


class BaseLLMAdapter(ABC):
    """
    Abstract base class for all LLM adapters.
    
    This class defines the interface that all LLM implementations must follow,
    ensuring consistent behavior and enabling easy addition of new models.
    """
    
    def __init__(self, config: LLMConfig):
        """
        Initialize the adapter with configuration.
        
        Args:
            config: LLM configuration object
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._session = None
        self._request_count = 0
        self._total_cost = 0.0
        
    @abstractmethod
    async def query(self, task: Task, **kwargs) -> LLMResponse:
        """
        Query the LLM with a task.
        
        Args:
            task: The task to process
            **kwargs: Additional model-specific parameters
            
        Returns:
            LLMResponse object containing the model's response
        """
        pass
    
    @abstractmethod
    def format_messages(self, task: Task, analysis: Optional[TaskAnalysis] = None) -> List[Dict[str, str]]:
        """
        Format the task into messages suitable for the LLM.
        
        Args:
            task: The task to format
            analysis: Optional task analysis results
            
        Returns:
            List of message dictionaries with 'role' and 'content' keys
        """
        pass
    
    @abstractmethod
    def estimate_cost(self, thinking_tokens: int, completion_tokens: int) -> float:
        """
        Estimate the cost of an API call.
        
        Args:
            thinking_tokens: Number of thinking/reasoning tokens
            completion_tokens: Number of completion tokens
            
        Returns:
            Estimated cost in USD
        """
        pass
    
    async def _make_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make an HTTP request to the LLM API.
        
        Args:
            payload: Request payload
            
        Returns:
            Response data from the API
        """
        import aiohttp
        
        if self._session is None:
            self._session = aiohttp.ClientSession()
        
        headers = {
            "Content-Type": "application/json",
            **self.config.custom_headers
        }
        
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        
        attempt = 0
        last_error = None
        
        while attempt < self.config.retry_attempts:
            try:
                start_time = time.time()
                
                async with self._session.post(
                    self.config.api_endpoint,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                ) as response:
                    response_data = await response.json()
                    
                    if response.status == 200:
                        latency_ms = (time.time() - start_time) * 1000
                        self._request_count += 1
                        return response_data
                    
                    # Handle rate limiting
                    if response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", "60"))
                        self.logger.warning(f"Rate limited. Retrying after {retry_after} seconds.")
                        await asyncio.sleep(retry_after)
                        attempt += 1
                        continue
                    
                    # Handle other errors
                    error_msg = response_data.get("error", {}).get("message", "Unknown error")
                    raise Exception(f"API error ({response.status}): {error_msg}")
                    
            except asyncio.TimeoutError:
                last_error = "Request timed out"
                self.logger.warning(f"Request timeout on attempt {attempt + 1}")
            except Exception as e:
                last_error = str(e)
                self.logger.error(f"Request error on attempt {attempt + 1}: {e}")
            
            attempt += 1
            if attempt < self.config.retry_attempts:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        raise Exception(f"Failed after {self.config.retry_attempts} attempts. Last error: {last_error}")
    
    def get_max_reasoning_params(self) -> Dict[str, Any]:
        """
        Get model-specific parameters for maximum reasoning.
        
        Returns:
            Dictionary of parameters to maximize reasoning capabilities
        """
        return {}
    
    @contextmanager
    def track_performance(self):
        """Context manager for tracking performance metrics."""
        start_time = time.time()
        initial_cost = self._total_cost
        
        yield
        
        elapsed_ms = (time.time() - start_time) * 1000
        cost_incurred = self._total_cost - initial_cost
        
        self.logger.info(
            f"Request completed in {elapsed_ms:.2f}ms, cost: ${cost_incurred:.4f}"
        )
    
    def validate_response(self, response: Dict[str, Any]) -> bool:
        """
        Validate that the API response contains expected fields.
        
        Args:
            response: Raw API response
            
        Returns:
            True if response is valid, False otherwise
        """
        required_fields = ["choices", "usage"]
        return all(field in response for field in required_fields)
    
    def extract_content(self, response: Dict[str, Any]) -> str:
        """
        Extract the main content from an API response.
        
        Args:
            response: Raw API response
            
        Returns:
            Extracted content string
        """
        if not self.validate_response(response):
            raise ValueError("Invalid API response format")
        
        choices = response.get("choices", [])
        if not choices:
            raise ValueError("No choices in API response")
        
        return choices[0].get("message", {}).get("content", "")
    
    def calculate_tokens(self, text: str) -> int:
        """
        Estimate token count for a given text.
        
        This is a rough approximation; specific models may count differently.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Estimated token count
        """
        # Rough approximation: 1 token ≈ 4 characters
        return len(text) // 4
    
    async def health_check(self) -> bool:
        """
        Check if the LLM service is available and responding.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Make a minimal request to check connectivity
            test_payload = {
                "model": self.config.model_id,
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 1
            }
            
            response = await self._make_request(test_payload)
            return self.validate_response(response)
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get usage statistics for this adapter.
        
        Returns:
            Dictionary containing usage statistics
        """
        return {
            "model": self.config.model_id,
            "request_count": self._request_count,
            "total_cost": self._total_cost,
            "average_cost": self._total_cost / self._request_count if self._request_count > 0 else 0
        }
    
    async def close(self):
        """Clean up resources."""
        if self._session:
            await self._session.close()
            self._session = None