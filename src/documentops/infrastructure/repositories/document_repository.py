"""Document repository for database operations."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from documentops.domain.models import DocumentStatus
from documentops.infrastructure.db.models import Document


class DocumentRepository:
    """Handles database operations for Document entities."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        source_type: str,
        source_id: str,
        original_filename: str,
        internal_filename: str,
        file_hash: str,
        file_size: int,
        mime_type: str,
        raw_path: str,
        metadata: dict | None = None,
    ) -> Document:
        """Create a new document record."""
        document = Document(
            source_type=source_type,
            source_id=source_id,
            original_filename=original_filename,
            internal_filename=internal_filename,
            file_hash=file_hash,
            file_size=file_size,
            mime_type=mime_type,
            status=DocumentStatus.DETECTED.value,
            raw_path=raw_path,
            metadata_=metadata,
        )
        self.db.add(document)
        self.db.flush()
        return document

    def get_by_id(self, document_id: uuid.UUID) -> Document | None:
        """Get a document by its ID."""
        return self.db.get(Document, document_id)

    def get_by_hash(self, file_hash: str) -> Document | None:
        """Get a document by its SHA-256 hash."""
        stmt = select(Document).where(Document.file_hash == file_hash)
        return self.db.scalar(stmt)

    def exists_by_hash(self, file_hash: str) -> bool:
        """Check if a document with the given hash already exists."""
        stmt = select(Document.id).where(Document.file_hash == file_hash)
        return self.db.scalar(stmt) is not None

    def update_status(
        self,
        document: Document,
        new_status: DocumentStatus,
        reason: str | None = None,
        created_by: str = "system",
    ) -> None:
        """Update document status and flush."""
        document.status = new_status.value
        self.db.flush()

    def set_processing_lease(
        self,
        document: Document,
        worker_id: str,
        lease_expires_at: datetime,
    ) -> None:
        """Set processing lease on a document."""
        document.status = DocumentStatus.PROCESSING.value
        document.processing_started_at = datetime.now(timezone.utc)
        document.processing_lease_expires_at = lease_expires_at
        document.processed_by = worker_id
        self.db.flush()

    def renew_lease(
        self,
        document: Document,
        lease_expires_at: datetime,
    ) -> None:
        """Renew processing lease on a document."""
        document.processing_lease_expires_at = lease_expires_at
        self.db.flush()

    def get_pending_documents(self, limit: int = 1) -> list[Document]:
        """Get documents eligible for processing (pending or expired lease)."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(Document)
            .where(
                Document.status.in_([
                    DocumentStatus.DETECTED.value,
                    DocumentStatus.PROCESSING.value,
                ]),
                (
                    (Document.processing_lease_expires_at.is_(None))
                    | (Document.processing_lease_expires_at < now)
                ),
            )
            .order_by(Document.received_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(self.db.scalars(stmt).all())
