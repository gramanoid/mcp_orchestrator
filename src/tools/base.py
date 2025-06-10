"""
Base class for MCP tools.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class ToolRequest(BaseModel):
    """Base request model for all tools."""
    temperature: Optional[float] = Field(None, description="Temperature for response")
    thinking_mode: Optional[str] = Field(
        None, 
        description="Thinking depth: minimal|low|medium|high|max"
    )


class ToolOutput(BaseModel):
    """Standardized output format for all tools."""
    status: str = Field(..., description="success|error|requires_clarification")
    content: str = Field(..., description="The main content/response")
    content_type: str = Field("text", description="text|markdown|json")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class BaseTool(ABC):
    """Abstract base class for MCP tools."""
    
    def __init__(self, orchestrator):
        """Initialize with orchestrator instance."""
        self.orchestrator = orchestrator
    
    @abstractmethod
    def get_name(self) -> str:
        """Return tool name."""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Return tool description."""
        pass
    
    @abstractmethod
    def get_input_schema(self) -> Dict[str, Any]:
        """Return JSON schema for tool inputs."""
        pass
    
    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> ToolOutput:
        """Execute the tool with given arguments."""
        pass