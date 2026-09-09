"""FastAPI application entrypoint."""

import logging

from fastapi import FastAPI

from documentops.api.routers.documents import router as documents_router
from documentops.config.settings import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(
    title="DocumentOps",
    description="Sistema de automatización documental",
    version="0.1.0",
)

app.include_router(documents_router)


@app.get("/health", tags=["health"])
def health_check() -> dict:
    """Return API health status."""
    return {"status": "ok", "service": "documentops-api"}


@app.get("/", tags=["root"])
def root() -> dict:
    """Root endpoint."""
    return {"message": "DocumentOps API", "version": "0.1.0"}
