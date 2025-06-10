"""
Multi-Model Review Tool - Forces use of multiple models for any task.

This tool ensures the Max Quality Council strategy is used, even for simple tasks.
"""

from typing import Dict, Any
from src.tools.base import BaseTool, ToolOutput
from src.core.task import Task


class MultiModelReviewTool(BaseTool):
    """
    Forces multi-model orchestration for comprehensive review.
    
    Use this when you want multiple AI perspectives on ANY task,
    regardless of complexity.
    """
    
    def __init__(self, orchestrator=None):
        super().__init__(orchestrator)
        self.name = "multi_model_review"
        self.description = (
            "Get multiple AI perspectives on any task. Forces use of Claude, "
            "Gemini, and GPT-4 in parallel, even for simple queries. "
            "Higher cost but maximum insight."
        )
    
    def get_name(self) -> str:
        """Return tool name."""
        return self.name
    
    def get_description(self) -> str:
        """Return tool description."""
        return self.description
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Return the input schema for this tool."""
        return {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The task or question to get multiple perspectives on"
                },
                "code_context": {
                    "type": "string",
                    "description": "Optional code context for analysis"
                },
                "focus_areas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific aspects to focus on (e.g., 'security', 'performance')"
                }
            },
            "required": ["task"]
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolOutput:
        """Execute multi-model review."""
        if not self.orchestrator:
            return ToolOutput(
                status="error",
                content="Orchestrator not initialized"
            )
        
        # Create task with forced council strategy
        task = Task(
            description=arguments.get("task", ""),
            code_context=arguments.get("code_context"),
            session_context={
                "strategy": "max_quality_council",
                "quality_mode": "maximum",
                "force_multi_model": True,
                "focus_areas": arguments.get("focus_areas", [])
            }
        )
        
        try:
            # Force max quality council strategy
            response = await self.orchestrator.orchestrate(
                task, 
                strategy_override="max_quality_council"
            )
            
            # The response now includes usage summary automatically
            return ToolOutput(
                status="success",
                content=response.content,
                content_type="markdown",
                metadata={
                    "models_used": response.metadata.get("strategy", {}).get("models_consulted", []),
                    "total_cost": response.cost,
                    "strategy": "max_quality_council"
                }
            )
            
        except Exception as e:
            return ToolOutput(
                status="error",
                content=f"Multi-model review failed: {str(e)}"
            )