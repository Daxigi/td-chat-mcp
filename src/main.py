from fastapi import FastAPI, HTTPException
from typing import List
import traceback
from .models import ToolExecutionRequest, ToolExecutionResponse
from .tools import (
    EstadoSolicitudPorIdTool,
    EstadoUltimaSolicitudUsuarioTool,
    ConteoEstadosTramiteEspecificoTool,
    SolicitudesPorEstadoTool,
    ListAvailableReportsTool,
    ObtenerRolesUsuarioTool,
    ListarUsuariosPorRolTool,
    ConsultarAtencionesAgenteTool,
    ConsultarAtencionesAgentePorTramiteTool,
    ListarSolicitudesPorDniTool,
    ConsultarMensajesSolicitudTool,
    SolicitudesTramiteHoyTool,
)

# --- App Initialization ---
app = FastAPI(
    title="MCP Server",
    description="A server exposing tools compatible with the Model Context Protocol.",
    version="1.0.0",
)

# --- Tool Registry ---
# CORRECCIÓN: Crear primero el registry sin list_available_reports
tools_registry = {
    "estado_solicitud_por_id": EstadoSolicitudPorIdTool(),
    "estado_ultima_solicitud_usuario": EstadoUltimaSolicitudUsuarioTool(),
    "conteo_estados_tramite_especifico": ConteoEstadosTramiteEspecificoTool(),
    "solicitudes_por_estado": SolicitudesPorEstadoTool(),
    "obtener_roles_usuario": ObtenerRolesUsuarioTool(),
    "listar_usuarios_por_rol": ListarUsuariosPorRolTool(),
    "consultar_atenciones_agente": ConsultarAtencionesAgenteTool(),
    "consultar_atenciones_agente_por_tramite": ConsultarAtencionesAgentePorTramiteTool(),
    "listar_solicitudes_por_dni": ListarSolicitudesPorDniTool(),
    "consultar_mensajes_solicitud": ConsultarMensajesSolicitudTool(),
    "solicitudes_tramite_hoy": SolicitudesTramiteHoyTool(),
}

# CORRECCIÓN: Luego añadir list_available_reports con el registry completo
tools_registry["list_available_reports"] = ListAvailableReportsTool(tools_registry=tools_registry)

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
        print(f"Using Tool: {request.tool_name}")  # Imprimimos para confirmar
        print(f"Arguments: {request.args}")  # AGREGADO: Debug de argumentos
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