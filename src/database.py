import os
import mysql.connector
from dotenv import load_dotenv

# Cargar variables de entorno una sola vez al importar este módulo
load_dotenv()

def get_db_connection():
    """Crea y devuelve una conexión a la base de datos MySQL."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_DATABASE")
    )
