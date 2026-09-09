"""File organization after processing."""

import logging
import shutil
from datetime import datetime
from pathlib import Path, PurePosixPath

from documentops.config.settings import settings
from documentops.domain.models import DocumentType
from documentops.infrastructure.storage.file_storage import sanitize_filename

logger = logging.getLogger(__name__)


def _normalize_path(path: Path) -> str:
    """Convert a Path to a POSIX-style string with forward slashes."""
    return str(PurePosixPath(path.as_posix()))


class FileOrganizer:
    """Organizes processed files into the correct directory structure."""

    def organize_to_processed(
        self,
        source_path: Path,
        document_type: DocumentType,
        date: str | None,
        invoice_number: str | None,
        hash_short: str,
    ) -> str:
        """Move file to processed directory.

        Returns the normalized file path with forward slashes.
        """
        now = datetime.now()
        year = date[:4] if date and len(date) >= 4 else str(now.year)
        month = date[5:7] if date and len(date) >= 7 else f"{now.month:02d}"

        if document_type == DocumentType.INVOICE and invoice_number:
            safe_number = sanitize_filename(invoice_number)
            safe_date = sanitize_filename(date or f"{now.year}-{now.month:02d}-{now.day:02d}")
            filename = f"invoice_{safe_date}_{safe_number}_{hash_short}.pdf"
            dest_dir = Path(settings.processed_dir) / "invoice" / year / month
        else:
            filename = f"unknown_{now.strftime('%Y%m%d_%H%M%S')}_{hash_short}.pdf"
            dest_dir = Path(settings.review_dir) / "unknown" / year / month

        dest_dir.mkdir(parents=True, exist_ok=True)
        destination = dest_dir / filename

        shutil.move(str(source_path), str(destination))
        normalized = _normalize_path(destination)
        logger.info("File organized to: %s", normalized)

        return normalized

    def organize_to_failed(
        self,
        source_path: Path,
        hash_short: str,
    ) -> str:
        """Move file to failed directory.

        Returns the normalized file path with forward slashes.
        """
        now = datetime.now()
        year = str(now.year)
        month = f"{now.month:02d}"

        safe_name = sanitize_filename(source_path.stem)
        filename = f"{safe_name}_{hash_short}.pdf"
        dest_dir = Path(settings.failed_dir) / year / month

        dest_dir.mkdir(parents=True, exist_ok=True)
        destination = dest_dir / filename

        shutil.move(str(source_path), str(destination))
        normalized = _normalize_path(destination)
        logger.info("File moved to failed: %s", normalized)

        return normalized

    def organize_to_review(
        self,
        source_path: Path,
        document_type: DocumentType,
        hash_short: str,
    ) -> str:
        """Move file to review directory.

        Returns the normalized file path with forward slashes.
        """
        now = datetime.now()
        year = str(now.year)
        month = f"{now.month:02d}"

        if document_type == DocumentType.INVOICE:
            subdir = "invoice"
        else:
            subdir = "unknown"

        safe_name = sanitize_filename(source_path.stem)
        filename = f"{safe_name}_{hash_short}.pdf"
        dest_dir = Path(settings.review_dir) / subdir / year / month

        dest_dir.mkdir(parents=True, exist_ok=True)
        destination = dest_dir / filename

        shutil.move(str(source_path), str(destination))
        normalized = _normalize_path(destination)
        logger.info("File organized to review: %s", normalized)

        return normalized
