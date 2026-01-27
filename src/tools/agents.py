from src.app import mcp
from src.database import get_db_connection

@mcp.tool()
def consultar_atenciones_agente(dni_agente: str, fecha_inicio: str, fecha_fin: str) -> str:
    """Consulta productividad de un agente en un periodo determinado."""
    query = """
        SELECT p.name AS nombre_tramite, rs.description AS estado, COUNT(*) AS total_cambios
        FROM request_state_records rsr
        JOIN users u ON rsr.user_id = u.id
        JOIN request_states rs ON rsr.request_status_id = rs.id
        JOIN requests r ON rsr.request_id = r.id
        JOIN procedures p ON r.procedure_id = p.id
        WHERE u.dni = %(dni_agente)s
          AND rsr.created_at BETWEEN %(fecha_inicio)s AND %(fecha_fin)s
          AND rsr.request_status_id NOT IN (0, 1, 2)
        GROUP BY p.name, rs.description
        ORDER BY p.name, COUNT(*) DESC;
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, {'dni_agente': dni_agente, 'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin})
        result = cursor.fetchall()
        conn.close()

        if not result:
            return f"No se registraron atenciones para el agente con DNI {dni_agente} en este periodo."

        output = [f"PRODUCTIVIDAD DEL AGENTE (DNI: {dni_agente})\n"]
        current_tramite = None
        for row in result:
            if row['nombre_tramite'] != current_tramite:
                current_tramite = row['nombre_tramite']
                output.append(f"\nTRAMITE: {current_tramite}")
            output.append(f"   - {row['estado']}: {row['total_cambios']}")
        
        return "\n".join(output)
    except Exception as e: return f"Error: {e}"

@mcp.tool()
def consultar_atenciones_agente_por_tramite(dni_agente: str, nombre_tramite: str, fecha_inicio: str, fecha_fin: str) -> str:
    """Consulta productividad de un agente filtrando por un trámite específico."""
    query = """
        SELECT rs.description AS estado, COUNT(*) AS total_cambios
        FROM request_state_records rsr
        JOIN users u ON rsr.user_id = u.id
        JOIN request_states rs ON rsr.request_status_id = rs.id
        JOIN requests r ON rsr.request_id = r.id
        JOIN procedures p ON r.procedure_id = p.id
        WHERE u.dni = %(dni_agente)s
          AND rsr.created_at BETWEEN %(fecha_inicio)s AND %(fecha_fin)s
          AND rsr.request_status_id NOT IN (0, 1, 2)
          AND p.name = %(nombre_tramite)s
        GROUP BY rs.description
        ORDER BY COUNT(*) DESC;
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, {'dni_agente': dni_agente, 'nombre_tramite': nombre_tramite, 'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin})
        result = cursor.fetchall()
        conn.close()

        if not result:
            return f"No hay datos para el tramite {nombre_tramite} con este agente."

        output = [f"PRODUCTIVIDAD: {nombre_tramite}\nAgente DNI: {dni_agente}\n"]
        for row in result:
            output.append(f"   - {row['estado']}: {row['total_cambios']}")
        
        return "\n".join(output)
    except Exception as e:
        return f"Error: {e}"
