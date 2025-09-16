from fastapi import FastAPI, HTTPException
from typing import List

from .models import ToolExecutionRequest, ToolExecutionResponse
from .tools import (
    EstadoUltimaSolicitudUsuarioTool,
    ConteoEstadosTramiteEspecificoTool,
    SolicitudesPorEstadoTool,
    ListAvailableReportsTool,
)

# --- App Initialization ---
app = FastAPI(
    title="MCP Server",
    description="A server exposing tools compatible with the Model Context Protocol.",
    version="1.0.0",
)

# --- Tool Registry ---
# Instantiate and register all available tools
tools_registry = {
    "estado_ultima_solicitud_usuario": EstadoUltimaSolicitudUsuarioTool(),
    "conteo_estados_tramite_especifico": ConteoEstadosTramiteEspecificoTool(),
    "solicitudes_por_estado": SolicitudesPorEstadoTool(),
    "list_available_reports": ListAvailableReportsTool(),
}

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
        # The `run` method of BaseTool handles Pydantic model validation and calls `_run`
        result = tool.run(request.args)
        return ToolExecutionResponse(result=str(result))
    except Exception as e:
        # Catch any exception during tool execution and return a 500 error
        raise HTTPException(
            status_code=500, detail=f"An error occurred while executing the tool: {e}"
        )
ption(
            status_code=500, detail=f"An error occurred while executing the tool: {e}"
        )
