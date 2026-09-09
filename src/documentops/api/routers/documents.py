"""Document API endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from documentops.api.schemas import (
    DocumentListResponse,
    DocumentResponse,
    DocumentSummary,
    ExtractedDataResponse,
    ProcessingAttemptResponse,
    ReprocessResponse,
    StateTransitionResponse,
)
from documentops.domain.models import DocumentStatus
from documentops.infrastructure.db.models import (
    Document,
    ExtractedData,
    ProcessingAttempt,
    StateTransition,
)
from documentops.infrastructure.db.session import get_db

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=DocumentListResponse)
def list_documents(
    status: str | None = Query(None, description="Filter by status"),
    source_type: str | None = Query(None, description="Filter by source type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
) -> DocumentListResponse:
    """List documents with optional filtering and pagination."""
    query = select(Document)
    count_query = select(func.count()).select_from(Document)

    if status:
        query = query.where(Document.status == status)
        count_query = count_query.where(Document.status == status)

    if source_type:
        query = query.where(Document.source_type == source_type)
        count_query = count_query.where(Document.source_type == source_type)

    total = db.scalar(count_query)

    offset = (page - 1) * page_size
    query = query.order_by(Document.received_at.desc()).offset(offset).limit(page_size)
    documents = list(db.scalars(query).all())

    items = [
        DocumentSummary(
            id=doc.id,
            source_type=doc.source_type,
            original_filename=doc.original_filename,
            file_hash=doc.file_hash,
            file_size=doc.file_size,
            mime_type=doc.mime_type,
            status=doc.status,
            received_at=doc.received_at,
            processed_at=doc.processed_at,
            created_at=doc.created_at,
        )
        for doc in documents
    ]

    return DocumentListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> DocumentResponse:
    """Get a single document by ID."""
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(
        id=document.id,
        source_type=document.source_type,
        source_id=document.source_id,
        original_filename=document.original_filename,
        internal_filename=document.internal_filename,
        file_hash=document.file_hash,
        file_size=document.file_size,
        mime_type=document.mime_type,
        status=document.status,
        raw_path=document.raw_path,
        processed_path=document.processed_path,
        received_at=document.received_at,
        processed_at=document.processed_at,
        processing_started_at=document.processing_started_at,
        processing_lease_expires_at=document.processing_lease_expires_at,
        processed_by=document.processed_by,
        created_at=document.created_at,
        updated_at=document.updated_at,
        metadata=document.metadata_,
    )


@router.get("/{document_id}/extracted-data", response_model=ExtractedDataResponse)
def get_extracted_data(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ExtractedDataResponse:
    """Get extracted data for a document."""
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if not document.extracted_data:
        raise HTTPException(status_code=404, detail="No extracted data for this document")

    ed = document.extracted_data
    return ExtractedDataResponse(
        id=ed.id,
        document_id=ed.document_id,
        document_type=ed.document_type,
        confidence=ed.confidence,
        extracted_fields=ed.extracted_fields,
        validation_errors=ed.validation_errors,
        created_at=ed.created_at,
        updated_at=ed.updated_at,
    )


@router.get("/{document_id}/attempts", response_model=list[ProcessingAttemptResponse])
def get_processing_attempts(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list[ProcessingAttemptResponse]:
    """Get processing attempts for a document."""
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return [
        ProcessingAttemptResponse(
            id=a.id,
            document_id=a.document_id,
            attempt_number=a.attempt_number,
            step=a.step,
            status=a.status,
            error_type=a.error_type,
            error_message=a.error_message,
            started_at=a.started_at,
            finished_at=a.finished_at,
            created_at=a.created_at,
        )
        for a in document.processing_attempts
    ]


@router.get("/{document_id}/transitions", response_model=list[StateTransitionResponse])
def get_state_transitions(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list[StateTransitionResponse]:
    """Get state transitions for a document."""
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return [
        StateTransitionResponse(
            id=t.id,
            document_id=t.document_id,
            from_state=t.from_state,
            to_state=t.to_state,
            reason=t.reason,
            created_by=t.created_by,
            created_at=t.created_at,
        )
        for t in document.state_transitions
    ]


@router.post("/{document_id}/reprocess", response_model=ReprocessResponse)
def reprocess_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ReprocessResponse:
    """Reprocess a document by resetting its state to DETECTED."""
    from documentops.application.services.reprocess import ReprocessService

    service = ReprocessService(db)
    try:
        document = service.reprocess(document_id)
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=409, detail=str(e))

    return ReprocessResponse(
        document_id=document.id,
        status=document.status,
        message=f"Document queued for reprocessing",
    )
