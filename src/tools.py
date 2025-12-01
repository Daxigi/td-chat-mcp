import os
import mysql.connector
from typing import Type, Optional
from collections import defaultdict
from datetime import datetime
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_DATABASE")
    )

# --- HERRAMIENTAS DE CONSULTA PUNTUAL (ID, DNI, USUARIO) ---

class EstadoSolicitudPorIdInput(BaseModel):
    """Input for estado_solicitud_por_id tool."""
    request_id: int = Field(..., description="el ID de la solicitud a consultar")

class EstadoSolicitudPorIdTool(BaseTool):
    name: str = "estado_solicitud_por_id"
    description: str = "Consulta el estado y detalles de una solicitud específica usando su ID."
    args_schema: Type[BaseModel] = EstadoSolicitudPorIdInput

    def _run(self, request_id: int) -> str:
        query = """
            SELECT
                r.id AS id_solicitud,
                u.name AS usuario,
                u.dni AS dni_usuario,
                p.name AS tramite,
                r.start_date AS fecha_inicio,
                r.finish_date AS fecha_fin,
                rs.description AS estado_actual,
                a.description AS ultima_accion,
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
            WHERE r.id = %(request_id)s
              AND r.deleted_at IS NULL;
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, {'request_id': request_id})
            result = cursor.fetchall()
            conn.close()

            if not result:
                return f"No se encontró ninguna solicitud con ID: {request_id}"

            return str(result)
        except Exception as e:
            return f"Error executing query: {e}"

class EstadoUltimaSolicitudUsuarioInput(BaseModel):
    """Input for estado_ultima_solicitud_usuario tool."""
    dni_usuario: str = Field(..., description="el número de DNI del usuario a consultar")
    nombre_tramite: str = Field(..., description="el nombre exacto del trámite a consultar")

class EstadoUltimaSolicitudUsuarioTool(BaseTool):
    name: str = "estado_ultima_solicitud_usuario"
    description: str = "Consulta el estado de la última solicitud de un trámite para un usuario (DNI)."
    args_schema: Type[BaseModel] = EstadoUltimaSolicitudUsuarioInput

    def _run(self, dni_usuario: str, nombre_tramite: str) -> str:
        query = """
            SELECT 
                u.name AS usuario,
                p.name AS tramite,
                r.start_date AS fecha_inicio,
                r.finish_date AS fecha_fin,
                rs.description AS estado_actual,
                a.description AS ultima_accion,
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
                  WHERE r2.user_id = u.id
                    AND p2.name = %(nombre_tramite)s
                  ORDER BY r2.created_at DESC
                  LIMIT 1
              )
              AND r.deleted_at IS NULL;
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, {'dni_usuario': dni_usuario, 'nombre_tramite': nombre_tramite})
            result = cursor.fetchall()
            conn.close()
            return str(result)
        except Exception as e:
            return f"Error executing query: {e}"

class ListarSolicitudesPorDniInput(BaseModel):
    """Input para la herramienta ListarSolicitudesPorDniTool."""
    dni_usuario: str = Field(..., description="el número de DNI del usuario a consultar")

