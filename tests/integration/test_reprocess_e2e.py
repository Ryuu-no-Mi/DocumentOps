"""End-to-end reprocess test using the API and worker service."""

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pymupdf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from documentops.api.main import app
from documentops.application.services.ingestion import IngestionService
from documentops.domain.models import DocumentIngestionRequest, DocumentStatus
from documentops.infrastructure.db.models import Document
from documentops.infrastructure.db.session import get_db
from documentops.infrastructure.storage.file_storage import compute_file_hash
from documentops.worker.service import WorkerService


DATABASE_URL = "postgresql://documentops:documentops@localhost:5432/documentops"
engine = create_engine(DATABASE_URL, echo=False)
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM state_transitions"))
        conn.execute(text("DELETE FROM processing_attempts"))
        conn.execute(text("DELETE FROM extracted_data"))
        conn.execute(text("DELETE FROM documents"))
        conn.commit()
    yield


def _create_invoice(path) -> None:
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text(
        (72, 72),
        "ENDESA ENERGIA\nFactura 2026/92837\nFecha: 01/09/2026\nTotal: 84,32 EUR\nIVA 21%",
    )
    pdf.save(str(path))
    pdf.close()


def test_reprocess_completed_document_through_worker(tmp_path) -> None:
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    review_dir = tmp_path / "review"
    failed_dir = tmp_path / "failed"
    raw_dir.mkdir()

    raw_file = raw_dir / "invoice.pdf"
    _create_invoice(raw_file)
    file_hash = compute_file_hash(raw_file)

    with TestSession() as db:
        document = Document(
            source_type="local_folder",
            source_id="test",
            original_filename="invoice.pdf",
            internal_filename="invoice.pdf",
            file_hash=file_hash,
            file_size=raw_file.stat().st_size,
            mime_type="application/pdf",
            status=DocumentStatus.DETECTED.value,
            raw_path=str(raw_file),
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        document_id = document.id

    worker_settings = SimpleNamespace(
        worker_id="test-worker",
        processing_timeout_seconds=300,
    )
    organizer_settings = SimpleNamespace(
        processed_dir=str(processed_dir),
        review_dir=str(review_dir),
        failed_dir=str(failed_dir),
    )

    with patch("documentops.worker.service.SessionLocal", TestSession), \
         patch("documentops.worker.service.settings", worker_settings), \
         patch("documentops.processing.organizer.settings", organizer_settings):
        worker = WorkerService()

        # Initial processing.
        worker._processing_poll_cycle()

        with TestSession() as db:
            document = db.get(Document, document_id)
            assert document is not None
            assert document.status == DocumentStatus.COMPLETED.value
            first_processed_path = document.processed_path
            first_attempt_count = len(document.processing_attempts)
            assert first_processed_path is not None
            assert not raw_file.exists()

        # API reprocess must restore the organized file to raw/.
        response = client.post(f"/documents/{document_id}/reprocess")
        assert response.status_code == 200

        with TestSession() as db:
            document = db.get(Document, document_id)
            assert document is not None
            assert document.status == DocumentStatus.DETECTED.value
            assert document.processed_path is None
            assert raw_file.exists()

        # The worker must process the same Document again.
        worker._processing_poll_cycle()

    with TestSession() as db:
        document = db.get(Document, document_id)
        assert document is not None
        assert document.status == DocumentStatus.COMPLETED.value
        assert document.processed_at is not None
        assert document.processed_path is not None
        assert document.processing_lease_expires_at is None
        assert document.processed_by is None
        assert len(document.processing_attempts) > first_attempt_count
        assert not raw_file.exists()
        document_count = db.execute(text("SELECT COUNT(*) FROM documents")).scalar()
        assert document_count == 1
        assert document.file_hash == file_hash
        assert document.processed_path is not None

        duplicate_source = tmp_path / "duplicate.pdf"
        duplicate_source.write_bytes(Path(document.processed_path).read_bytes())
        duplicate_request = DocumentIngestionRequest(
            source_type="local_folder",
            source_id="test",
            original_filename="duplicate.pdf",
            file_path=duplicate_source,
            file_size=duplicate_source.stat().st_size,
            mime_type="application/pdf",
            received_at=datetime.now(timezone.utc),
        )
        assert IngestionService(db).ingest(duplicate_request) is None
        assert db.execute(text("SELECT COUNT(*) FROM documents")).scalar() == 1
