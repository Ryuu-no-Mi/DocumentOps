"""Integration tests for the full processing pipeline against real PostgreSQL."""

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from documentops.domain.models import DocumentStatus, DocumentType
from documentops.infrastructure.db.models import Document, ExtractedData
from documentops.processing.pipeline import DocumentProcessor

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://documentops:documentops@localhost:5432/documentops"
)


@pytest.fixture(scope="module")
def db_session():
    engine = create_engine(DATABASE_URL, echo=False)
    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = TestSession()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def clean_db(db_session):
    db_session.execute(text("DELETE FROM state_transitions"))
    db_session.execute(text("DELETE FROM processing_attempts"))
    db_session.execute(text("DELETE FROM extracted_data"))
    db_session.execute(text("DELETE FROM documents"))
    db_session.commit()
    yield


def _create_test_pdf(tmpdir: Path, content: str = "ENDESA Factura nº 2026/92837 Total 84.32 EUR") -> Path:
    """Create a simple text file that PyMuPDF can read as PDF."""
    import pymupdf

    pdf_path = tmpdir / "test_invoice.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), content)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def _create_document(db: Session, raw_path: str, file_hash: str = "a" * 64) -> Document:
    """Create a test Document in DETECTED state."""
    doc = Document(
        source_type="local_folder",
        source_id="test",
        original_filename="test.pdf",
        internal_filename="test_internal.pdf",
        file_hash=file_hash,
        file_size=100,
        mime_type="application/pdf",
        status=DocumentStatus.DETECTED.value,
        raw_path=raw_path,
    )
    db.add(doc)
    db.commit()
    return doc


class TestProcessingPipeline:
    def test_process_invoice_full_pipeline(self, db_session, tmp_path) -> None:
        """Test full pipeline with a valid invoice PDF."""
        pdf_path = _create_test_pdf(
            tmp_path,
            "ENDESA ENERGÍA\nFactura nº 2026/92837\nFecha: 01/09/2026\nTotal: 84,32 EUR\nIVA 21%"
        )
        doc = _create_document(db_session, str(pdf_path))

        processor = DocumentProcessor(db_session)
        result = processor.process(doc)

        assert result.status in [
            DocumentStatus.COMPLETED.value,
            DocumentStatus.NEEDS_REVIEW.value,
        ]

        extracted = result.extracted_data
        assert extracted is not None
        assert extracted.document_type == DocumentType.INVOICE.value
        assert extracted.extracted_text is not None
        assert len(extracted.extracted_text) > 0

        assert len(result.processing_attempts) > 0
        assert len(result.state_transitions) > 0

        last_state = result.state_transitions[-1].to_state
        assert last_state in ["COMPLETED", "NEEDS_REVIEW"]

    def test_process_unknown_document(self, db_session, tmp_path) -> None:
        """Test pipeline with a document that cannot be classified as invoice."""
        pdf_path = _create_test_pdf(
            tmp_path,
            "This is a random letter about weather and sports. No invoice content here."
        )
        doc = _create_document(db_session, str(pdf_path))

        processor = DocumentProcessor(db_session)
        result = processor.process(doc)

        assert result.extracted_data is not None
        assert result.extracted_data.document_type == DocumentType.UNKNOWN.value
        assert result.status == DocumentStatus.NEEDS_REVIEW.value

        states = [t.to_state for t in result.state_transitions]
        assert DocumentStatus.CLASSIFIED.value in states
        assert DocumentStatus.ORGANIZED.value in states
        assert DocumentStatus.NEEDS_REVIEW.value in states
        assert DocumentStatus.DATA_EXTRACTED.value not in states
        assert DocumentStatus.VALIDATED.value not in states

    def test_process_creates_state_transitions(self, db_session, tmp_path) -> None:
        """Test that processing creates proper state transitions."""
        pdf_path = _create_test_pdf(tmp_path, "Factura Endesa 12345")
        doc = _create_document(db_session, str(pdf_path))

        processor = DocumentProcessor(db_session)
        result = processor.process(doc)

        states = [t.to_state for t in result.state_transitions]
        assert DocumentStatus.PROCESSING.value in states
        assert DocumentStatus.TEXT_EXTRACTED.value in states
        assert DocumentStatus.CLASSIFIED.value in states

    def test_process_creates_processing_attempts(self, db_session, tmp_path) -> None:
        """Test that processing creates processing attempts for each step."""
        pdf_path = _create_test_pdf(
            tmp_path,
            "ENDESA ENERGÍA\nFactura nº 2026/92837\nFecha: 01/09/2026\nTotal: 84,32 EUR\nIVA 21%"
        )
        doc = _create_document(db_session, str(pdf_path))

        processor = DocumentProcessor(db_session)
        result = processor.process(doc)

        steps = {a.step for a in result.processing_attempts}
        assert "extract" in steps
        assert "classify" in steps
        assert "structure" in steps
        assert "validate" in steps
        assert "organize" in steps

    def test_process_handles_corrupt_pdf(self, db_session, tmp_path) -> None:
        """Test that corrupt PDF results in FAILED state."""
        corrupt_path = tmp_path / "corrupt.pdf"
        corrupt_path.write_bytes(b"this is not a PDF")
        doc = _create_document(db_session, str(corrupt_path))

        processor = DocumentProcessor(db_session)
        result = processor.process(doc)

        assert result.status == DocumentStatus.FAILED.value
        failed_attempts = [a for a in result.processing_attempts if a.status == "failed"]
        assert len(failed_attempts) > 0

    def test_process_handles_nonexistent_file(self, db_session) -> None:
        """Test that missing file results in FAILED state."""
        doc = _create_document(db_session, "/nonexistent/path/file.pdf")

        processor = DocumentProcessor(db_session)
        result = processor.process(doc)

        assert result.status == DocumentStatus.FAILED.value
