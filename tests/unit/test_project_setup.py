"""Smoke tests for project setup."""

from documentops.api.main import app
from documentops.config.settings import Settings, settings
from documentops.infrastructure.db.base import Base
from documentops.worker.main import run_worker


def test_settings_loads_defaults() -> None:
    """Settings should load with sensible defaults."""
    assert settings.api_port == 8000
    assert settings.worker_concurrency == 1
    assert settings.max_file_size_bytes == 52_428_800
    assert settings.max_extracted_text_length == 10_485_760
    assert ".pdf" in settings.supported_extensions_list


def test_custom_settings_override() -> None:
    """Custom settings should override defaults."""
    custom = Settings(api_port=9000, worker_concurrency=1)
    assert custom.api_port == 9000


def test_base_metadata_exists() -> None:
    """SQLAlchemy Base should be defined."""
    assert Base is not None


def test_fastapi_app_exists() -> None:
    """FastAPI app should be importable."""
    assert app.title == "DocumentOps"
    assert app.version == "0.1.0"


def test_worker_entrypoint_imports() -> None:
    """Worker entrypoint should be importable."""
    assert callable(run_worker)
