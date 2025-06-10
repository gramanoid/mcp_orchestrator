"""
Error handling and custom exceptions for MCP Orchestrator.

This module defines custom exceptions and error handling strategies
for the orchestrator system.
"""

from typing import Optional, Dict, Any
import logging


logger = logging.getLogger(__name__)


class MCPError(Exception):
    """Base exception for all MCP-related errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize MCP error.
        
        Args:
            message: Error message
            details: Optional dictionary with additional error details
        """
        super().__init__(message)
        self.details = details or {}
        
        # Log the error
        logger.error(f"{self.__class__.__name__}: {message}", extra={"details": self.details})


class ConfigurationError(MCPError):
    """Raised when there's a configuration issue."""
    pass


class ModelNotAvailableError(MCPError):
    """Raised when a requested model is not available."""
    
    def __init__(self, model_name: str, reason: Optional[str] = None):
        """
        Initialize model availability error.
        
        Args:
            model_name: Name of the unavailable model
            reason: Optional reason for unavailability
        """
        message = f"Model '{model_name}' is not available"
        if reason:
            message += f": {reason}"
        
        super().__init__(message, {"model": model_name, "reason": reason})


class APIError(MCPError):
    """Raised when an API call fails."""
    
    def __init__(self, service: str, status_code: Optional[int] = None, 
                 response: Optional[str] = None):
        """
        Initialize API error.
        
        Args:
            service: Name of the API service
            status_code: HTTP status code if applicable
            response: Error response from the API
        """
        message = f"API error from {service}"
        if status_code:
            message += f" (status: {status_code})"
        
        super().__init__(
            message,
            {"service": service, "status_code": status_code, "response": response}
        )


class RateLimitError(APIError):
    """Raised when API rate limit is exceeded."""
    
    def __init__(self, service: str, retry_after: Optional[int] = None):
        """
        Initialize rate limit error.
        
        Args:
            service: Name of the API service
            retry_after: Seconds to wait before retry
        """
        message = f"Rate limit exceeded for {service}"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        
        super().__init__(service, status_code=429)
        self.retry_after = retry_after
        self.details["retry_after"] = retry_after


class CostLimitError(MCPError):
    """Raised when cost limits are exceeded."""
    
    def __init__(self, current_cost: float, limit: float, limit_type: str = "request"):
        """
        Initialize cost limit error.
        
        Args:
            current_cost: Current cost that would exceed limit
            limit: The limit that would be exceeded
            limit_type: Type of limit ("request" or "daily")
        """
        message = f"Cost limit exceeded: ${current_cost:.2f} exceeds {limit_type} limit of ${limit:.2f}"
        
        super().__init__(
            message,
            {"current_cost": current_cost, "limit": limit, "limit_type": limit_type}
        )


class OrchestrationError(MCPError):
    """Raised when orchestration fails."""
    
    def __init__(self, strategy: str, phase: str, reason: str):
        """
        Initialize orchestration error.
        
        Args:
            strategy: Name of the orchestration strategy
            phase: Phase where the error occurred
            reason: Reason for the failure
        """
        message = f"Orchestration failed in {strategy} strategy during {phase}: {reason}"
        
        super().__init__(
            message,
            {"strategy": strategy, "phase": phase, "reason": reason}
        )


class TaskAnalysisError(MCPError):
    """Raised when task analysis fails."""
    
    def __init__(self, reason: str, task_description: Optional[str] = None):
        """
        Initialize task analysis error.
        
        Args:
            reason: Reason for analysis failure
            task_description: Optional task description that failed
        """
        message = f"Task analysis failed: {reason}"
        
        super().__init__(
            message,
            {"reason": reason, "task_description": task_description}
        )


class ResponseSynthesisError(MCPError):
    """Raised when response synthesis fails."""
    
    def __init__(self, strategy: str, reason: str, response_count: int = 0):
        """
        Initialize synthesis error.
        
        Args:
            strategy: Synthesis strategy that failed
            reason: Reason for failure
            response_count: Number of responses being synthesized
        """
        message = f"Failed to synthesize responses using {strategy}: {reason}"
        
        super().__init__(
            message,
            {"strategy": strategy, "reason": reason, "response_count": response_count}
        )


class MCPTimeoutError(MCPError):
    """Raised when an operation times out."""
    
    def __init__(self, operation: str, timeout_seconds: float):
        """
        Initialize timeout error.
        
        Args:
            operation: Operation that timed out
            timeout_seconds: Timeout duration in seconds
        """
        message = f"Operation '{operation}' timed out after {timeout_seconds} seconds"
        
        super().__init__(
            message,
            {"operation": operation, "timeout_seconds": timeout_seconds}
        )


