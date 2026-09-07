"""Document ingestion service."""

import logging

from sqlalchemy.orm import Session

from documentops.config.settings import settings
from documentops.domain.models import DocumentIngestionRequest, DocumentStatus
from documentops.infrastructure.db.models import Document, StateTransition
from documentops.infrastructure.repositories.document_repository import DocumentRepository
from documentops.infrastructure.storage.file_storage import (
    compute_file_hash,
    copy_to_raw,
    generate_internal_filename,
)

logger = logging.getLogger(__name__)

MIME_TYPE_WHITELIST = {
    ".pdf": ["application/pdf"],
}


class IngestionService:
    """Handles document ingestion: validate, hash, deduplicate, store, register."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = DocumentRepository(db)

    def ingest(self, request: DocumentIngestionRequest) -> Document | None:
        """Ingest a document from a source request.

        Returns the created Document, or None if the document was skipped (duplicate).
        Raises ValueError for validation failures.
        """
        self._validate_mime_type(request)

        file_hash = compute_file_hash(request.file_path)

        if self.repo.exists_by_hash(file_hash):
            logger.info("Duplicate document skipped: hash=%s file=%s", file_hash, request.original_filename)
            return None

        internal_filename = generate_internal_filename(request.original_filename)
        copy_to_raw(request.file_path, internal_filename)

        document = self.repo.create(
            source_type=request.source_type,
            source_id=request.source_id,
            original_filename=request.original_filename,
            internal_filename=internal_filename,
            file_hash=file_hash,
            file_size=request.file_size,
            mime_type=request.mime_type,
            raw_path=f"{settings.raw_dir}/{internal_filename}",
            metadata=request.metadata,
        )

        transition = StateTransition(
            document_id=document.id,
            from_state="",
            to_state=DocumentStatus.DETECTED.value,
            reason="Document ingested",
            created_by="ingestion",
        )
        self.db.add(transition)
        self.db.commit()

        logger.info("Document ingested: id=%s hash=%s file=%s", document.id, file_hash, request.original_filename)

        return document

    def _validate_mime_type(self, request: DocumentIngestionRequest) -> None:
        """Validate that MIME type matches file extension."""
        from pathlib import Path

        suffix = Path(request.original_filename).suffix.lower()
        allowed_mimes = MIME_TYPE_WHITELIST.get(suffix, [])

        if not allowed_mimes:
            raise ValueError(f"Unsupported file extension: {suffix}")

        if request.mime_type not in allowed_mimes:
            raise ValueError(
                f"MIME type mismatch: extension={suffix} mime={request.mime_type} "
                f"expected one of {allowed_mimes}"
            )
