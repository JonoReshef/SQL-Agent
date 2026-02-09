# Backend Dockerfile for WestBrand Python API
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY backend/pyproject.toml ./pyproject.toml

# Install Python dependencies
RUN pip install uv
RUN uv sync

# Copy source code
COPY backend/agent/ ./agent/
COPY backend/workflow/ ./workflow/
COPY config/ ./config/

# Create output directory
RUN mkdir -p /app/output

# Expose port for FastAPI server
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run the FastAPI server
CMD ["uv", "run", "uvicorn", "agent.server.server:app", "--host", "0.0.0.0", "--port", "8000"]
