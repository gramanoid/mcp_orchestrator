"""
Gemini adapter for Google's Gemini 2.5 Pro Preview model via OpenRouter.

This adapter specializes in leveraging Gemini's 32k thinking tokens capability
for complex code edits and polyglot programming tasks.
"""

from typing import Dict, List, Optional, Any
import json
import asyncio
from datetime import datetime

from src.adapters.base import BaseLLMAdapter, LLMResponse, LLMConfig
from src.core.task import Task, TaskAnalysis, TaskType


class GeminiAdapter(BaseLLMAdapter):
    """
    Adapter for Gemini-2.5-pro-preview with 32k thinking tokens.
    
    This model excels at precise code edits and supports the diff-fenced
    edit format, achieving 83.1% correctness on coding benchmarks.
    """
    
    # OpenRouter pricing (approximate, check latest)
    PRICING = {
        "input": 2.00,   # per million tokens
        "output": 10.00,  # per million tokens
        "thinking": 2.00  # thinking tokens billed as input
    }
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize Gemini adapter with OpenRouter configuration."""
        if config is None:
            config = LLMConfig(
                model_id="google/gemini-2.5-pro-preview-06-05",
                api_endpoint="https://openrouter.ai/api/v1/chat/completions",
                max_tokens=8192,
                temperature=0.7,
                timeout_seconds=180  # Longer timeout for deep thinking
            )
        super().__init__(config)
        self.max_thinking_tokens = 32000
        self.default_thinking_tokens = 16000
        
    async def query(self, task: Task, **kwargs) -> LLMResponse:
        """
        Query Gemini with a task, utilizing its thinking token capability.
        
        Args:
            task: The task to process
            **kwargs: Additional parameters including:
                - thinking_tokens: Number of thinking tokens (default: 16000, max: 32000)
                - edit_format: "diff-fenced" for code edits
                - temperature: Override default temperature
                - analysis: TaskAnalysis results
                
        Returns:
            LLMResponse with Gemini's output
        """
        # Extract parameters
        thinking_tokens = min(
            kwargs.get("thinking_tokens", self.default_thinking_tokens),
            self.max_thinking_tokens
        )
        edit_format = kwargs.get("edit_format", "diff-fenced")
        temperature = kwargs.get("temperature", self.config.temperature)
        analysis = kwargs.get("analysis")
        
        # Optimize thinking tokens based on task
        if analysis and analysis.requires_deep_reasoning:
            thinking_tokens = self.max_thinking_tokens
        
        # Prepare messages
        messages = self.format_messages(task, analysis, edit_format)
        
        # Build request payload with OpenRouter-specific parameters
        payload = {
            "model": self.config.model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": self.config.max_tokens,
            "provider": {
                "order": ["Google"],
                "allow_fallbacks": False,
                "require_parameters": True,
                "data_collection": False
            },
            "transforms": ["thinking_tokens"],
            "thinking_tokens": thinking_tokens,
            "route": "fallback"  # Use fallback routing for reliability
        }
        
        # Add edit format instructions if applicable
        if edit_format == "diff-fenced" and self._is_edit_task(task, analysis):
            payload["messages"].append({
                "role": "system",
                "content": self._get_diff_format_instructions()
            })
        
        # Track performance
        with self.track_performance():
            response = await self._make_request(payload)
        
        # Process response
        return self._process_response(response, thinking_tokens)
    
    def format_messages(self, task: Task, analysis: Optional[TaskAnalysis] = None,
                       edit_format: str = "standard") -> List[Dict[str, str]]:
        """
        Format task into Gemini-compatible messages.
        
        Args:
            task: The task to format
            analysis: Optional task analysis results
            edit_format: Format preference for edits
            
        Returns:
            List of message dictionaries
        """
        messages = []
        
        # System message optimized for Gemini
        system_content = """You are an expert software engineer with deep knowledge across 
multiple programming languages and frameworks. You excel at precise code modifications,
architectural design, and solving complex programming challenges.

Key strengths:
- Polyglot programming expertise
- Precise code editing with minimal errors
- Deep reasoning about code structure and design
- Understanding of complex codebases

