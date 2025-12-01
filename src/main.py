from fastapi import FastAPI, HTTPException
from typing import List
import traceback
import inspect
from crewai.tools import BaseTool

from .models import ToolExecutionRequest, ToolExecutionResponse
from . import tools

# --- App Initialization ---
app = FastAPI(
    title="MCP Server",
    description="A server exposing tools compatible with the Model Context Protocol.",
    version="1.0.0",
)

# --- Tool Registry ---
tools_registry = {}
# Dynamically discover and register tools from the 'tools' module
for name, cls in inspect.getmembers(tools, inspect.isclass):
    if issubclass(cls, BaseTool) and cls is not BaseTool:
        # Special handling for ListAvailableReportsTool, which needs the registry
        if cls is tools.ListAvailableReportsTool:
            continue
        instance = cls()
        tools_registry[instance.name] = instance

# Add ListAvailableReportsTool at the end, passing the populated registry
if 'ListAvailableReportsTool' in dir(tools):
    # The registry is passed to the tool, so it can list the other tools
    tools_registry["list_available_reports"] = tools.ListAvailableReportsTool(tools_registry=tools_registry)

# --- API Endpoints ---

@app.get("/", summary="Server Status")
def read_root():
    """Returns a simple status message indicating the server is running."""
    return {"status": "MCP Server is running"}

@app.get("/tools", summary="List Available Tools")
def list_tools() -> List[dict]:
    """Returns a list of available tools with their MCP-compatible schema."""
    tool_schemas = []
    for tool_name, tool in tools_registry.items():
        # Ensure the tool has the necessary attributes
        if hasattr(tool, 'name') and hasattr(tool, 'description') and hasattr(tool, 'args_schema'):
            tool_schemas.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "args_schema": tool.args_schema.model_json_schema(),
                }
            )
    return tool_schemas

@app.post("/tools/execute", summary="Execute a Tool")
async def execute_tool(request: ToolExecutionRequest) -> ToolExecutionResponse:
    """Executes a specified tool with the given arguments."""
    tool = tools_registry.get(request.tool_name)

    if not tool:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{request.tool_name}' not found. Available tools: {list(tools_registry.keys())}",
        )

    try:
        print(f"Using Tool: {request.tool_name}")
        print(f"Arguments: {request.args}")
        result = tool.run(**request.args)
        return ToolExecutionResponse(result=str(result))
    except Exception as e:
        print("--- AN ERROR OCCURRED ---")
        print(f"Tool: {request.tool_name}")
        print(f"Args: {request.args}")
        print(f"Error: {str(e)}")
        traceback.print_exc()
        print("-------------------------")
        raise HTTPException(
            status_code=500, detail=f"An error occurred while executing the tool: {e}"
        )