class ListarSolicitudesPorDniTool(BaseTool):
    name: str = "listar_solicitudes_por_dni"
    description: str = "Lista todas las solicitudes realizadas por un usuario específico usando su DNI. Muestra información detallada de cada solicitud incluyendo ID, trámite, fechas, estado actual y última acción."
    args_schema: Type[BaseModel] = ListarSolicitudesPorDniInput

    def _run(self, dni_usuario: str) -> str:
        query = """
            SELECT
                r.id AS id_solicitud,
                u.name AS usuario,
                u.dni AS dni_usuario,
                p.name AS tramite,
                r.start_date AS fecha_inicio,
                r.finish_date AS fecha_fin,
                rs.description AS estado_actual,
                a.description AS ultima_accion,
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
              AND r.deleted_at IS NULL
            ORDER BY r.created_at DESC;
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, {'dni_usuario': dni_usuario})
            result = cursor.fetchall()
            conn.close()

            if not result:
                return f"No se encontraron solicitudes para el usuario con DNI: {dni_usuario}"

            output = f"Solicitudes encontradas para el DNI {dni_usuario} ({result[0]['usuario']}):\n\n"
            for idx, solicitud in enumerate(result, start=1):
                output += f"{idx}. ID Solicitud: {solicitud['id_solicitud']}\n"
                output += f"   Trámite: {solicitud['tramite']}\n"
                output += f"   Estado actual: {solicitud['estado_actual']}\n"
                output += f"   Fecha inicio: {solicitud['fecha_inicio']}\n"
                if solicitud['fecha_fin']:
                    output += f"   Fecha fin: {solicitud['fecha_fin']}\n"
                if solicitud['ultima_accion']:
                    output += f"   Última acción: {solicitud['ultima_accion']} ({solicitud['fecha_accion']})\n"
                output += "\n"

            output += f"Total de solicitudes: {len(result)}"
            return output
        except Exception as e:
            return f"Error al ejecutar la consulta: {e}"

class ConsultarMensajesSolicitudInput(BaseModel):
    """Input para la herramienta ConsultarMensajesSolicitudTool."""
    request_id: int = Field(..., description="el ID de la solicitud para consultar sus mensajes")

class ConsultarMensajesSolicitudTool(BaseTool):
    name: str = "consultar_mensajes_solicitud"
    description: str = "Consulta todos los mensajes de la conversación asociada a una solicitud específica. Muestra el historial completo de mensajes ordenados cronológicamente."
    args_schema: Type[BaseModel] = ConsultarMensajesSolicitudInput

    def _run(self, request_id: int) -> str:
        query = """
            SELECT 
                m.id AS mensaje_id,
                m.tittle AS titulo,
                m.content AS contenido,
                m.emisor_id,
                ue.name AS nombre_emisor,
                m.receptor_id,
                ur.name AS nombre_receptor,
                m.readd AS leido,
                m.send AS enviado,
                m.conversation_id,
                m.created_at AS fecha_creacion,
                m.current_role AS rol_actual
            FROM messages m
            LEFT JOIN users ue ON m.emisor_id = ue.id
            LEFT JOIN users ur ON m.receptor_id = ur.id
            WHERE m.conversation_id = (
                SELECT conversation_id 
                FROM messages 
                WHERE request_id = %(request_id)s 
                LIMIT 1
            )
            ORDER BY m.created_at ASC;
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, {'request_id': request_id})
            result = cursor.fetchall()
            conn.close()

            if not result:
                return f"No se encontraron mensajes para la solicitud con ID: {request_id}"

            conversation_id = result[0]['conversation_id']
            output = f"Mensajes de la conversación ID {conversation_id} (Solicitud #{request_id}):\n"
            output += "=" * 70 + "\n\n"

            for idx, mensaje in enumerate(result, start=1):
                output += f"Mensaje #{idx} (ID: {mensaje['mensaje_id']})\n"
                output += f"Fecha: {mensaje['fecha_creacion']}\n"
                output += f"De: {mensaje['nombre_emisor'] or 'Usuario ' + str(mensaje['emisor_id'])}\n"
                output += f"Para: {mensaje['nombre_receptor'] or 'Usuario ' + str(mensaje['receptor_id'])}\n"
                
                if mensaje['titulo']:
                    output += f"Título: {mensaje['titulo']}\n"
                
                output += f"Contenido: {mensaje['contenido']}\n"
                output += f"Estado: {'Leído' if mensaje['leido'] else 'No leído'} | {'Enviado' if mensaje['enviado'] else 'No enviado'}\n"
                
                if mensaje['rol_actual']:
                    output += f"Rol: {mensaje['rol_actual']}\n"
                
                output += "-" * 70 + "\n\n"

            output += f"Total de mensajes: {len(result)}"
            return output
        except Exception as e:
            return f"Error al ejecutar la consulta: {e}"


# --- HERRAMIENTAS DE REPORTES Y CONTEOS (CONSOLIDADAS) ---
class CantidadSolicitudesPorEstadoInput(BaseModel):
    """Input para la herramienta cantidad_solicitudes_por_estado."""
    nombre_estado: str = Field(..., description="El nombre exacto o parcial del estado a contar (ej: 'En proceso', 'Finalizado').")
    nombre_tramite: Optional[str] = Field(default=None, description="Opcional. Nombre del trámite para filtrar (ej: 'Licencia').")

