from collections import defaultdict
from datetime import datetime
from src.app import mcp
from src.database import get_db_connection

@mcp.tool()
def cantidad_solicitudes_por_estado(nombre_estado: str, nombre_tramite: str = None) -> str:
    """Devuelve las solicitudes del AÑO CORRIENTE agrupadas por trámite en el estado indicado."""
    now = datetime.now()
    fecha_desde = f"{now.year}-01-01"
    fecha_hasta = f"{now.year}-12-31 23:59:59"
    
    query = """
        SELECT p.name AS tramite, COUNT(r.id) as total
        FROM requests r
        JOIN (
            SELECT rsr1.* FROM request_state_records rsr1
            JOIN (
                SELECT request_id, MAX(date) AS max_date
                FROM request_state_records GROUP BY request_id
            ) latest ON rsr1.request_id = latest.request_id AND rsr1.date = latest.max_date
        ) rsr ON rsr.request_id = r.id
        JOIN request_states rs ON rsr.request_status_id = rs.id
        JOIN procedures p ON r.procedure_id = p.id
        WHERE rs.description LIKE %(nombre_estado)s
        AND r.deleted_at IS NULL
        AND r.start_date BETWEEN %(fecha_desde)s AND %(fecha_hasta)s
    """
    params = {'nombre_estado': f"%{nombre_estado}%", 'fecha_desde': fecha_desde, 'fecha_hasta': fecha_hasta}

    if nombre_tramite:
        query += " AND p.name LIKE %(nombre_tramite)s"
        params['nombre_tramite'] = f"%{nombre_tramite}%"

    query += " GROUP BY p.name ORDER BY total DESC"

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            return f"ℹ️ No se encontraron trámites en estado {nombre_estado} para el año {now.year}."

        output = [f"📈 Estadísticas: {nombre_estado} ({now.year})\n"]
        total_general = 0
        for row in results:
            output.append(f"• {row['tramite']}: {row['total']}")
            total_general += row['total']
        
        output.append(f"\n{'─' * 30}\n🏆 Total General: {total_general}")
        return "\n".join(output)
    except Exception as e:
        return f"⚠️ Error: {e}"

@mcp.tool()
def reporte_solicitudes_hoy() -> str:
    """Genera un reporte detallado de todas las solicitudes creadas HOY."""
    query = """
        SELECT
            r.id AS request_id, p.name AS nombre_tramite,
            CONCAT(u.name, ' ', u.surname) AS nombre_usuario,
            rs.description AS estado_actual
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
        WHERE DATE(r.start_date) = CURDATE() AND r.deleted_at IS NULL
        ORDER BY r.created_at ASC;
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        result = cursor.fetchall()
        conn.close()

        if not result:
            return f"No se han registrado nuevas solicitudes el día de hoy ({datetime.now().strftime('%d/%m/%Y')})."

        output_parts = [f"Reporte de Solicitudes - {datetime.now().strftime('%d/%m/%Y')}\n"]
        summary_data = defaultdict(lambda: defaultdict(int))

        for idx, sol in enumerate(result, start=1):
            output_parts.append(
                f"{idx}. Solicitud de: \"{sol['nombre_tramite']}\"\n"
                f"   - Numero de la solicitud: {sol['request_id']}\n"
                f"   - Nombre del usuario: {sol['nombre_usuario']}\n"
                f"   - Estado: {sol['estado_actual']}\n"
            )
            summary_data[sol['nombre_tramite']][sol['estado_actual']] += 1

        # Sección de Resumen
        output_parts.append(f"\n{'═' * 40}")
        output_parts.append(" Resumen por Trámite y Estado\n")
        
        for tramite, states in summary_data.items():
            output_parts.append(f"{tramite}")
            total_tramite = 0
            for estado, count in states.items():
                output_parts.append(f"    {estado}: {count}")
                total_tramite += count
            output_parts.append(f"   Subtotal: {total_tramite}\n")

        return "\n".join(output_parts)
    except Exception as e:
        return f"⚠️ Error al generar reporte: {e}"
