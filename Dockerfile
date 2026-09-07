# Multi-stage Dockerfile for DocumentOps API and Worker services.
#
# Build API image:
#   docker build --target api -t documentops-api .
#
# Build Worker image:
#   docker build --target worker -t documentops-worker .

# -----------------------------------------------------------------------------
# Base stage: shared dependencies and application code
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock ./
RUN poetry install --without dev --no-root && rm -rf $POETRY_CACHE_DIR

COPY . .
RUN poetry install --without dev


# -----------------------------------------------------------------------------
# API stage: exposes FastAPI application
# -----------------------------------------------------------------------------
FROM base AS api

EXPOSE 8000

CMD ["poetry", "run", "uvicorn", "documentops.api.main:app", "--host", "0.0.0.0", "--port", "8000"]


# -----------------------------------------------------------------------------
# Worker stage: runs document processing worker
# -----------------------------------------------------------------------------
FROM base AS worker

CMD ["poetry", "run", "python", "-m", "documentops.worker.main"]
