"""Document processing pipeline orchestrator."""

import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from documentops.domain.models import (
    AttemptStatus,
    DocumentStatus,
    DocumentType,
    ErrorType,
)
from documentops.infrastructure.db.models import (
    Document,
    ExtractedData,
    ProcessingAttempt,
    StateTransition,
)
from documentops.infrastructure.repositories.document_repository import DocumentRepository
from documentops.processing.classification import DocumentClassifier
from documentops.processing.data_extraction import DataExtractor
from documentops.processing.extraction import TextExtractor
from documentops.processing.organizer import FileOrganizer
from documentops.processing.validation import DataValidator

logger = logging.getLogger(__name__)


class ProcessingError(Exception):
    """Raised when a processing step fails."""

    def __init__(self, message: str, error_type: ErrorType, step: str) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.step = step


class DocumentProcessor:
    """Orchestrates the document processing pipeline."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = DocumentRepository(db)
        self.text_extractor = TextExtractor()
        self.classifier = DocumentClassifier()
        self.data_extractor = DataExtractor()
        self.validator = DataValidator()
        self.organizer = FileOrganizer()

    def process(self, document: Document) -> Document:
        """Process a document through the full pipeline.

        Steps: extract → classify → structure → validate → organize
        """
        attempt_number = len(document.processing_attempts) + 1

        try:
            self._transition(document, DocumentStatus.PROCESSING, "Pipeline started")

            self._record_attempt_start(document, attempt_number, "extract")
            extracted_text = self.text_extractor.extract(document.raw_path)
            self._record_attempt_success(document, attempt_number, "extract")

            extracted_data = ExtractedData(
                document_id=document.id,
                document_type=DocumentType.UNKNOWN.value,
                extracted_text=extracted_text,
            )
            self.db.add(extracted_data)
            self._transition(document, DocumentStatus.TEXT_EXTRACTED, "Text extracted")

            self._record_attempt_start(document, attempt_number, "classify")
            doc_type, confidence = self.classifier.classify(extracted_text)
            extracted_data.document_type = doc_type.value
            extracted_data.confidence = confidence
            self._record_attempt_success(document, attempt_number, "classify")
            self._transition(document, DocumentStatus.CLASSIFIED, f"Classified as {doc_type.value}")

            self._record_attempt_start(document, attempt_number, "structure")
            invoice_data = self.data_extractor.extract(doc_type, extracted_text)
            if invoice_data:
                extracted_data.extracted_fields = invoice_data.model_dump()
            self._record_attempt_success(document, attempt_number, "structure")
            self._transition(document, DocumentStatus.DATA_EXTRACTED, "Data extracted")

            self._record_attempt_start(document, attempt_number, "validate")
            if doc_type == DocumentType.INVOICE and invoice_data:
                validation_result = self.validator.validate_invoice(invoice_data)
                extracted_data.validation_errors = validation_result.errors
                self._record_attempt_success(document, attempt_number, "validate")

                if not validation_result.is_valid:
                    self._transition(document, DocumentStatus.ORGANIZED, "Validation failed")
                    hash_short = document.file_hash[:8]
                    new_path = self.organizer.organize_to_review(
                        Path(document.raw_path), doc_type, hash_short
                    )
                    document.processed_path = str(new_path)
                    self._transition(document, DocumentStatus.NEEDS_REVIEW, "Needs review")
                    return document
            else:
                self._record_attempt_success(document, attempt_number, "validate")

            self._transition(document, DocumentStatus.VALIDATED, "Validation passed")

            self._record_attempt_start(document, attempt_number, "organize")
            hash_short = document.file_hash[:8]

            if doc_type == DocumentType.INVOICE:
                new_path = self.organizer.organize_to_processed(
                    Path(document.raw_path),
                    doc_type,
                    invoice_data.date if invoice_data else None,
                    invoice_data.invoice_number if invoice_data else None,
                    hash_short,
                )
            else:
                new_path = self.organizer.organize_to_review(
                    Path(document.raw_path), doc_type, hash_short
                )

            document.processed_path = str(new_path)
            self._record_attempt_success(document, attempt_number, "organize")

            if doc_type == DocumentType.UNKNOWN:
                self._transition(document, DocumentStatus.ORGANIZED, "Organized to review")
                self._transition(document, DocumentStatus.NEEDS_REVIEW, "Needs review")
            else:
                self._transition(document, DocumentStatus.ORGANIZED, "Organized to processed")
                self._transition(document, DocumentStatus.COMPLETED, "Processing complete")

            self.db.refresh(document)
            return document

        except ProcessingError as e:
            logger.error("Processing error: %s (step=%s, type=%s)", e, e.step, e.error_type)
            self._record_attempt_failure(document, attempt_number, e.step, e.error_type, str(e))
            self._transition(document, DocumentStatus.FAILED, str(e))
            self.db.refresh(document)
            return document

        except Exception as e:
            logger.error("Unexpected error processing document: %s", e)
            self._record_attempt_failure(
                document, attempt_number, "unknown", ErrorType.PERMANENT, str(e)
            )
            self._transition(document, DocumentStatus.FAILED, str(e))
            self.db.refresh(document)
            return document

    def _transition(self, document: Document, new_status: DocumentStatus, reason: str) -> None:
        """Record a state transition and update document status."""
        old_status = document.status
        document.status = new_status.value

        transition = StateTransition(
            document_id=document.id,
            from_state=old_status,
            to_state=new_status.value,
            reason=reason,
            created_by="processor",
        )
        self.db.add(transition)
        self.db.flush()

    def _record_attempt_start(self, document: Document, attempt_number: int, step: str) -> None:
        """Record the start of a processing attempt step."""
        attempt = ProcessingAttempt(
            document_id=document.id,
            attempt_number=attempt_number,
            step=step,
            status=AttemptStatus.SUCCESS.value,
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(attempt)
        self.db.flush()

    def _record_attempt_success(self, document: Document, attempt_number: int, step: str) -> None:
        """Mark a processing attempt step as successful."""
        attempt = self._get_latest_attempt(document, attempt_number, step)
        if attempt:
            attempt.finished_at = datetime.now(timezone.utc)
            self.db.flush()

    def _record_attempt_failure(
        self,
        document: Document,
        attempt_number: int,
        step: str,
        error_type: ErrorType,
        error_message: str,
    ) -> None:
        """Record a failed processing attempt step."""
        attempt = ProcessingAttempt(
            document_id=document.id,
            attempt_number=attempt_number,
            step=step,
            status=AttemptStatus.FAILED.value,
            error_type=error_type.value,
            error_message=error_message,
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
        )
        self.db.add(attempt)
        self.db.flush()

    def _get_latest_attempt(
        self, document: Document, attempt_number: int, step: str
    ) -> ProcessingAttempt | None:
        """Get the latest processing attempt for a given step."""
        for attempt in reversed(document.processing_attempts):
            if attempt.attempt_number == attempt_number and attempt.step == step:
                return attempt
        return None
