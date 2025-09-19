import os
import mysql.connector
from typing import Type
from pydantic import BaseModel, Field
from crewai.tools.base_tool import BaseTool
from dotenv import load_dotenv
import inspect


load_dotenv()

def get_db_connection(model_type: str = None):
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_DATABASE")
    )

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

class ConteoEstadosTramiteEspecificoInput(BaseModel):
    """Input for conteo_estados_tramite_especifico tool."""
    nombre_tramite: str = Field(..., description="el nombre exacto del trámite que se desea consultar")
    fecha_inicio: str = Field(..., description="la fecha y hora de inicio del período (formato AAAA-MM-DD HH:MM:SS)")
    fecha_fin: str = Field(..., description="la fecha y hora de fin del período (formato AAAA-MM-DD HH:MM:SS)")

class ConteoEstadosTramiteEspecificoTool(BaseTool):
    name: str = "conteo_estados_tramite_especifico"
    description: str = "Cuenta las solicitudes y sus estados para un trámite y rango de fechas."
    args_schema: Type[BaseModel] = ConteoEstadosTramiteEspecificoInput

    def _run(self, nombre_tramite: str, fecha_inicio: str, fecha_fin: str) -> str:
        query = """
            WITH ultimo_estado AS (
                SELECT r.id AS request_id, p.name AS tramite, rs.description AS estado,
                       ROW_NUMBER() OVER (PARTITION BY r.id ORDER BY rsr.date DESC) AS rn
                FROM requests r
                JOIN procedures p ON r.procedure_id = p.id
                JOIN request_state_records rsr ON rsr.request_id = r.id
                JOIN request_states rs ON rsr.request_status_id = rs.id
                WHERE p.name = %(nombre_tramite)s
                  AND r.start_date BETWEEN %(fecha_inicio)s AND %(fecha_fin)s
                  AND r.deleted_at IS NULL
            )
            SELECT tramite,
                   SUM(CASE WHEN estado = 'Borrador' THEN 1 ELSE 0 END) AS borrador,
                   SUM(CASE WHEN estado = 'Publicado' THEN 1 ELSE 0 END) AS publicado,
                   SUM(CASE WHEN estado = 'En proceso' THEN 1 ELSE 0 END) AS en_proceso,
                   SUM(CASE WHEN estado = 'Finalizado' THEN 1 ELSE 0 END) AS finalizado,
                   SUM(CASE WHEN estado = 'Rechazado' THEN 1 ELSE 0 END) AS rechazado,
                   SUM(CASE WHEN estado = 'Revocado' THEN 1 ELSE 0 END) AS revocado,
                   COUNT(*) AS total
            FROM ultimo_estado WHERE rn = 1 GROUP BY tramite ORDER BY tramite;
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, {'nombre_tramite': nombre_tramite, 'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin})
            result = cursor.fetchall()
            conn.close()
            return str(result)
        except Exception as e:
            return f"Error executing query: {e}"

class SolicitudesPorEstadoInput(BaseModel):
    """Input for solicitudes_por_estado tool."""
    fecha_inicio: str = Field(..., description="la fecha y hora de inicio del período (formato AAAA-MM-DD HH:MM:SS)")
    fecha_fin: str = Field(..., description="la fecha y hora de fin del período (formato AAAA-MM-DD HH:MM:SS)")

class SolicitudesPorEstadoTool(BaseTool):
    name: str = "solicitudes_por_estado"
    description: str = "Cuenta las solicitudes y sus estados para todos los trámites en un rango de fechas."
    args_schema: Type[BaseModel] = SolicitudesPorEstadoInput

    def _run(self, fecha_inicio: str, fecha_fin: str) -> str:
        query = """
            WITH ultimo_estado AS (
                SELECT r.id AS request_id, p.name AS tramite, rs.description AS estado,
                       ROW_NUMBER() OVER (PARTITION BY r.id ORDER BY rsr.date DESC) AS rn
                FROM requests r
                JOIN request_state_records rsr ON rsr.request_id = r.id
                JOIN request_states rs ON rsr.request_status_id = rs.id
                JOIN procedures p ON p.id = r.procedure_id
                WHERE r.created_at BETWEEN %(fecha_inicio)s AND %(fecha_fin)s
                  AND r.deleted_at IS NULL
            )
            SELECT tramite,
                   SUM(CASE WHEN estado = 'Borrador' THEN 1 ELSE 0 END) AS borrador,
                   SUM(CASE WHEN estado = 'Publicado' THEN 1 ELSE 0 END) AS publicado,
                   SUM(CASE WHEN estado = 'En proceso' THEN 1 ELSE 0 END) AS en_proceso,
                   SUM(CASE WHEN estado = 'Finalizado' THEN 1 ELSE 0 END) AS finalizado,
                   SUM(CASE WHEN estado = 'Rechazado' THEN 1 ELSE 0 END) AS rechazado,
                   SUM(CASE WHEN estado = 'Revocado' THEN 1 ELSE 0 END) AS revocado,
                   COUNT(*) AS total
            FROM ultimo_estado WHERE rn = 1 GROUP BY tramite ORDER BY tramite;
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, {'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin})
            result = cursor.fetchall()
            conn.close()
            return str(result)
        except Exception as e:
            return f"Error executing query: {e}"

# CORRECCIÓN 1: Input vacío pero válido
class ListAvailableReportsInput(BaseModel):
    """Input for list_available_reports tool."""
    # No hay campos requeridos, pero el modelo debe existir

# CORRECCIÓN 2: Herramienta corregida
class ListAvailableReportsTool(BaseTool):
    name: str = "list_available_reports"
    description: str = "Útil para cuando el usuario pregunta qué reportes, trámites o 'tramites' conoces o puedes hacer."
    args_schema: Type[BaseModel] = ListAvailableReportsInput

    def __init__(self, tools_registry: dict = None):
        """Inicializar la herramienta con el registro de herramientas"""
        super().__init__()
        self._tools_registry = tools_registry or {}

    def _run(self) -> str:  # CORRECCIÓN 3: Sin parámetros ya que no los necesita
        if not self._tools_registry:
            return "No hay reportes disponibles."

        report_list = "Puedo ayudarte con los siguientes reportes:\n"
        for tool_name, tool in self._tools_registry.items():
            if tool_name == self.name:  # No se lista a sí misma
                continue
            report_list += f"- {tool.name}: {tool.description}\n"
        
        return report_list
        
class ObtenerRolesUsuarioInput(BaseModel):
    """Input para la herramienta obtener_roles_usuario."""
    dni_usuario: str = Field(..., description="DNI del usuario a consultar.")

class ObtenerRolesUsuarioTool(BaseTool):
    name: str = "obtener_roles_usuario"
    description: str = "Obtiene los roles asociados a un usuario a través de su DNI."
    args_schema: Type[BaseModel] = ObtenerRolesUsuarioInput

    def _run(self, dni_usuario: str) -> str:
        # Limpiamos el DNI para más seguridad
        dni_limpio = str(dni_usuario).strip()
        print(f"DEBUG: [Tool] Consultando roles para el DNI: '{dni_limpio}'")

        # La consulta probada, usando parámetros para todo
        query = r"""
            SELECT 
                r.name AS rol
            FROM users u
            JOIN model_has_roles mhr 
                ON mhr.model_id = u.id 
               AND mhr.model_type = %(m_type)s
            JOIN roles r 
                ON r.id = mhr.role_id
            WHERE u.dni = %(dni)s;
        """
        
        # Parámetros que se pasarán de forma segura a la consulta
        params = {
            'dni': dni_limpio,
            'm_type': os.getenv("MODEL_TYPE")
        }

        try:
            conn = get_db_connection()
            if not conn:
                return "Error: No se pudo establecer la conexión con la base de datos."

            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            result = cursor.fetchall()
            conn.close()
            
            if not result:
                return f"No se encontraron roles para el DNI: {dni_limpio}"
                
            roles = [row['rol'] for row in result]
            return f"El usuario con DNI {dni_limpio} tiene los siguientes roles: {', '.join(roles)}"
        except Exception as e:
            return f"Error al ejecutar la consulta en la herramienta: {e}"


class ListarUsuariosPorRolInput(BaseModel):
    """Input para la herramienta ListarUsuariosPorRolTool."""
    nombre_rol: str = Field(..., description="el nombre exacto del rol a consultar")

class ListarUsuariosPorRolTool(BaseTool):
    name: str = "listar_usuarios_por_rol"
    description: str = "Lista a todos los usuarios que tienen un rol específico. Necesita el nombre exacto del rol a consultar."
    args_schema: Type[BaseModel] = ListarUsuariosPorRolInput

    def _run(self, nombre_rol: str) -> str:
        # **CAMBIO CLAVE:** Se añade un marcador de posición para model_type
        query = r"""
            SELECT 
                u.name, 
                u.dni
            FROM users u
            JOIN model_has_roles mhr 
                ON u.id = mhr.model_id
               AND mhr.model_type = %(m_type)s
            JOIN roles r
                ON r.id = mhr.role_id
            WHERE r.name = %(nombre_rol)s;
        """
        try:
            conn = get_db_connection()
            if not conn:
                return "Error: No se pudo conectar a la base de datos."

            cursor = conn.cursor(dictionary=True)

            # **CAMBIO CLAVE:** Se añaden ambos valores al diccionario de parámetros
            params = {
                'nombre_rol': nombre_rol,
                'm_type': os.getenv("MODEL_TYPE")
            }

            cursor.execute(query, params)
            result = cursor.fetchall()
            conn.close()
            
            if not result:
                return f"No se encontraron usuarios con el rol '{nombre_rol}' en la base de datos."
            
            usuarios_info = []
            for row in result:
                usuarios_info.append(f"- Nombre: {row['name']}, DNI: {row['dni']}")
                
            return f"Usuarios encontrados con el rol '{nombre_rol}':\n" + "\n".join(usuarios_info)
        except Exception as e:
            return f"Error al ejecutar la consulta: {e}"
            
class ConsultarAtencionesAgenteInput(BaseModel):
    """Input para la herramienta ConsultarAtencionesAgenteTool."""
    dni_agente: str = Field(..., description="El número de DNI del agente a consultar")
    fecha_inicio: str = Field(..., description="La fecha y hora de inicio del periodo a consultar, en formato 'YYYY-MM-DD HH:MM:SS'")
    fecha_fin: str = Field(..., description="La fecha y hora de fin del periodo a consultar, en formato 'YYYY-MM-DD HH:MM:SS'")

def _consultar_atenciones_agente(dni_agente: str, fecha_inicio: str, fecha_fin: str, nombre_tramite: str = None) -> str:
    base_query = """
        SELECT
          p.name AS nombre_tramite,
          rs.description AS estado,
          COUNT(*) AS total_cambios
        FROM
          request_state_records rsr
        JOIN
          users u ON rsr.user_id = u.id
        JOIN
          request_states rs ON rsr.request_status_id = rs.id
        JOIN
          requests r ON rsr.request_id = r.id
        JOIN
          procedures p ON r.procedure_id = p.id
        WHERE
          u.dni = %(dni_agente)s
          AND rsr.created_at BETWEEN %(fecha_inicio)s AND %(fecha_fin)s
          AND rsr.request_status_id NOT IN (0, 1, 2)
    """
    params = {
        'dni_agente': dni_agente,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin
    }

    if nombre_tramite:
        base_query += " AND p.name = %(nombre_tramite)s"
        params['nombre_tramite'] = nombre_tramite

    base_query += """
        GROUP BY
          p.name,
          rs.description
        ORDER BY
          p.name,
          COUNT(*) DESC;
    """

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(base_query, params)
        result = cursor.fetchall()
        conn.close()

        if not result:
            if nombre_tramite:
                return f"No se encontraron cambios de estado para el agente con DNI {dni_agente} para el trámite '{nombre_tramite}' entre {fecha_inicio} y {fecha_fin}."
            else:
                return f"No se encontraron cambios de estado para el agente con DNI {dni_agente} entre {fecha_inicio} y {fecha_fin}."

        if nombre_tramite:
            output = f"Resumen de atenciones para el agente con DNI {dni_agente} en el trámite '{nombre_tramite}':\n"
            for row in result:
                estado = row['estado']
                cantidad = row['total_cambios']
                output += f"- {estado}: {cantidad} cambios de estado.\n"
        else:
            output = f"Resumen de atenciones para el agente con DNI {dni_agente} entre {fecha_inicio} y {fecha_fin}:\n"
            tramites_agrupados = {}
            for row in result:
                tramite = row['nombre_tramite']
                estado = row['estado']
                cantidad = row['total_cambios']

                if tramite not in tramites_agrupados:
                    tramites_agrupados[tramite] = []
                tramites_agrupados[tramite].append(f"{estado}: {cantidad}")

            for tramite, estados in tramites_agrupados.items():
                output += f"- {tramite}: {', '.join(estados)}\n"

        return output
    except Exception as e:
        return f"Error al ejecutar la consulta: {e}"

class ConsultarAtencionesAgenteTool(BaseTool):
    name: str = "consultar_atenciones_agente"
    description: str = "Consulta la cantidad de atenciones (cambios de estado) realizadas por un agente, por tipo de trámite y estado, en un periodo de tiempo específico. Utiliza el DNI del agente y un rango de fechas para el filtro."
    args_schema: Type[BaseModel] = ConsultarAtencionesAgenteInput

    def _run(self, dni_agente: str, fecha_inicio: str, fecha_fin: str) -> str:
        return _consultar_atenciones_agente(dni_agente, fecha_inicio, fecha_fin)

class ConsultarAtencionesAgentePorTramiteInput(BaseModel):
    """Input para la herramienta ConsultarAtencionesAgentePorTramiteTool."""
    dni_agente: str = Field(..., description="El número de DNI del agente a consultar")
    nombre_tramite: str = Field(..., description="El nombre exacto del trámite a consultar")
    fecha_inicio: str = Field(..., description="La fecha y hora de inicio del periodo a consultar, en formato 'YYYY-MM-DD HH:MM:SS'")
    fecha_fin: str = Field(..., description="La fecha y hora de fin del periodo a consultar, en formato 'YYYY-MM-DD HH:MM:SS'")

class ConsultarAtencionesAgentePorTramiteTool(BaseTool):
    name: str = "consultar_atenciones_agente_por_tramite"
    description: str = "Consulta la cantidad de atenciones (cambios de estado) realizadas por un agente, para un tipo de trámite específico y en un periodo de tiempo. Utiliza el DNI del agente, el nombre exacto del trámite y un rango de fechas para el filtro."
    args_schema: Type[BaseModel] = ConsultarAtencionesAgentePorTramiteInput

    def _run(self, dni_agente: str, nombre_tramite: str, fecha_inicio: str, fecha_fin: str) -> str:
        return _consultar_atenciones_agente(dni_agente, fecha_inicio, fecha_fin, nombre_tramite)