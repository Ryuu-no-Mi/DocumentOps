"""Integration tests for WorkerService against real PostgreSQL."""

import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from documentops.domain.models import DocumentStatus
from documentops.infrastructure.db.models import Document
from documentops.infrastructure.repositories.document_repository import DocumentRepository
from documentops.worker.service import WorkerService

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://documentops:documentops@localhost:5432/documentops"
)


@pytest.fixture(scope="module")
def db_engine():
    return create_engine(DATABASE_URL, echo=False)


@pytest.fixture
def db_session(db_engine):
    TestSession = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
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


class TestWorkerService:
    def test_source_poll_and_ingest(self, db_session, db_engine, tmp_path) -> None:
        """Test that source polling detects and ingests new files."""
        import pymupdf

        input_dir = tmp_path / "input"
        input_dir.mkdir()

        pdf_path = input_dir / "invoice.pdf"
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((72, 72), "ENDESA ENERGÍA Factura nº 2026/92837 Total 84,32 EUR IVA")
        doc.save(str(pdf_path))
        doc.close()

        from unittest.mock import patch
        import documentops.worker.service as ws_mod
        import documentops.infrastructure.storage.file_storage as storage_mod
        import documentops.application.services.ingestion as ingestion_mod
        from documentops.sources.local_folder import LocalFolderSource

        with patch.object(ws_mod, "settings") as mock_ws, \
             patch.object(storage_mod, "settings") as mock_storage, \
             patch.object(ingestion_mod, "settings") as mock_ingestion:
            mock_ws.input_dir = str(input_dir)
            mock_ws.supported_extensions_list = [".pdf"]
            mock_ws.max_file_size_bytes = 52_428_800
            mock_ws.poll_interval_seconds = 10
            mock_ws.processing_timeout_seconds = 300
            mock_ws.worker_id = "test-worker"
            mock_ws.raw_dir = str(tmp_path / "raw")
            mock_ws.processed_dir = str(tmp_path / "processed")
            mock_ws.review_dir = str(tmp_path / "review")
            mock_ws.failed_dir = str(tmp_path / "failed")
            mock_storage.raw_dir = str(tmp_path / "raw")
            mock_ingestion.raw_dir = str(tmp_path / "raw")

            source = LocalFolderSource(input_dir=input_dir)
            worker = WorkerService(source=source)
            worker._source_poll_cycle()

        with db_engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM documents")).scalar()
            assert count == 1

            row = conn.execute(text("SELECT status, original_filename FROM documents")).fetchone()
            assert row[0] == "DETECTED"
            assert row[1] == "invoice.pdf"

    def test_processing_poll_processes_document(self, db_session, tmp_path) -> None:
        """Test that processing poll finds and processes DETECTED documents."""
        import pymupdf

        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()

        pdf_path = raw_dir / "test.pdf"
        pdoc = pymupdf.open()
        page = pdoc.new_page()
        page.insert_text((72, 72), "ENDESA ENERGÍA Factura nº 2026/92837 Total 84,32 EUR IVA")
        pdoc.save(str(pdf_path))
        pdoc.close()

        document = Document(
            source_type="local_folder",
            source_id="test",
            original_filename="test.pdf",
            internal_filename="test_internal.pdf",
            file_hash="a" * 64,
            file_size=pdf_path.stat().st_size,
            mime_type="application/pdf",
            status=DocumentStatus.DETECTED.value,
            raw_path=str(pdf_path),
        )
        db_session.add(document)
        db_session.commit()

        from unittest.mock import patch
        import documentops.worker.service as ws_mod
        import documentops.infrastructure.storage.file_storage as storage_mod

        with patch.object(ws_mod, "settings") as mock_ws, \
             patch.object(storage_mod, "settings") as mock_storage:
            mock_ws.input_dir = str(tmp_path / "input")
            mock_ws.supported_extensions_list = [".pdf"]
            mock_ws.max_file_size_bytes = 52_428_800
            mock_ws.poll_interval_seconds = 10
            mock_ws.processing_timeout_seconds = 300
            mock_ws.worker_id = "test-worker"
            mock_ws.raw_dir = str(raw_dir)
            mock_ws.processed_dir = str(tmp_path / "processed")
            mock_ws.review_dir = str(tmp_path / "review")
            mock_ws.failed_dir = str(tmp_path / "failed")
            mock_storage.raw_dir = str(raw_dir)
            mock_storage.processed_dir = str(tmp_path / "processed")
            mock_storage.review_dir = str(tmp_path / "review")
            mock_storage.failed_dir = str(tmp_path / "failed")

            worker = WorkerService()
            worker._processing_poll_cycle()

        db_session.refresh(document)
        assert document.status in [
            DocumentStatus.COMPLETED.value,
            DocumentStatus.NEEDS_REVIEW.value,
        ]

    def test_cleanup_expired_leases(self, db_session) -> None:
        """Test that expired leases are reset to DETECTED."""
        document = Document(
            source_type="local_folder",
            source_id="test",
            original_filename="stuck.pdf",
            internal_filename="stuck_internal.pdf",
            file_hash="b" * 64,
            file_size=100,
            mime_type="application/pdf",
            status=DocumentStatus.PROCESSING.value,
            raw_path="/tmp/stuck.pdf",
            processing_started_at=datetime.now(timezone.utc) - timedelta(hours=1),
            processing_lease_expires_at=datetime.now(timezone.utc) - timedelta(minutes=30),
            processed_by="dead-worker",
        )
        db_session.add(document)
        db_session.commit()

        from unittest.mock import patch
        import documentops.worker.service as ws_mod

        with patch.object(ws_mod, "settings") as mock_ws:
            mock_ws.input_dir = "/nonexistent"
            mock_ws.poll_interval_seconds = 10
            mock_ws.processing_timeout_seconds = 300

            worker = WorkerService()
            worker._cleanup_expired_leases()

        db_session.refresh(document)
        assert document.status == DocumentStatus.DETECTED.value
        assert document.processed_by is None
        assert document.processing_lease_expires_at is None
