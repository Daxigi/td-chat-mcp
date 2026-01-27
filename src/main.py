from src.app import mcp

# IMPORTANTE: Importar los módulos de herramientas para que se registren los decoradores @mcp.tool()
import src.tools.requests
import src.tools.reports
import src.tools.agents
import src.tools.system

# --- EJECUCIÓN PRINCIPAL (CLI/Stdio) ---
if __name__ == "__main__":
    mcp.run()