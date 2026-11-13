# ==============================================================================
# CodeRazz Backend — Production Multi-Worker Dockerfile (FastAPI + Gunicorn)
# Hardened Python 3.12 Slim with Docker CLI for Sandboxed Runner Orchestration
# ==============================================================================

FROM python:3.12-slim-bookworm AS base

# Prevent Python from writing .pyc and buffer standard I/O streams
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies & Docker CLI for container orchestrator
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root application user and group
RUN groupadd -g 10001 coderazz && \
    useradd -u 10001 -g coderazz -s /bin/bash -m coderazz && \
    (groupadd -g 999 docker || true) && \
    usermod -aG docker coderazz || true && \
    usermod -aG root coderazz || true

# Copy and install python dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy backend source modules, machine learning taxonomy engine, and execution harness
COPY backend /app/backend
COPY ml /app/ml
COPY execution /app/execution
COPY scripts /app/scripts
COPY backend/alembic.ini /app/alembic.ini

# Ensure non-root ownership
RUN chown -R coderazz:coderazz /app

# Switch to non-root application user
USER coderazz

EXPOSE 8000

# Container health probe
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://127.0.0.1:8000/health || exit 1

# Production WSGI/ASGI entrypoint: Gunicorn pre-fork worker manager with Uvicorn workers
CMD ["gunicorn", "backend.app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-"]
