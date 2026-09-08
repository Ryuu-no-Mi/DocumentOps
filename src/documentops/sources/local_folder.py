"""Local folder document source."""

import mimetypes
from datetime import datetime, timezone
from pathlib import Path

from documentops.config.settings import settings
from documentops.domain.models import DocumentIngestionRequest
from documentops.sources.base import DocumentSource


class LocalFolderSource(DocumentSource):
    """Detects new files in a configured local directory.

    Only scans for supported file extensions and validates basic file properties.
    Does NOT process files or access the database.
    """

    def __init__(
        self,
        input_dir: str | Path | None = None,
        supported_extensions: list[str] | None = None,
        max_file_size: int | None = None,
    ) -> None:
        self.input_dir = Path(input_dir or settings.input_dir)
        self.supported_extensions = supported_extensions or settings.supported_extensions_list
        self.max_file_size = max_file_size or settings.max_file_size_bytes

    async def poll(self) -> list[DocumentIngestionRequest]:
        """Scan input directory for new files and return ingestion requests."""
        requests: list[DocumentIngestionRequest] = []

        if not self.input_dir.exists():
            return requests

        for entry in self.input_dir.iterdir():
            if not entry.is_file():
                continue
            if entry.name.startswith(".") or entry.name.startswith("~"):
                continue
            if not self._is_supported_extension(entry):
                continue

            file_size = entry.stat().st_size
            if file_size > self.max_file_size:
                continue
            if file_size == 0:
                continue

            mime_type = self._detect_mime_type(entry)

            requests.append(
                DocumentIngestionRequest(
                    source_type="local_folder",
                    source_id=str(self.input_dir),
                    original_filename=entry.name,
                    file_path=entry.resolve(),
                    file_size=file_size,
                    mime_type=mime_type,
                    received_at=datetime.now(timezone.utc),
                    metadata={},
                )
            )

        return requests

    def _is_supported_extension(self, path: Path) -> bool:
        """Check if file extension is in the supported list."""
        return path.suffix.lower() in self.supported_extensions

    def _detect_mime_type(self, path: Path) -> str:
        """Detect MIME type from file extension."""
        mime, _ = mimetypes.guess_type(str(path))
        return mime or "application/octet-stream"