class CantidadSolicitudesPorEstadoTool(BaseTool):
    name: str = "cantidad_solicitudes_por_estado"
    description: str = (
        "Herramienta PRINCIPAL para reportes. "
        "Devuelve las solicitudes del AÑO CORRIENTE (1 Ene a 31 Dic del año actual) agrupadas por trámite en el estado indicado. "
        "No requiere fechas, calcula automáticamente el año actual."
    )
    args_schema: Type[BaseModel] = CantidadSolicitudesPorEstadoInput

    def _run(self, nombre_estado: str, nombre_tramite: Optional[str] = None) -> str:
        # --- Lógica de AÑO CORRIENTE Automática ---
        now = datetime.now()
        current_year = now.year
        
        # Fijamos el rango desde el 1 de Enero hasta el 31 de Diciembre del año en curso
        fecha_desde = f"{current_year}-01-01"
        fecha_hasta = f"{current_year}-12-31 23:59:59"
        
        rango_msg = f"del año {current_year}"

        # --- Construcción de la consulta con GROUP BY ---
        query = """
            SELECT p.name AS tramite, COUNT(r.id) as total
            FROM requests r
            JOIN request_state_records rsr ON r.id = rsr.request_id
            JOIN request_states rs ON rsr.request_status_id = rs.id
            JOIN procedures p ON r.procedure_id = p.id
            WHERE rsr.id = (
                SELECT MAX(sub_rsr.id)
                FROM request_state_records sub_rsr
                WHERE sub_rsr.request_id = r.id
            )
            AND rs.description LIKE %(nombre_estado)s
            AND r.deleted_at IS NULL
            AND r.start_date BETWEEN %(fecha_desde)s AND %(fecha_hasta)s
        """
        
        params = {
            'nombre_estado': f"%{nombre_estado}%",
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta
        }

        if nombre_tramite:
            query += " AND p.name LIKE %(nombre_tramite)s"
            params['nombre_tramite'] = f"%{nombre_tramite}%"

        # Agrupamos por trámite para el desglose
        query += " GROUP BY p.name ORDER BY total DESC"

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            results = cursor.fetchall()
            conn.close()
            
            # --- Formateo de la salida CON SALTOS DE LÍNEA FORZADOS ---
            if not results:
                filtros_txt = f"del trámite '{nombre_tramite}'" if nombre_tramite else ""
                return f"No se encontraron solicitudes en estado '{nombre_estado}' {filtros_txt} en el año {current_year}."

            # Encabezado
            output = f"Las solicitudes en estado \"{nombre_estado}\" {rango_msg} son las siguientes:\n\n"
            
            total_general = 0
            for i, row in enumerate(results, 1):
                tramite = row['tramite']
                count = row['total']
                total_general += count
                unit = "solicitud" if count == 1 else "solicitudes"
                
                # AQUI ESTA LA CORRECCIÓN: \n\n asegura el espacio en blanco visual
                output += f"{i}. {tramite}: {count} {unit}\n\n"
            
            # Total separado también
            output += f"Total: {total_general}"
            
            return output

        except Exception as e:
            return f"Error al ejecutar la consulta: {e}"

class ReporteSolicitudesHoyInput(BaseModel):
    """Input for ReporteSolicitudesHoyTool."""
    pass

class ReporteSolicitudesHoyTool(BaseTool):
    name: str = "reporte_solicitudes_hoy"
    description: str = "Genera un reporte RÁPIDO de todas las solicitudes creadas HOY. Muestra resumen y detalles."
    args_schema: Type[BaseModel] = ReporteSolicitudesHoyInput

    def _run(self) -> str:
        query = """
            SELECT
                r.id AS request_id,
                p.name AS nombre_tramite,
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
            WHERE DATE(r.start_date) = CURDATE()
              AND r.deleted_at IS NULL
            ORDER BY r.created_at ASC;
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query)
            result = cursor.fetchall()
            conn.close()

            if not result:
                return "No se encontraron solicitudes creadas hoy."

            output_parts = ["Solicitudes de hoy:\n\n"]
            summary_data = defaultdict(lambda: defaultdict(int))

            for idx, solicitud in enumerate(result, start=1):
                output_parts.append(
                    f"{idx}. {solicitud['nombre_tramite']} - {solicitud['nombre_usuario']} ({solicitud['estado_actual']})\n"
                )
                summary_data[solicitud['nombre_tramite']][solicitud['estado_actual']] += 1

            output_parts.append("\nResumen:\n")
            for trámite, estados in summary_data.items():
                total = sum(estados.values())
                output_parts.append(f"- {trámite}: {total} (")
                detalles = [f"{k}: {v}" for k, v in estados.items()]
                output_parts.append(", ".join(detalles) + ")\n")

            return "".join(output_parts)

        except Exception as e:
            return f"Error al ejecutar la consulta: {e}"

# --- HERRAMIENTAS ADMINISTRATIVAS Y DE AGENTES ---

class ObtenerRolesUsuarioInput(BaseModel):
    """Input para la herramienta obtener_roles_usuario."""
    dni_usuario: str = Field(..., description="DNI del usuario a consultar.")

class ObtenerRolesUsuarioTool(BaseTool):
    name: str = "obtener_roles_usuario"
    description: str = "Obtiene los roles asociados a un usuario a través de su DNI."
    args_schema: Type[BaseModel] = ObtenerRolesUsuarioInput

    def _run(self, dni_usuario: str) -> str:
        dni_limpio = str(dni_usuario).strip()
        query = r"""
            SELECT r.name AS rol
            FROM users u
            JOIN model_has_roles mhr ON mhr.model_id = u.id AND mhr.model_type = %(m_type)s
            JOIN roles r ON r.id = mhr.role_id
            WHERE u.dni = %(dni)s;
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, {'dni': dni_limpio, 'm_type': r'App\Models\User'})
            result = cursor.fetchall()
            conn.close()
            
            if not result: return f"No se encontraron roles para el DNI: {dni_limpio}"
            roles = [row['rol'] for row in result]
            return f"El usuario {dni_limpio} tiene roles: {', '.join(roles)}"
        except Exception as e:
            return f"Error: {e}"

