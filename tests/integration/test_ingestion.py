"""Tests for ingestion service."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from documentops.domain.models import DocumentIngestionRequest, DocumentStatus
from documentops.infrastructure.db.base import Base
from documentops.infrastructure.db.models import Document
from documentops.application.services.ingestion import IngestionService


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def _make_request(file_path: Path, filename: str | None = None) -> DocumentIngestionRequest:
    return DocumentIngestionRequest(
        source_type="local_folder",
        source_id="/test/input",
        original_filename=filename or file_path.name,
        file_path=file_path,
        file_size=file_path.stat().st_size,
        mime_type="application/pdf",
        received_at=datetime.now(timezone.utc),
    )


class TestIngestionService:
    def test_ingest_creates_document(self, db_session: Session, temp_dir: Path) -> None:
        pdf = temp_dir / "factura.pdf"
        pdf.write_bytes(b"%PDF-1.4 ENDESA factura content")
        raw_dir = str(temp_dir / "raw")

        with patch("documentops.application.services.ingestion.settings") as mock_s, \
             patch("documentops.infrastructure.storage.file_storage.settings") as mock_f:
            mock_s.raw_dir = raw_dir
            mock_f.raw_dir = raw_dir

            service = IngestionService(db_session)
            request = _make_request(pdf)
            doc = service.ingest(request)

            assert doc is not None
            assert doc.status == "DETECTED"
            assert doc.file_hash is not None
            assert len(doc.file_hash) == 64
            assert doc.original_filename == "factura.pdf"
            assert doc.state_transitions[-1].to_state == "DETECTED"

    def test_ingest_duplicate_returns_none(self, db_session: Session, temp_dir: Path) -> None:
        pdf = temp_dir / "factura.pdf"
        pdf.write_bytes(b"%PDF-1.4 same content")
        raw_dir = str(temp_dir / "raw")

        with patch("documentops.application.services.ingestion.settings") as mock_s, \
             patch("documentops.infrastructure.storage.file_storage.settings") as mock_f:
            mock_s.raw_dir = raw_dir
            mock_f.raw_dir = raw_dir

            service = IngestionService(db_session)
            request = _make_request(pdf)

            doc1 = service.ingest(request)
            assert doc1 is not None

            doc2 = service.ingest(request)
            assert doc2 is None

    def test_ingest_rejects_mime_mismatch(self, db_session: Session, temp_dir: Path) -> None:
        pdf = temp_dir / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 content")

        service = IngestionService(db_session)
        request = DocumentIngestionRequest(
            source_type="local_folder",
            source_id="/test",
            original_filename="test.pdf",
            file_path=pdf,
            file_size=pdf.stat().st_size,
            mime_type="image/png",
            received_at=datetime.now(timezone.utc),
        )

        with pytest.raises(ValueError, match="MIME type mismatch"):
            service.ingest(request)

    def test_ingest_rejects_unsupported_extension(self, db_session: Session, temp_dir: Path) -> None:
        txt = temp_dir / "test.txt"
        txt.write_bytes(b"hello")

        service = IngestionService(db_session)
        request = DocumentIngestionRequest(
            source_type="local_folder",
            source_id="/test",
            original_filename="test.txt",
            file_path=txt,
            file_size=txt.stat().st_size,
            mime_type="text/plain",
            received_at=datetime.now(timezone.utc),
        )

        with pytest.raises(ValueError, match="Unsupported file extension"):
            service.ingest(request)

    def test_ingest_state_transition_recorded(self, db_session: Session, temp_dir: Path) -> None:
        pdf = temp_dir / "doc.pdf"
        pdf.write_bytes(b"%PDF-1.4 content")
        raw_dir = str(temp_dir / "raw")

        with patch("documentops.application.services.ingestion.settings") as mock_s, \
             patch("documentops.infrastructure.storage.file_storage.settings") as mock_f:
            mock_s.raw_dir = raw_dir
            mock_f.raw_dir = raw_dir

            service = IngestionService(db_session)
            request = _make_request(pdf)
            doc = service.ingest(request)

            assert len(doc.state_transitions) == 1
            assert doc.state_transitions[0].from_state == ""
            assert doc.state_transitions[0].to_state == "DETECTED"
            assert doc.state_transitions[0].created_by == "ingestion"
