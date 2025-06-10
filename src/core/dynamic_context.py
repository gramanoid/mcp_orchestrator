"""
Dynamic context request system for collaborative problem-solving.

Allows LLMs to request additional context mid-execution.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class RequestStatus(Enum):
    """Status of a tool execution."""
    SUCCESS = "success"
    ERROR = "error"
    REQUIRES_CLARIFICATION = "requires_clarification"


@dataclass
class ClarificationRequest:
    """Request for additional context or information."""
    question: str
    files_needed: Optional[List[str]] = None
    context_type: Optional[str] = None
    suggested_next_action: Optional[Dict[str, Any]] = None


@dataclass
class ToolResponse:
    """Standardized response format for all tools."""
    status: RequestStatus
    content: str
    content_type: str = "text"  # text, markdown, json
    metadata: Optional[Dict[str, Any]] = None
    clarification_request: Optional[ClarificationRequest] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        result = {
            "status": self.status.value,
            "content": self.content,
            "content_type": self.content_type,
        }
        
        if self.metadata:
            result["metadata"] = self.metadata
            
        if self.clarification_request:
            result["clarification"] = {
                "question": self.clarification_request.question,
                "files_needed": self.clarification_request.files_needed,
                "context_type": self.clarification_request.context_type,
                "suggested_next_action": self.clarification_request.suggested_next_action
            }
            
        return result


class DynamicContextManager:
    """Manages dynamic context requests between LLMs."""
    
    def __init__(self):
        self.pending_requests: List[ClarificationRequest] = []
        self.context_history: List[Dict[str, Any]] = []
    
    def add_request(self, request: ClarificationRequest) -> None:
        """Add a clarification request."""
        self.pending_requests.append(request)
        self.context_history.append({
            "type": "request",
            "request": request,
            "timestamp": self._get_timestamp()
        })
    
    def resolve_request(self, request: ClarificationRequest, resolution: Dict[str, Any]) -> None:
        """Resolve a clarification request with provided context."""
        if request in self.pending_requests:
            self.pending_requests.remove(request)
        
        self.context_history.append({
            "type": "resolution",
            "request": request,
            "resolution": resolution,
            "timestamp": self._get_timestamp()
        })
    
    def has_pending_requests(self) -> bool:
        """Check if there are pending clarification requests."""
        return len(self.pending_requests) > 0
    
    def get_next_request(self) -> Optional[ClarificationRequest]:
        """Get the next pending clarification request."""
        return self.pending_requests[0] if self.pending_requests else None
    
    def parse_llm_response(self, response: str) -> ToolResponse:
        """
        Parse LLM response to check for clarification requests.
        
        If response contains JSON with status="requires_clarification",
        parse it as a clarification request.
        """
        import json
        
        # Try to parse as JSON clarification request
        try:
            # Look for JSON in the response
            if "{" in response and "requires_clarification" in response:
                # Extract JSON from response
                start = response.find("{")
                end = response.rfind("}") + 1
                json_str = response[start:end]
                
                data = json.loads(json_str)
                
                if data.get("status") == "requires_clarification":
                    clarification = ClarificationRequest(
                        question=data.get("question", ""),
                        files_needed=data.get("files_needed", []),
                        context_type=data.get("context_type"),
                        suggested_next_action=data.get("suggested_next_action")
                    )
                    
                    return ToolResponse(
                        status=RequestStatus.REQUIRES_CLARIFICATION,
                        content=json.dumps(data),
                        content_type="json",
                        clarification_request=clarification
                    )
        except (json.JSONDecodeError, KeyError):
            # Not a clarification request, treat as normal response
            pass
        
        # Normal response
        return ToolResponse(
            status=RequestStatus.SUCCESS,
            content=response,
            content_type="markdown" if "```" in response else "text"
        )
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat()