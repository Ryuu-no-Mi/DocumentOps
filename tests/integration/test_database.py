"""Integration tests for SQLAlchemy models and repository."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from documentops.domain.models import DocumentStatus
from documentops.infrastructure.db.base import Base
from documentops.infrastructure.db.models import (
    Document,
    ExtractedData,
    ProcessingAttempt,
    StateTransition,
)
from documentops.infrastructure.repositories.document_repository import DocumentRepository


@pytest.fixture
def db_session() -> Session:
    """Create an in-memory SQLite database session for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


class TestDocumentModel:
    def test_create_document(self, db_session: Session) -> None:
        doc = Document(
            source_type="local_folder",
            source_id="downloads",
            original_filename="factura.pdf",
            internal_filename="abc123.pdf",
            file_hash="a" * 64,
            file_size=1024,
            mime_type="application/pdf",
            status="DETECTED",
            raw_path="/data/raw/abc123.pdf",
        )
        db_session.add(doc)
        db_session.commit()

        retrieved = db_session.get(Document, doc.id)
        assert retrieved is not None
        assert retrieved.source_type == "local_folder"
        assert retrieved.file_hash == "a" * 64
        assert retrieved.status == "DETECTED"

    def test_file_hash_unique_constraint(self, db_session: Session) -> None:
        doc1 = Document(
            source_type="local_folder",
            source_id="downloads",
            original_filename="a.pdf",
            internal_filename="a.pdf",
            file_hash="b" * 64,
            file_size=100,
            mime_type="application/pdf",
            status="DETECTED",
            raw_path="/raw/a.pdf",
        )
        doc2 = Document(
            source_type="local_folder",
            source_id="downloads",
            original_filename="b.pdf",
            internal_filename="b.pdf",
            file_hash="b" * 64,
            file_size=200,
            mime_type="application/pdf",
            status="DETECTED",
            raw_path="/raw/b.pdf",
        )
        db_session.add(doc1)
        db_session.commit()

        db_session.add(doc2)
        with pytest.raises(Exception):
            db_session.commit()

    def test_document_default_status(self, db_session: Session) -> None:
        doc = Document(
            source_type="local_folder",
            source_id="downloads",
            original_filename="test.pdf",
            internal_filename="test.pdf",
            file_hash="c" * 64,
            file_size=100,
            mime_type="application/pdf",
            raw_path="/raw/test.pdf",
        )
        db_session.add(doc)
        db_session.commit()
        assert doc.status == "DETECTED"


class TestExtractedDataModel:
    def test_one_to_one_relationship(self, db_session: Session) -> None:
        doc = Document(
            source_type="local_folder",
            source_id="downloads",
            original_filename="factura.pdf",
            internal_filename="abc.pdf",
            file_hash="d" * 64,
            file_size=100,
            mime_type="application/pdf",
            status="DETECTED",
            raw_path="/raw/abc.pdf",
        )
        db_session.add(doc)
        db_session.flush()

        extracted = ExtractedData(
            document_id=doc.id,
            document_type="invoice",
            confidence=0.85,
            extracted_text="Invoice text here",
            extracted_fields={"issuer": "Endesa", "total": 84.32},
        )
        db_session.add(extracted)
        db_session.commit()

        assert doc.extracted_data is not None
        assert doc.extracted_data.document_type == "invoice"
        assert doc.extracted_data.confidence == 0.85

    def test_unique_document_id_constraint(self, db_session: Session) -> None:
        doc = Document(
            source_type="local_folder",
            source_id="downloads",
            original_filename="test.pdf",
            internal_filename="test.pdf",
            file_hash="e" * 64,
            file_size=100,
            mime_type="application/pdf",
            status="DETECTED",
            raw_path="/raw/test.pdf",
        )
        db_session.add(doc)
        db_session.flush()

        ed1 = ExtractedData(document_id=doc.id, document_type="invoice", confidence=0.5)
        ed2 = ExtractedData(document_id=doc.id, document_type="unknown", confidence=0.0)
        db_session.add(ed1)
        db_session.commit()

        db_session.add(ed2)
        with pytest.raises(Exception):
            db_session.commit()


class TestProcessingAttemptModel:
    def test_multiple_attempts(self, db_session: Session) -> None:
        doc = Document(
            source_type="local_folder",
            source_id="downloads",
            original_filename="test.pdf",
            internal_filename="test.pdf",
            file_hash="f" * 64,
            file_size=100,
            mime_type="application/pdf",
            status="DETECTED",
            raw_path="/raw/test.pdf",
        )
        db_session.add(doc)
        db_session.flush()

        a1 = ProcessingAttempt(
            document_id=doc.id,
            attempt_number=1,
            step="extraction",
            status="failed",
            error_type="TRANSIENT",
            error_message="File locked",
            started_at=datetime.now(timezone.utc),
        )
        a2 = ProcessingAttempt(
            document_id=doc.id,
            attempt_number=2,
            step="extraction",
            status="success",
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
        )
        db_session.add_all([a1, a2])
        db_session.commit()

        assert len(doc.processing_attempts) == 2
        assert doc.processing_attempts[0].attempt_number == 1
        assert doc.processing_attempts[1].status == "success"


