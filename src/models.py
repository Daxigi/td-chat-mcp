from pydantic import BaseModel
from typing import Optional, Dict, Any

class ToolExecutionRequest(BaseModel):
    """Request body for executing a tool."""
    tool_name: str
    args: Dict[str, Any]

class ToolExecutionResponse(BaseModel):
    """Response body for a tool execution."""
    result: str
    error: Optional[str] = None
