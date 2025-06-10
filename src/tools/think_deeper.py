"""
Think Deeper Tool - Extended reasoning using orchestration strategies.
"""

import logging
from typing import Dict, Any, Optional, List

from src.tools.base import BaseTool, ToolOutput, ToolRequest
from src.core.task import Task


logger = logging.getLogger(__name__)


class ThinkDeeperRequest(ToolRequest):
    """Request model for extended thinking."""
    current_analysis: str
    problem_context: Optional[str] = None
    focus_areas: Optional[List[str]] = None
    files: Optional[List[str]] = None


class ThinkDeeperTool(BaseTool):
    """
    Extended thinking tool that leverages progressive deep dive strategy.
    
    This tool is designed to:
    - Extend and validate existing analysis
    - Challenge assumptions and find edge cases
    - Provide alternative approaches
    - Synthesize insights from multiple models
    """
    
    def get_name(self) -> str:
        return "think_deeper"
    
    def get_description(self) -> str:
        return (
            "Ask Gemini 2.5 Pro and O3 to think deeper about Claude's analysis. "
            "They will challenge assumptions, explore edge cases, and provide "
            "alternative perspectives to enhance Claude's response."
        )
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "current_analysis": {
                    "type": "string",
                    "description": "Current analysis to extend"
                },
                "problem_context": {
                    "type": "string",
                    "description": "Additional context about the problem"
                },
                "focus_areas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific aspects to focus on"
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional files for context"
                },
                "thinking_mode": {
                    "type": "string",
                    "enum": ["minimal", "low", "medium", "high", "max"],
                    "default": "max"
                }
            },
            "required": ["current_analysis"]
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolOutput:
        """Execute extended thinking using orchestration."""
        try:
            request = ThinkDeeperRequest(**arguments)
            
            # Build extended thinking prompt
            prompt = self._build_thinking_prompt(request)
            
            # Create task with high complexity for deep thinking
            task = Task(
                description=prompt,
                session_context={
                    "tool": "think_deeper",
                    "thinking_mode": arguments.get("thinking_mode", "max"),
                    "focus_areas": arguments.get("focus_areas")
                }
            )
            
            # Configure strategy for maximum depth
            config = {
                "max_depth": 3,  # Use all layers
                "require_synthesis": True,
                "thinking_mode": request.thinking_mode or "max"
            }
            
            # Use progressive deep dive for thorough analysis
            # Add config to session context
            task.session_context.update(config)
            result = await self.orchestrator.orchestrate(
                task,
                strategy_override="progressive_deep_dive"
            )
            
            # Check if additional context is needed
            if self._needs_clarification(result.content):
                return ToolOutput(
                    status="requires_clarification",
                    content=self._extract_clarification(result.content),
                    content_type="json",
                    metadata={"original_analysis": arguments.get("current_analysis", "")}
                )
            
            # Format extended analysis
            formatted_content = self._format_extended_analysis(
                result.content,
                result.metadata
            )
            
            return ToolOutput(
                status="success",
                content=formatted_content,
                content_type="markdown",
                metadata={
                    "models_used": result.metadata.get("models_used", []),
                    "thinking_depth": result.metadata.get("depth", 0),
                    "synthesis_performed": result.metadata.get("synthesis", False)
                }
            )
            
        except Exception as e:
            logger.error(f"Think deeper failed: {e}")
            return ToolOutput(
                status="error",
                content=f"Extended thinking failed: {str(e)}",
                content_type="text"
            )
    
    def _build_thinking_prompt(self, request: ThinkDeeperRequest) -> str:
        """Build prompt for extended thinking."""
        prompt_parts = [
            "Perform extended analysis to deepen and challenge the following thinking:",
            f"\n{request.current_analysis}\n"
        ]
        
        if request.problem_context:
            prompt_parts.append(f"\nProblem Context:\n{request.problem_context}\n")
        
        prompt_parts.append("\nYour analysis should:")
        prompt_parts.append("1. Identify gaps and unstated assumptions")
        prompt_parts.append("2. Explore edge cases and failure modes")
        prompt_parts.append("3. Suggest alternative approaches")
        prompt_parts.append("4. Provide concrete implementation insights")
        prompt_parts.append("5. Assess risks and mitigation strategies")
        
        if request.focus_areas:
            areas = ", ".join(request.focus_areas)
            prompt_parts.append(f"\nFocus especially on: {areas}")
        
        prompt_parts.append("\nBe critical but constructive. Challenge ideas while providing actionable alternatives.")
        
        return "\n".join(prompt_parts)
    
    def _needs_clarification(self, response: str) -> bool:
        """Check if response indicates need for clarification."""
        clarification_markers = [
            "requires_clarification",
            "need more context",
            "additional information needed",
            "please provide"
        ]
        return any(marker in response.lower() for marker in clarification_markers)
    
    def _extract_clarification(self, response: str) -> str:
        """Extract clarification request from response."""
        # Simple extraction - in production, use structured parsing
        import json
        return json.dumps({
            "question": "Additional context needed for thorough analysis",
            "suggested_info": ["Related files", "System architecture", "Constraints"]
        })
    
    def _format_extended_analysis(self, response: str, metadata: Dict) -> str:
        """Format the extended analysis results."""
        header = "# Extended Analysis\n\n"
        
        models = metadata.get("models_used", [])
        if models:
            header += f"**Models Consulted**: {', '.join(models)}\n"
        
        if metadata.get("synthesis"):
            header += "**Synthesis**: Multi-model insights combined\n"
        
        header += "\n---\n\n"
        
        return header + response