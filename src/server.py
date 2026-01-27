import uvicorn
from mcp.server.sse import SseServerTransport
from src.app import mcp

# IMPORTANTE: Importar las herramientas para que se registren en la instancia mcp
import src.tools.requests
import src.tools.reports
import src.tools.agents
import src.tools.system

# 1. Definimos el transporte SSE
sse = SseServerTransport("/messages")

# 2. Definimos la aplicación ASGI manualmente
async def app(scope, receive, send):
    """
    Aplicación ASGI cruda para manejar MCP sobre SSE.
    """
    if scope["type"] != "http":
        return

    path = scope["path"]
    method = scope["method"]

    # --- RUTA 1: Conexión SSE (GET /sse) ---
    if path == "/sse" and method == "GET":
        async with sse.connect_sse(scope, receive, send) as streams:
            # Iniciamos el servidor MCP usando los streams de lectura/escritura
            await mcp._mcp_server.run(
                streams[0], 
                streams[1], 
                mcp._mcp_server.create_initialization_options()
            )
        return

    # --- RUTA 2: Recepción de Mensajes (POST /messages) ---
    if path == "/messages" and method == "POST":
        await sse.handle_post_message(scope, receive, send)
        return

    # --- 404 Para todo lo demás ---
    await send({
        "type": "http.response.start",
        "status": 404,
        "headers": [(b"content-type", b"text/plain")],
    })
    await send({
        "type": "http.response.body",
        "body": b"Not Found",
    })

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