Please think carefully through the problem before providing your solution."""
        
        if edit_format == "diff-fenced" and self._is_edit_task(task, analysis):
            system_content += "\n\nWhen editing code, use diff-fenced format for clarity."
        
        messages.append({
            "role": "system",
            "content": system_content
        })
        
        # Build user message with rich context
        user_content = self._build_user_content(task, analysis)
        messages.append({
            "role": "user",
            "content": user_content
        })
        
        return messages
    
    def estimate_cost(self, thinking_tokens: int, completion_tokens: int) -> float:
        """
        Estimate the cost of a Gemini API call via OpenRouter.
        
        Args:
            thinking_tokens: Number of thinking tokens used
            completion_tokens: Number of completion tokens
            
        Returns:
            Estimated cost in USD
        """
        # Thinking tokens are billed as input tokens
        input_cost = (thinking_tokens / 1_000_000) * self.PRICING["thinking"]
        output_cost = (completion_tokens / 1_000_000) * self.PRICING["output"]
        
        # Add small OpenRouter fee (typically ~10%)
        total = (input_cost + output_cost) * 1.1
        
        return total
    
    def get_max_reasoning_params(self) -> Dict[str, Any]:
        """Get Gemini-specific parameters for maximum reasoning."""
        return {
            "thinking_tokens": self.max_thinking_tokens,
            "temperature": 0.7,
            "max_tokens": 8192,
            "edit_format": "diff-fenced",
            "provider": {
                "order": ["Google"],
                "require_parameters": True
            }
        }
    
    def _build_user_content(self, task: Task, analysis: Optional[TaskAnalysis]) -> str:
        """
        Build comprehensive user message content.
        
        Args:
            task: The task to process
            analysis: Optional task analysis
            
        Returns:
            Formatted user content string
        """
        content_parts = [f"Task: {task.description}"]
        
        # Add code context with proper formatting
        if task.code_context:
            content_parts.append("\nCode Context:")
            # Detect language for syntax highlighting
            lang = self._detect_language(task.code_context, task.file_paths)
            content_parts.append(f"```{lang}\n{task.code_context}\n```")
        
        # Add file information
        if task.file_paths:
            content_parts.append(f"\nFiles involved: {', '.join(task.file_paths)}")
        
        # Add analysis insights
        if analysis:
            insights = []
            insights.append(f"Task type: {analysis.task_type.name}")
            insights.append(f"Complexity: {analysis.complexity.name}")
            
            if analysis.languages_detected:
                insights.append(f"Languages: {', '.join(analysis.languages_detected)}")
            
            if analysis.frameworks_detected:
                insights.append(f"Frameworks: {', '.join(analysis.frameworks_detected)}")
            
            if analysis.estimated_lines_affected > 100:
                insights.append(f"Large scope: ~{analysis.estimated_lines_affected} lines affected")
            
            content_parts.append("\nTask Analysis:")
            for insight in insights:
                content_parts.append(f"- {insight}")
        
        # Add user preferences
        if task.user_preferences:
            if task.user_preferences.get("quality_mode") == "maximum":
                content_parts.append("\nNote: Maximum quality mode requested. Please be thorough.")
            
            if task.user_preferences.get("specific_requirements"):
                content_parts.append(f"\nSpecific requirements: {task.user_preferences['specific_requirements']}")
        
        return "\n".join(content_parts)
    
    def _is_edit_task(self, task: Task, analysis: Optional[TaskAnalysis]) -> bool:
        """Determine if the task involves code editing."""
        if analysis and analysis.task_type in [
            TaskType.BUG_FIX, TaskType.REFACTORING, TaskType.COMPLEX_EDIT,
            TaskType.OPTIMIZATION
        ]:
            return True
        
        # Check task description for edit indicators
        edit_keywords = ["fix", "modify", "change", "update", "refactor", "edit"]
        desc_lower = task.description.lower()
        return any(keyword in desc_lower for keyword in edit_keywords)
    
    def _get_diff_format_instructions(self) -> str:
        """Get instructions for diff-fenced format output."""
        return """When making code modifications, please use the diff-fenced format:

```diff
--- original.py
+++ modified.py
@@ -10,7 +10,7 @@
 def calculate_total(items):
     total = 0
     for item in items:
-        total += item.price
+        total += item.price * item.quantity
     return total
```

