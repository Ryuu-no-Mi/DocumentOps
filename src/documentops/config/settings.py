"""Application settings loaded from environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="postgresql://documentops:documentops@localhost:5432/documentops",
        description="PostgreSQL connection URL",
    )

    # API
    api_host: str = Field(default="0.0.0.0", description="API bind host")
    api_port: int = Field(default=8000, description="API bind port")

    # Worker
    worker_id: str = Field(default="worker-1", description="Unique worker identifier")
    worker_concurrency: int = Field(
        default=1,
        ge=1,
        description="Number of documents processed concurrently (V1: always 1)",
    )
    poll_interval_seconds: int = Field(
        default=10,
        ge=1,
        description="Seconds between source and processing polling cycles",
    )
    processing_timeout_seconds: int = Field(
        default=300,
        ge=30,
        description="Lease timeout in seconds for document processing",
    )

    # Processing limits
    max_file_size_bytes: int = Field(
        default=52_428_800,
        ge=1,
        description="Maximum file size allowed for processing (50 MB)",
    )
    max_extracted_text_length: int = Field(
        default=10_485_760,
        ge=1,
        description="Maximum extracted text length stored in PostgreSQL (10 MB)",
    )
    max_auto_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum automatic retries for transient errors",
    )

    # Storage paths
    input_dir: str = Field(
        default="./data/input",
        description="Directory watched by LocalFolderSource",
    )
    raw_dir: str = Field(default="./data/raw", description="Directory for original copies")
    processed_dir: str = Field(
        default="./data/processed",
        description="Directory for successfully processed documents",
    )
    failed_dir: str = Field(
        default="./data/failed",
        description="Directory for documents with technical errors",
    )
    review_dir: str = Field(
        default="./data/review",
        description="Directory for documents needing human review",
    )

    # Supported file types
    supported_extensions: str = Field(
        default=".pdf",
        description="Comma-separated list of supported file extensions",
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    @property
    def supported_extensions_list(self) -> list[str]:
        """Return supported extensions as a list of lowercase strings."""
        return [ext.strip().lower() for ext in self.supported_extensions.split(",")]


# Global settings instance
settings = Settings()
