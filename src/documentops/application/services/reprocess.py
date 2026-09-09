"""Document reprocess service."""

import logging
import uuid

from sqlalchemy.orm import Session

from documentops.domain.models import DocumentStatus
from documentops.infrastructure.db.models import Document, StateTransition
from documentops.infrastructure.db.models import ProcessingAttempt

logger = logging.getLogger(__name__)

REPROCESSABLE_STATES = {
    DocumentStatus.COMPLETED.value,
    DocumentStatus.FAILED.value,
    DocumentStatus.NEEDS_REVIEW.value,
}


class ReprocessService:
    """Handles document reprocessing logic."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def reprocess(self, document_id: uuid.UUID) -> Document:
        """Reprocess a document by resetting its state to DETECTED.

        Raises:
            ValueError: If document not found or not in a reprocessable state.
        """
        document = self.db.get(Document, document_id)
        if not document:
            raise ValueError("Document not found")

        if document.status not in REPROCESSABLE_STATES:
            raise ValueError(
                f"Cannot reprocess document in state {document.status}. "
                f"Must be one of: {', '.join(REPROCESSABLE_STATES)}"
            )

        old_status = document.status
        document.status = DocumentStatus.DETECTED.value
        document.processed_at = None
        document.processing_started_at = None
        document.processing_lease_expires_at = None
        document.processed_by = None

        transition = StateTransition(
            document_id=document.id,
            from_state=old_status,
            to_state=DocumentStatus.DETECTED.value,
            reason="Manual reprocess via API",
            created_by="api",
        )
        self.db.add(transition)
        self.db.commit()

        logger.info("Document %s queued for reprocessing (was %s)", document.id, old_status)
        return document
