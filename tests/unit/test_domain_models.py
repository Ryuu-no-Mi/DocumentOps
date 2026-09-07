"""Tests for Pydantic domain models."""

import uuid
from datetime import datetime, timezone

from documentops.domain.models import (
    AttemptStatus,
    DocumentCreate,
    DocumentStatus,
    DocumentType,
    ErrorType,
    ExtractedDataCreate,
    InvoiceData,
    ProcessingAttemptCreate,
    SourceContext,
    StateTransitionCreate,
)


class TestDocumentStatus:
    def test_all_statuses_defined(self) -> None:
        expected = {
            "DETECTED", "PROCESSING", "TEXT_EXTRACTED", "CLASSIFIED",
            "DATA_EXTRACTED", "VALIDATED", "ORGANIZED", "COMPLETED",
            "FAILED", "NEEDS_REVIEW",
        }
        actual = {s.value for s in DocumentStatus}
        assert actual == expected


class TestDocumentType:
    def test_invoice_and_unknown(self) -> None:
        assert DocumentType.INVOICE.value == "invoice"
        assert DocumentType.UNKNOWN.value == "unknown"


class TestErrorType:
    def test_error_types(self) -> None:
        expected = {"TRANSIENT", "PERMANENT", "VALIDATION_ERROR", "MIME_TYPE_MISMATCH", "EXTRACTED_TEXT_TOO_LARGE"}
        actual = {e.value for e in ErrorType}
        assert actual == expected


class TestSourceContext:
    def test_valid_source_context(self) -> None:
        ctx = SourceContext(
            source_type="local_folder",
            source_id="downloads",
            original_filename="factura.pdf",
            received_at=datetime.now(timezone.utc),
        )
        assert ctx.source_type == "local_folder"
        assert ctx.metadata == {}

    def test_with_metadata(self) -> None:
        ctx = SourceContext(
            source_type="email",
            source_id="inbox",
            original_filename="invoice.pdf",
            received_at=datetime.now(timezone.utc),
            metadata={"sender": "test@example.com"},
        )
        assert ctx.metadata["sender"] == "test@example.com"


class TestDocumentCreate:
    def test_valid_document_create(self) -> None:
        doc = DocumentCreate(
            source_type="local_folder",
            source_id="downloads",
            original_filename="factura.pdf",
            internal_filename="abc123.pdf",
            file_hash="a" * 64,
            file_size=1024,
            mime_type="application/pdf",
            raw_path="/data/raw/abc123.pdf",
        )
        assert doc.file_hash == "a" * 64
        assert doc.file_size == 1024

    def test_invalid_hash_length(self) -> None:
        import pytest
        with pytest.raises(Exception):
            DocumentCreate(
                source_type="local_folder",
                source_id="downloads",
                original_filename="factura.pdf",
                internal_filename="abc123.pdf",
                file_hash="short",
                file_size=1024,
                mime_type="application/pdf",
                raw_path="/data/raw/abc123.pdf",
            )


class TestInvoiceData:
    def test_full_invoice(self) -> None:
        invoice = InvoiceData(
            issuer="Endesa Energía",
            invoice_number="2026/92837",
            date="2026-09-01",
            total=84.32,
            currency="EUR",
        )
        assert invoice.issuer == "Endesa Energía"
        assert invoice.total == 84.32

    def test_partial_invoice(self) -> None:
        invoice = InvoiceData(issuer="Endesa")
        assert invoice.invoice_number is None
        assert invoice.total is None


class TestExtractedDataCreate:
    def test_valid_extracted_data(self) -> None:
        data = ExtractedDataCreate(
            document_type=DocumentType.INVOICE,
            confidence=0.85,
            extracted_text="Some invoice text",
            extracted_fields={"issuer": "Endesa", "total": 84.32},
        )
        assert data.document_type == DocumentType.INVOICE
        assert data.confidence == 0.85

    def test_unknown_type(self) -> None:
        data = ExtractedDataCreate(
            document_type=DocumentType.UNKNOWN,
            confidence=0.0,
        )
        assert data.document_type == DocumentType.UNKNOWN


class TestProcessingAttemptCreate:
    def test_success_attempt(self) -> None:
        now = datetime.now(timezone.utc)
        attempt = ProcessingAttemptCreate(
            document_id=uuid.uuid4(),
            attempt_number=1,
            step="extraction",
            status=AttemptStatus.SUCCESS,
            started_at=now,
            finished_at=now,
        )
        assert attempt.status == AttemptStatus.SUCCESS
        assert attempt.error_type is None

    def test_failed_attempt(self) -> None:
        now = datetime.now(timezone.utc)
        attempt = ProcessingAttemptCreate(
            document_id=uuid.uuid4(),
            attempt_number=1,
            step="extraction",
            status=AttemptStatus.FAILED,
            error_type=ErrorType.TRANSIENT,
            error_message="File locked",
            started_at=now,
        )
        assert attempt.error_type == ErrorType.TRANSIENT
        assert attempt.finished_at is None


class TestStateTransitionCreate:
    def test_valid_transition(self) -> None:
        transition = StateTransitionCreate(
            document_id=uuid.uuid4(),
            from_state=DocumentStatus.DETECTED,
            to_state=DocumentStatus.PROCESSING,
            created_by="worker",
        )
        assert transition.from_state == DocumentStatus.DETECTED
        assert transition.to_state == DocumentStatus.PROCESSING
