from src.app import mcp

@mcp.tool()
def list_available_reports() -> str:
    """
    META-HERRAMIENTA DE AYUDA.
    Devuelve la lista de todas las herramientas disponibles en el servidor.
    """
    tools_disponibles = mcp._tool_manager._tools
    
    if not tools_disponibles:
        return "No hay herramientas registradas en el sistema todavía."

    reporte = ["HERRAMIENTAS DISPONIBLES:\n"]

    for nombre_tool, tool_obj in tools_disponibles.items():
        if nombre_tool == "list_available_reports":
            continue
            
        nombre_amigable = nombre_tool.replace("_", " ").capitalize()
        descripcion = (tool_obj.description or "Sin descripcion disponible.").strip()
        
        reporte.append(f"- {nombre_amigable}\n  Descripcion: {descripcion}\n")

    return "\n".join(reporte)