from src.app import mcp
from src.database import get_db_connection

def format_solicitud_detalle(sol):
    """Formato limpio y plano para detalle de solicitud."""
    return (
        f"DETALLES DE LA SOLICITUD #{sol['id_solicitud']}\n"
        f"----------------------------------------\n"
        f"Nombre del usuario: {sol['usuario']} (DNI: {sol['dni_usuario']})\n"
        f"Tramite: {sol['tramite']}\n"
        f"Estado actual: {sol['estado_actual']}\n\n"
        f"FECHAS:\n"
        f"  - Inicio: {sol['fecha_inicio']}\n"
        f"  - Fin: {sol['fecha_fin'] if sol['fecha_fin'] else 'En curso'}\n\n"
        f"ULTIMA ACCION:\n"
        f"  - Accion: {sol['ultima_accion'] if sol['ultima_accion'] else 'Sin acciones registradas'}\n"
        f"  - Fecha: {sol['fecha_accion'] if sol['fecha_accion'] else 'N/A'}\n"
        f"----------------------------------------"
    )

@mcp.tool()
def estado_solicitud_por_id(request_id: int) -> str:
    """Consulta el estado y detalles de una solicitud especifica usando su ID."""
    query = """
        SELECT
            r.id AS id_solicitud, u.name AS usuario, u.dni AS dni_usuario,
            p.name AS tramite, r.start_date AS fecha_inicio, r.finish_date AS fecha_fin,
            rs.description AS estado_actual, a.description AS ultima_accion,
            ra.created_at AS fecha_accion
        FROM requests r
        JOIN users u ON r.user_id = u.id
        JOIN procedures p ON r.procedure_id = p.id
        JOIN (
            SELECT rsr1.* FROM request_state_records rsr1
            JOIN (
                SELECT request_id, MAX(date) AS max_date
                FROM request_state_records GROUP BY request_id
            ) latest ON rsr1.request_id = latest.request_id AND rsr1.date = latest.max_date
        ) rsr ON rsr.request_id = r.id
        JOIN request_states rs ON rs.id = rsr.request_status_id
        LEFT JOIN (
            SELECT ra1.* FROM request_actions ra1
            JOIN (
                SELECT request_id, MAX(created_at) AS max_date
                FROM request_actions GROUP BY request_id
            ) latest_ra ON ra1.request_id = latest_ra.request_id AND ra1.created_at = latest_ra.max_date
        ) ra ON ra.request_id = r.id
        LEFT JOIN actions a ON a.id = ra.action_id
        WHERE r.id = %(request_id)s AND r.deleted_at IS NULL;
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, {'request_id': request_id})
        result = cursor.fetchone()
        conn.close()

        if not result:
            return f"No se encontro ninguna solicitud con ID: {request_id}"
        
        return format_solicitud_detalle(result)
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def estado_ultima_solicitud_usuario(dni_usuario: str, nombre_tramite: str) -> str:
    """Consulta el estado de la ultima solicitud de un tramite especifico para un usuario."""
    query = """
        SELECT 
            r.id AS id_solicitud, u.name AS usuario, u.dni AS dni_usuario,
            p.name AS tramite, r.start_date AS fecha_inicio, r.finish_date AS fecha_fin,
            rs.description AS estado_actual, a.description AS ultima_accion,
            ra.created_at AS fecha_accion
        FROM requests r
        JOIN users u ON r.user_id = u.id
        JOIN procedures p ON r.procedure_id = p.id
        JOIN (
            SELECT rsr1.* FROM request_state_records rsr1
            JOIN (
                SELECT request_id, MAX(date) AS max_date
                FROM request_state_records GROUP BY request_id
            ) latest ON rsr1.request_id = latest.request_id AND rsr1.date = latest.max_date
        ) rsr ON rsr.request_id = r.id
        JOIN request_states rs ON rs.id = rsr.request_status_id
        LEFT JOIN (
            SELECT ra1.* FROM request_actions ra1
            JOIN (
                SELECT request_id, MAX(created_at) AS max_date
                FROM request_actions GROUP BY request_id
            ) latest_ra ON ra1.request_id = latest_ra.request_id AND ra1.created_at = latest_ra.max_date
        ) ra ON ra.request_id = r.id
        LEFT JOIN actions a ON a.id = ra.action_id
        WHERE u.dni = %(dni_usuario)s
          AND p.name = %(nombre_tramite)s
          AND r.id = (
              SELECT r2.id FROM requests r2
              JOIN procedures p2 ON r2.procedure_id = p2.id
              WHERE r2.user_id = u.id AND p2.name = %(nombre_tramite)s
              ORDER BY r2.created_at DESC LIMIT 1
          )
          AND r.deleted_at IS NULL;
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, {'dni_usuario': dni_usuario, 'nombre_tramite': nombre_tramite})
        result = cursor.fetchone()
        conn.close()

        if not result:
            return f"No se encontro ninguna solicitud de {nombre_tramite} para el DNI {dni_usuario}."
        
        return format_solicitud_detalle(result)
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def listar_solicitudes_por_dni(dni_usuario: str) -> str:
    """Lista todas las solicitudes realizadas por un usuario especifico usando su DNI."""
    query = """
        SELECT
            r.id AS id_solicitud, u.name AS usuario, p.name AS tramite,
            rs.description AS estado_actual, r.start_date AS fecha_inicio
        FROM requests r
        JOIN users u ON r.user_id = u.id
        JOIN procedures p ON r.procedure_id = p.id
        JOIN (
            SELECT rsr1.* FROM request_state_records rsr1
            JOIN (
                SELECT request_id, MAX(date) AS max_date
                FROM request_state_records GROUP BY request_id
            ) latest ON rsr1.request_id = latest.request_id AND rsr1.date = latest.max_date
        ) rsr ON rsr.request_id = r.id
        JOIN request_states rs ON rs.id = rsr.request_status_id
        WHERE u.dni = %(dni_usuario)s AND r.deleted_at IS NULL
        ORDER BY r.created_at DESC;
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, {'dni_usuario': dni_usuario})
        result = cursor.fetchall()
        conn.close()

        if not result:
            return f"No se encontraron solicitudes para el DNI: {dni_usuario}"

        output = [f"HISTORIAL DE SOLICITUDES - {result[0]['usuario']}\n"]
        for idx, sol in enumerate(result, start=1):
            output.append(
                f"{idx}. Tramite: {sol['tramite']}\n"
                f"   - Numero de la solicitud: {sol['id_solicitud']}\n"
                f"   - Estado: {sol['estado_actual']}\n"
                f"   - Fecha de inicio: {sol['fecha_inicio']}\n"
            )
        return "\n".join(output)
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def consultar_mensajes_solicitud(request_id: int) -> str:
    """Consulta todos los mensajes de la conversacion asociada a una solicitud especifica."""
    query = """
        SELECT 
            m.content AS contenido, ue.name AS emisor, ur.name AS receptor,
            m.created_at AS fecha, m.current_role AS rol
        FROM messages m
        LEFT JOIN users ue ON m.emisor_id = ue.id
        LEFT JOIN users ur ON m.receptor_id = ur.id
        WHERE m.request_id = %(request_id)s
        ORDER BY m.created_at ASC;
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, {'request_id': request_id})
        result = cursor.fetchall()
        conn.close()

        if not result:
            return f"No hay mensajes registrados para la solicitud #{request_id}."

        output = [f"CONVERSACION DE LA SOLICITUD #{request_id}\n"]
        for msg in result:
            output.append(
                f"Fecha: {msg['fecha']}\n"
                f"De: {msg['emisor']} -> Para: {msg['receptor']}\n"
                f"Mensaje: {msg['contenido']}\n"
                f"--------------------"
            )
        return "\n".join(output)
    except Exception as e:
        return f"Error: {e}"