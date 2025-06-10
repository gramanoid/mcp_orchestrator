"""
Quick Claude Tool - Uses only Claude for fast responses.

This tool ensures only Claude is used for maximum speed and minimum cost.
"""

from typing import Dict, Any
from src.tools.base import BaseTool, ToolOutput
from src.core.task import Task


class QuickClaudeTool(BaseTool):
    """
    Uses only Claude for quick, efficient responses.
    
    Best for simple tasks where you want fast answers without
    the overhead of multiple model consultation.
    """
    
    def __init__(self, orchestrator=None):
        super().__init__(orchestrator)
        self.name = "quick_claude"
        self.description = (
            "Get a quick response using only Claude. Fast, efficient, "
            "and cost-effective for simple tasks or when you trust "
            "Claude's judgment alone."
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
                    "description": "The task or question for Claude"
                },
                "code_context": {
                    "type": "string",
                    "description": "Optional code context"
                },
                "thinking_mode": {
                    "type": "string",
                    "enum": ["minimal", "low", "medium", "high", "max"],
                    "description": "Thinking depth (default: medium)"
                }
            },
            "required": ["task"]
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolOutput:
        """Execute quick Claude response."""
        if not self.orchestrator:
            return ToolOutput(
                status="error",
                content="Orchestrator not initialized"
            )
        
        # Create task with forced progressive strategy
        thinking_mode = arguments.get("thinking_mode", "medium")
        task_description = arguments.get("task", "")
        
        # Inject thinking mode into description if specified
        if thinking_mode != "medium":
            task_description = f"Use {thinking_mode} thinking: {task_description}"
        
        task = Task(
            description=task_description,
            code_context=arguments.get("code_context"),
            session_context={
                "strategy": "progressive_deep_dive",
                "force_claude_only": True,
                "thinking_mode": thinking_mode
            }
        )
        
        try:
            # Force progressive strategy (Claude only)
            response = await self.orchestrator.orchestrate(
                task, 
                strategy_override="progressive_deep_dive"
            )
            
            return ToolOutput(
                status="success",
                content=response.content,
                content_type="markdown",
                metadata={
                    "model_used": "claude",
                    "total_cost": response.cost,
                    "strategy": "progressive_deep_dive",
                    "thinking_mode": thinking_mode
                }
            )
            
        except Exception as e:
            return ToolOutput(
                status="error",
                content=f"Quick Claude response failed: {str(e)}"
            )