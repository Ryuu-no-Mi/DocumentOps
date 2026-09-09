"""Tests for API endpoints against real PostgreSQL."""

import os
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from documentops.api.main import app
from documentops.domain.models import DocumentStatus
from documentops.infrastructure.db.base import Base
from documentops.infrastructure.db.models import (
    Document,
    ExtractedData,
    ProcessingAttempt,
    StateTransition,
)
from documentops.infrastructure.db.session import get_db

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://documentops:documentops@localhost:5432/documentops"
)

engine = create_engine(DATABASE_URL, echo=False)
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def clean_db():
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM state_transitions"))
        conn.execute(text("DELETE FROM processing_attempts"))
        conn.execute(text("DELETE FROM extracted_data"))
        conn.execute(text("DELETE FROM documents"))
        conn.commit()
    yield


@pytest.fixture
def sample_document():
    doc = Document(
        source_type="local_folder",
        source_id="test",
        original_filename="invoice.pdf",
        internal_filename="invoice_internal.pdf",
        file_hash="a" * 64,
        file_size=1024,
        mime_type="application/pdf",
        status=DocumentStatus.COMPLETED.value,
        raw_path="/app/data/raw/invoice_internal.pdf",
        processed_path="/app/data/processed/invoice/2026/09/invoice.pdf",
    )
    with TestSession() as db:
        db.add(doc)
        db.commit()
        db.refresh(doc)
        doc_id = doc.id
    return doc_id


@pytest.fixture
def sample_document_with_details(sample_document):
    doc_id = sample_document
    with TestSession() as db:
        ed = ExtractedData(
            document_id=doc_id,
            document_type="invoice",
            confidence=0.85,
            extracted_fields={"issuer": "Endesa", "total": 84.32},
            validation_errors=None,
        )
        db.add(ed)

        a1 = ProcessingAttempt(
            document_id=doc_id,
            attempt_number=1,
            step="extract",
            status="success",
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
        )
        a2 = ProcessingAttempt(
            document_id=doc_id,
            attempt_number=1,
            step="classify",
            status="success",
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
        )
        db.add_all([a1, a2])

        t1 = StateTransition(
            document_id=doc_id,
            from_state="",
            to_state="DETECTED",
            reason="Document ingested",
            created_by="ingestion",
        )
        t2 = StateTransition(
            document_id=doc_id,
            from_state="DETECTED",
            to_state="PROCESSING",
            reason="Pipeline started",
            created_by="processor",
        )
        db.add_all([t1, t2])
        db.commit()

    return doc_id


client = TestClient(app)


class TestHealthEndpoint:
    def test_health(self) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestListDocuments:
    def test_empty_list(self) -> None:
        response = client.get("/documents")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_list_with_documents(self, sample_document) -> None:
        response = client.get("/documents")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["original_filename"] == "invoice.pdf"

    def test_filter_by_status(self, sample_document) -> None:
        response = client.get("/documents?status=COMPLETED")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1

        response = client.get("/documents?status=FAILED")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_pagination(self, sample_document) -> None:
        response = client.get("/documents?page=1&page_size=1")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 1


class TestGetDocument:
    def test_get_existing_document(self, sample_document) -> None:
        doc_id = sample_document
        response = client.get(f"/documents/{doc_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(doc_id)
        assert data["original_filename"] == "invoice.pdf"
        assert data["status"] == "COMPLETED"

    def test_get_nonexistent_document(self) -> None:
        fake_id = uuid.uuid4()
        response = client.get(f"/documents/{fake_id}")
        assert response.status_code == 404


class TestGetExtractedData:
    def test_get_extracted_data(self, sample_document_with_details) -> None:
        doc_id = sample_document_with_details
        response = client.get(f"/documents/{doc_id}/extracted-data")
        assert response.status_code == 200
        data = response.json()
        assert data["document_type"] == "invoice"
        assert data["confidence"] == 0.85
        assert data["extracted_fields"]["issuer"] == "Endesa"

    def test_no_extracted_data(self, sample_document) -> None:
        doc_id = sample_document
        response = client.get(f"/documents/{doc_id}/extracted-data")
        assert response.status_code == 404


class TestGetProcessingAttempts:
    def test_get_attempts(self, sample_document_with_details) -> None:
        doc_id = sample_document_with_details
        response = client.get(f"/documents/{doc_id}/attempts")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        steps = {a["step"] for a in data}
        assert "extract" in steps
        assert "classify" in steps


class TestGetStateTransitions:
    def test_get_transitions(self, sample_document_with_details) -> None:
        doc_id = sample_document_with_details
        response = client.get(f"/documents/{doc_id}/transitions")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["to_state"] == "DETECTED"
        assert data[1]["to_state"] == "PROCESSING"


class TestReprocessDocument:
    def test_reprocess_completed_document(self, sample_document) -> None:
        doc_id = sample_document
        response = client.post(f"/documents/{doc_id}/reprocess")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "DETECTED"
        assert "was COMPLETED" in data["message"]

    def test_reprocess_failed_document(self) -> None:
        with TestSession() as db:
            doc = Document(
                source_type="local_folder",
                source_id="test",
                original_filename="failed.pdf",
                internal_filename="failed_internal.pdf",
                file_hash="b" * 64,
                file_size=100,
                mime_type="application/pdf",
                status=DocumentStatus.FAILED.value,
                raw_path="/app/data/raw/failed_internal.pdf",
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            doc_id = doc.id

        response = client.post(f"/documents/{doc_id}/reprocess")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "DETECTED"

    def test_cannot_reprocess_processing_document(self) -> None:
        with TestSession() as db:
            doc = Document(
                source_type="local_folder",
                source_id="test",
                original_filename="processing.pdf",
                internal_filename="processing_internal.pdf",
                file_hash="c" * 64,
                file_size=100,
                mime_type="application/pdf",
                status=DocumentStatus.PROCESSING.value,
                raw_path="/app/data/raw/processing_internal.pdf",
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            doc_id = doc.id

        response = client.post(f"/documents/{doc_id}/reprocess")
        assert response.status_code == 409

    def test_reprocess_nonexistent_document(self) -> None:
        fake_id = uuid.uuid4()
        response = client.post(f"/documents/{fake_id}/reprocess")
        assert response.status_code == 404