This format clearly shows what lines are being changed, making edits precise and easy to review."""
    
    def _detect_language(self, code: str, file_paths: List[str]) -> str:
        """Detect programming language for syntax highlighting."""
        # Check file extensions first
        for path in file_paths:
            if path.endswith('.py'):
                return 'python'
            elif path.endswith('.js'):
                return 'javascript'
            elif path.endswith('.ts'):
                return 'typescript'
            elif path.endswith('.java'):
                return 'java'
            elif path.endswith('.go'):
                return 'go'
            elif path.endswith('.rs'):
                return 'rust'
            elif path.endswith('.cpp') or path.endswith('.cc'):
                return 'cpp'
        
        # Fall back to content detection
        if 'def ' in code or 'import ' in code:
            return 'python'
        elif 'function ' in code or 'const ' in code:
            return 'javascript'
        
        return ''  # No specific language detected
    
    def _process_response(self, response: Dict[str, Any], thinking_tokens: int) -> LLMResponse:
        """
        Process Gemini's response into standardized format.
        
        Args:
            response: Raw API response
            thinking_tokens: Number of thinking tokens requested
            
        Returns:
            Standardized LLMResponse
        """
        content = self.extract_content(response)
        usage = response.get("usage", {})
        
        # Extract token counts
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        actual_thinking_tokens = usage.get("thinking_tokens", thinking_tokens)
        
        # Calculate cost
        cost = self.estimate_cost(actual_thinking_tokens, completion_tokens)
        self._total_cost += cost
        
        # Extract any confidence indicators from the response
        confidence = self._extract_confidence_from_content(content)
        
        return LLMResponse(
            content=content,
            model=self.config.model_id,
            thinking_tokens_used=actual_thinking_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens + actual_thinking_tokens,
            latency_ms=response.get("latency_ms"),
            cost=cost,
            confidence_score=confidence,
            metadata={
                "thinking_tokens_requested": thinking_tokens,
                "provider": "Google",
                "edit_format": "diff-fenced",
                "model_capabilities": {
                    "max_thinking_tokens": self.max_thinking_tokens,
                    "supports_diff_format": True,
                    "polyglot_optimized": True
                }
            }
        )
    
    def _extract_confidence_from_content(self, content: str) -> Optional[float]:
        """
        Extract confidence indicators from Gemini's response.
        
        Args:
            content: Response content
            
        Returns:
            Confidence score or None
        """
        # Look for explicit confidence statements
        import re
        
        patterns = [
            r'confidence[:\s]+(\d+)%',
            r'(\d+)%\s+confident',
            r'certainty[:\s]+(\d+\.?\d*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.I)
            if match:
                value = float(match.group(1))
                return value / 100 if value > 1 else value
        
        # Infer confidence from language
        high_confidence_phrases = ["definitely", "certainly", "clearly", "obviously"]
        low_confidence_phrases = ["might", "possibly", "perhaps", "could be"]
        
        content_lower = content.lower()
        high_count = sum(1 for phrase in high_confidence_phrases if phrase in content_lower)
        low_count = sum(1 for phrase in low_confidence_phrases if phrase in content_lower)
        
        if high_count > low_count:
            return 0.85
        elif low_count > high_count:
            return 0.65
        
        return None  # No clear confidence indicators
    
    async def optimize_for_edit_task(self, task: Task, existing_code: str) -> Dict[str, Any]:
        """
        Optimize parameters specifically for code editing tasks.
        
        Args:
            task: The editing task
            existing_code: Current code to be edited
            
        Returns:
            Optimized parameters for edit tasks
        """
        params = self.get_max_reasoning_params()
        
        # Calculate complexity based on code size
        code_lines = existing_code.count('\n')
        
        if code_lines < 50:
            params["thinking_tokens"] = 8000
        elif code_lines < 200:
            params["thinking_tokens"] = 16000
        else:
            params["thinking_tokens"] = 32000  # Maximum for complex edits
        
        # Lower temperature for precise edits
        params["temperature"] = 0.3
        
        # Ensure diff format is used
        params["edit_format"] = "diff-fenced"
        
        return params