class TestStateTransitionModel:
    def test_transitions_recorded(self, db_session: Session) -> None:
        doc = Document(
            source_type="local_folder",
            source_id="downloads",
            original_filename="test.pdf",
            internal_filename="test.pdf",
            file_hash="g" * 64,
            file_size=100,
            mime_type="application/pdf",
            status="DETECTED",
            raw_path="/raw/test.pdf",
        )
        db_session.add(doc)
        db_session.flush()

        t1 = StateTransition(
            document_id=doc.id,
            from_state="DETECTED",
            to_state="PROCESSING",
            created_by="worker",
        )
        t2 = StateTransition(
            document_id=doc.id,
            from_state="PROCESSING",
            to_state="TEXT_EXTRACTED",
            reason="Extraction successful",
            created_by="worker",
        )
        db_session.add_all([t1, t2])
        db_session.commit()

        assert len(doc.state_transitions) == 2
        assert doc.state_transitions[0].from_state == "DETECTED"
        assert doc.state_transitions[1].to_state == "TEXT_EXTRACTED"


class TestDocumentRepository:
    def test_create_and_get_by_id(self, db_session: Session) -> None:
        repo = DocumentRepository(db_session)
        doc = repo.create(
            source_type="local_folder",
            source_id="downloads",
            original_filename="test.pdf",
            internal_filename="test.pdf",
            file_hash="h" * 64,
            file_size=100,
            mime_type="application/pdf",
            raw_path="/raw/test.pdf",
        )
        db_session.commit()

        retrieved = repo.get_by_id(doc.id)
        assert retrieved is not None
        assert retrieved.file_hash == "h" * 64

    def test_get_by_hash(self, db_session: Session) -> None:
        repo = DocumentRepository(db_session)
        doc = repo.create(
            source_type="local_folder",
            source_id="downloads",
            original_filename="test.pdf",
            internal_filename="test.pdf",
            file_hash="i" * 64,
            file_size=100,
            mime_type="application/pdf",
            raw_path="/raw/test.pdf",
        )
        db_session.commit()

        retrieved = repo.get_by_hash("i" * 64)
        assert retrieved is not None
        assert retrieved.id == doc.id

    def test_exists_by_hash(self, db_session: Session) -> None:
        repo = DocumentRepository(db_session)
        assert not repo.exists_by_hash("j" * 64)

        repo.create(
            source_type="local_folder",
            source_id="downloads",
            original_filename="test.pdf",
            internal_filename="test.pdf",
            file_hash="j" * 64,
            file_size=100,
            mime_type="application/pdf",
            raw_path="/raw/test.pdf",
        )
        db_session.commit()

        assert repo.exists_by_hash("j" * 64)

    def test_set_processing_lease(self, db_session: Session) -> None:
        repo = DocumentRepository(db_session)
        doc = repo.create(
            source_type="local_folder",
            source_id="downloads",
            original_filename="test.pdf",
            internal_filename="test.pdf",
            file_hash="k" * 64,
            file_size=100,
            mime_type="application/pdf",
            raw_path="/raw/test.pdf",
        )
        db_session.commit()

        expires = datetime.now(timezone.utc) + timedelta(seconds=300)
        repo.set_processing_lease(doc, "worker-1", expires)
        db_session.commit()

        assert doc.status == "PROCESSING"
        assert doc.processed_by == "worker-1"
        assert doc.processing_lease_expires_at is not None

    def test_get_pending_documents(self, db_session: Session) -> None:
        repo = DocumentRepository(db_session)
        doc1 = repo.create(
            source_type="local_folder",
            source_id="downloads",
            original_filename="a.pdf",
            internal_filename="a.pdf",
            file_hash="l" * 64,
            file_size=100,
            mime_type="application/pdf",
            raw_path="/raw/a.pdf",
        )
        doc2 = repo.create(
            source_type="local_folder",
            source_id="downloads",
            original_filename="b.pdf",
            internal_filename="b.pdf",
            file_hash="m" * 64,
            file_size=100,
            mime_type="application/pdf",
            raw_path="/raw/b.pdf",
        )
        db_session.commit()

        pending = repo.get_pending_documents(limit=10)
        assert len(pending) == 2
        assert pending[0].received_at <= pending[1].received_at

    def test_expired_lease_is_pending(self, db_session: Session) -> None:
        repo = DocumentRepository(db_session)
        doc = repo.create(
            source_type="local_folder",
            source_id="downloads",
            original_filename="test.pdf",
            internal_filename="test.pdf",
            file_hash="n" * 64,
            file_size=100,
            mime_type="application/pdf",
            raw_path="/raw/test.pdf",
        )
        db_session.commit()

        past = datetime.now(timezone.utc) - timedelta(seconds=600)
        repo.set_processing_lease(doc, "worker-1", past)
        db_session.commit()

        pending = repo.get_pending_documents()
        assert len(pending) == 1
        assert pending[0].id == doc.id
