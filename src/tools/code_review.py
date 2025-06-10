"""
Code Review Tool - Professional code analysis with multi-model insights.
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.tools.base import BaseTool, ToolOutput, ToolRequest
from src.core.task import Task
from src.utils.file_utils import FileManager


logger = logging.getLogger(__name__)


class CodeReviewRequest(ToolRequest):
    """Request model for code review."""
    files: List[str] = []
    review_type: str = "full"  # full|security|performance|quick
    focus_areas: Optional[List[str]] = None
    severity_filter: str = "all"  # all|high|critical


class CodeReviewTool(BaseTool):
    """
    Professional code review tool using multi-model orchestration.
    
    Leverages different models for comprehensive analysis:
    - Security vulnerabilities
    - Performance issues
    - Code quality and maintainability
    - Best practices adherence
    """
    
    def get_name(self) -> str:
        return "review_code"
    
    def get_description(self) -> str:
        return (
            "Get Gemini 2.5 Pro and O3 to review code. "
            "They identify additional bugs, security issues, and improvements "
            "that complement Claude's analysis."
        )
    
    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Files or directories to review"
                },
                "review_type": {
                    "type": "string",
                    "enum": ["full", "security", "performance", "quick"],
                    "default": "full"
                },
                "focus_areas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific areas to focus on"
                },
                "severity_filter": {
                    "type": "string",
                    "enum": ["all", "high", "critical"],
                    "default": "all"
                }
            },
            "required": ["files"]
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolOutput:
        """Execute code review using orchestration strategies."""
        try:
            request = CodeReviewRequest(**arguments)
            
            # Read files using file manager
            file_manager = FileManager()
            file_contents = await file_manager.read_files(request.files)
            
            if not file_contents:
                return ToolOutput(
                    status="error",
                    content="No files found to review",
                    content_type="text"
                )
            
            # Create review task
            review_prompt = self._build_review_prompt(request, file_contents)
            
            task = Task(
                description=review_prompt,
                session_context={
                    "tool": "code_review",
                    "review_type": request.review_type,
                    "files_count": len(file_contents)
                }
            )
            
            # Use appropriate strategy based on review type
            if request.review_type == "security":
                # Use council for security - multiple perspectives
                result = await self.orchestrator.orchestrate(
                    task, 
                    strategy_override="max_quality_council"
                )
            elif request.review_type == "quick":
                # Use single fast model for quick review
                # Add quick flag to session context
                task.session_context["quick_review"] = True
                result = await self.orchestrator.orchestrate(
                    task,
                    strategy_override="progressive_deep_dive"
                )
            else:
                # Full review with progressive strategy
                result = await self.orchestrator.orchestrate(
                    task,
                    strategy_override="progressive_deep_dive"
                )
            
            # Format the response
            formatted_content = self._format_review_results(
                result.content, 
                request
            )
            
            return ToolOutput(
                status="success",
                content=formatted_content,
                content_type="markdown",
                metadata={
                    "models_used": result.metadata.get("models_used", []),
                    "files_reviewed": len(file_contents),
                    "review_type": request.review_type
                }
            )
            
        except Exception as e:
            logger.error(f"Code review failed: {e}")
            return ToolOutput(
                status="error",
                content=f"Code review failed: {str(e)}",
                content_type="text"
            )
    
    def _build_review_prompt(self, request: CodeReviewRequest, 
                           file_contents: Dict[str, str]) -> str:
        """Build the review prompt."""
        prompt_parts = [
            "Perform a professional code review of the following files."
        ]
        
        if request.review_type == "security":
            prompt_parts.append(
                "Focus on security vulnerabilities, authentication issues, "
                "and potential attack vectors."
            )
        elif request.review_type == "performance":
            prompt_parts.append(
                "Focus on performance bottlenecks, inefficient algorithms, "
                "and optimization opportunities."
            )
        
        if request.focus_areas:
            areas = ", ".join(request.focus_areas)
            prompt_parts.append(f"Pay special attention to: {areas}")
        
        prompt_parts.append("\nProvide feedback with severity ratings:")
        prompt_parts.append("- 🔴 CRITICAL: Security vulnerabilities, data loss")
        prompt_parts.append("- 🟠 HIGH: Bugs, performance issues")
        prompt_parts.append("- 🟡 MEDIUM: Code smells, maintainability")
        prompt_parts.append("- 🟢 LOW: Style issues, minor improvements")
        
        if request.severity_filter != "all":
            prompt_parts.append(
                f"\nOnly report issues of {request.severity_filter} severity or higher."
            )
        
        prompt_parts.append("\n\nFiles to review:")
        
        for filepath, content in file_contents.items():
            prompt_parts.append(f"\n--- {filepath} ---")
            prompt_parts.append(content)
            prompt_parts.append("--- END FILE ---\n")
        
        return "\n".join(prompt_parts)
    
    def _format_review_results(self, response: str, 
                             request: CodeReviewRequest) -> str:
        """Format review results with proper structure."""
        header = f"# Code Review Report\n\n"
        header += f"**Type**: {request.review_type.title()}\n"
        
        if request.focus_areas:
            header += f"**Focus Areas**: {', '.join(request.focus_areas)}\n"
        
        header += f"**Severity Filter**: {request.severity_filter}\n\n"
        
        return header + response