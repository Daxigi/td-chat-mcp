
# 1. Base Image
FROM python:3.9-slim

# 2. Set up Environment
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. Install Poetry
RUN pip install poetry

# 4. Copy Project Files and Install Dependencies
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root

# 5. Copy Source Code
COPY src/ ./src/

# 6. Expose Port
EXPOSE 8000

# 7. Run Command
CMD ["poetry", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