class ListarUsuariosPorRolInput(BaseModel):
    """Input para la herramienta ListarUsuariosPorRolTool."""
    nombre_rol: str = Field(..., description="el nombre exacto del rol a consultar")

class ListarUsuariosPorRolTool(BaseTool):
    name: str = "listar_usuarios_por_rol"
    description: str = "Lista a todos los usuarios que tienen un rol específico."
    args_schema: Type[BaseModel] = ListarUsuariosPorRolInput

    def _run(self, nombre_rol: str) -> str:
        query = """
            SELECT u.name, u.dni
            FROM users u
            JOIN model_has_roles mhr ON u.id = mhr.model_id AND mhr.model_type = %(model_type)s
            JOIN roles r ON r.id = mhr.role_id
            WHERE r.name = %(nombre_rol)s;
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, {'nombre_rol': nombre_rol, 'model_type': r'App\Models\User'})
            result = cursor.fetchall()
            conn.close()

            if not result: return f"No se encontraron usuarios con rol '{nombre_rol}'."
            return "\n".join([f"{row['name']} (DNI: {row['dni']})" for row in result])
        except Exception as e:
            return f"Error: {e}"

class ConsultarAtencionesAgenteInput(BaseModel):
    """Input para ConsultarAtencionesAgenteTool."""
    dni_agente: str = Field(..., description="DNI del agente")
    fecha_inicio: str = Field(..., description="Inicio (YYYY-MM-DD HH:MM:SS)")
    fecha_fin: str = Field(..., description="Fin (YYYY-MM-DD HH:MM:SS)")

class ConsultarAtencionesAgenteTool(BaseTool):
    name: str = "consultar_atenciones_agente"
    description: str = "Consulta productividad de un agente (cambios de estado realizados) en un periodo."
    args_schema: Type[BaseModel] = ConsultarAtencionesAgenteInput

    def _run(self, dni_agente: str, fecha_inicio: str, fecha_fin: str) -> str:
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
            if not result: return "No se encontraron atenciones en ese periodo."
            return str(result)
        except Exception as e: return f"Error: {e}"

class ConsultarAtencionesAgentePorTramiteInput(BaseModel):
    """Input para ConsultarAtencionesAgentePorTramiteTool."""
    dni_agente: str = Field(..., description="DNI del agente")
    nombre_tramite: str = Field(..., description="Nombre del trámite")
    fecha_inicio: str = Field(..., description="Inicio")
    fecha_fin: str = Field(..., description="Fin")

class ConsultarAtencionesAgentePorTramiteTool(BaseTool):
    name: str = "consultar_atenciones_agente_por_tramite"
    description: str = "Igual que consultar_atenciones_agente pero filtrando por un trámite específico."
    args_schema: Type[BaseModel] = ConsultarAtencionesAgentePorTramiteInput

    def _run(self, dni_agente: str, nombre_tramite: str, fecha_inicio: str, fecha_fin: str) -> str:
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
            if not result: return "No se encontraron datos."
            return str(result)
        except Exception as e: return f"Error: {e}"

class ListAvailableReportsInput(BaseModel):
    """Input for list_available_reports tool."""
    pass

class ListAvailableReportsTool(BaseTool):
    name: str = "list_available_reports"
    description: str = "Lista las capacidades de reporte disponibles."
    args_schema: Type[BaseModel] = ListAvailableReportsInput
    tools_registry: dict = {}

    def __init__(self, tools_registry: dict = None):
        super().__init__()
        if tools_registry:
            self.tools_registry = tools_registry

    def _run(self) -> str:
        if not self.tools_registry: return "No registry available."
        output = "Available reports:\n"
        for idx, (t_name, t_inst) in enumerate(self.tools_registry.items(), 1):
            if t_name != "list_available_reports":
                output += f"{idx}. {t_name}: {t_inst.description}\n"
        return output