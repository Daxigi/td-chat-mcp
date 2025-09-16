# MCP Server

This project is a FastAPI server that exposes existing tools so they can be consumed by any MCP-compatible client, such as a CrewAI agent.

## Installation

To install the dependencies, it is recommended to use a virtual environment. Once activated, run:

```bash
pip install "fastapi" "uvicorn[standard]" "pydantic"
```

## Usage

To start the server, run the following command from the root of the project:

```bash
uvicorn src.main:app --reload
```

The server will be available at `http://127.0.0.1:8000`.