class NoModelsAvailableError(MCPError):
    """Raised when no models are available for a task."""
    
    def __init__(self, reason: str = "All models are unavailable or have failed"):
        """
        Initialize no models available error.
        
        Args:
            reason: Reason why no models are available
        """
        super().__init__(f"No models available: {reason}")


class ErrorHandler:
    """
    Centralized error handling for the MCP system.
    
    Provides retry logic, fallback mechanisms, and error recovery strategies.
    """
    
    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0):
        """
        Initialize error handler.
        
        Args:
            max_retries: Maximum number of retry attempts
            backoff_factor: Exponential backoff factor
        """
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def handle_with_retry(self, operation, *args, **kwargs):
        """
        Execute an operation with retry logic.
        
        Args:
            operation: Async function to execute
            *args: Positional arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Result of the operation
            
        Raises:
            The last exception if all retries fail
        """
        import asyncio
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                return await operation(*args, **kwargs)
                
            except RateLimitError as e:
                # Handle rate limiting with specific wait time
                wait_time = e.retry_after or (self.backoff_factor ** attempt)
                self.logger.warning(
                    f"Rate limit hit on attempt {attempt + 1}. "
                    f"Waiting {wait_time} seconds..."
                )
                await asyncio.sleep(wait_time)
                last_error = e
                
            except APIError as e:
                # Retry API errors with exponential backoff
                if attempt < self.max_retries - 1:
                    wait_time = self.backoff_factor ** attempt
                    self.logger.warning(
                        f"API error on attempt {attempt + 1}. "
                        f"Retrying in {wait_time} seconds..."
                    )
                    await asyncio.sleep(wait_time)
                    last_error = e
                else:
                    raise
                    
            except (CostLimitError, NoModelsAvailableError) as e:
                # Don't retry these errors
                raise
                
            except Exception as e:
                # Log unexpected errors
                self.logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                last_error = e
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.backoff_factor ** attempt)
                else:
                    raise
        
        # If we get here, all retries failed
        if last_error:
            raise last_error
        else:
            raise MCPError("Operation failed after all retry attempts")
    
    def get_fallback_model(self, failed_models: list, available_models: dict) -> Optional[str]:
        """
        Get a fallback model when primary models fail.
        
        Args:
            failed_models: List of model names that have failed
            available_models: Dictionary of all available models
            
        Returns:
            Name of fallback model or None if no fallback available
        """
        # Priority order for fallbacks
        fallback_order = [
            "claude_opus",      # Most reliable
            "claude_sonnet",    # Fast internal fallback
            "gemini_polyglot",  # External fallback
            "o3_architect"      # Last resort
        ]
        
        for model in fallback_order:
            if model in available_models and model not in failed_models:
                self.logger.info(f"Using {model} as fallback")
                return model
        
        return None
    
    def should_escalate_to_user(self, error: Exception) -> bool:
        """
        Determine if an error should be escalated to the user.
        
        Args:
            error: The exception to evaluate
            
        Returns:
            True if the error should be shown to the user
        """
        # Always escalate these errors
        escalate_types = (
            CostLimitError,
            NoModelsAvailableError,
            ConfigurationError
        )
        
        return isinstance(error, escalate_types)
    
    def format_user_error(self, error: Exception) -> str:
        """
        Format an error message for user presentation.
        
        Args:
            error: The exception to format
            
        Returns:
            User-friendly error message
        """
        if isinstance(error, CostLimitError):
            return (
                f"The request would exceed the {error.details['limit_type']} "
                f"cost limit of ${error.details['limit']:.2f}. "
                "Please adjust your limits or try a simpler request."
            )
        
        elif isinstance(error, NoModelsAvailableError):
            return (
                "No AI models are currently available to process your request. "
                "This might be due to service outages or missing API keys. "
                "Please check your configuration and try again later."
            )
        
        elif isinstance(error, ConfigurationError):
            return (
                f"Configuration error: {str(error)}. "
                "Please check your MCP configuration settings."
            )
        
        elif isinstance(error, RateLimitError):
            retry_msg = ""
            if error.retry_after:
                retry_msg = f" Please try again in {error.retry_after} seconds."
            return (
                f"Rate limit exceeded for {error.details['service']}.{retry_msg}"
            )
        
        else:
            # Generic error message
            return (
                "An error occurred while processing your request. "
                f"Error: {str(error)}"
            )