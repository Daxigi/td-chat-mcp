# 1. Imagen base (Mantenemos Python 3.12 como tenías)
FROM python:3.12-slim-bookworm

# 2. Copiamos el binario de 'uv' directamente (Truco moderno: no hace falta pip install)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 3. Configuración de entorno
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PYTHONPATH=/app

# 4. Copiamos ficheros de dependencias
# IMPORTANTE: Ahora usamos uv.lock, no poetry.lock
COPY pyproject.toml uv.lock ./

# 5. Instalamos dependencias
# --frozen: Usa versiones exactas del lockfile
# --no-cache: No guarda basura para mantener la imagen ligera
RUN uv sync --frozen --no-cache --no-dev

# 6. Copiamos el código fuente
COPY src/ ./src/

# 7. Exponemos el puerto interno (8765 como tenías configurado)
EXPOSE 8765

# 8. Comando de arranque usando 'uv run'
CMD ["uv", "run", "uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8765"]