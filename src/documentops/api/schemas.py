"""API response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    """Response model for a single document."""

    id: uuid.UUID
    source_type: str
    source_id: str
    original_filename: str
    internal_filename: str
    file_hash: str
    file_size: int
    mime_type: str
    status: str
    raw_path: str
    processed_path: str | None = None
    received_at: datetime
    processed_at: datetime | None = None
    processing_started_at: datetime | None = None
    processing_lease_expires_at: datetime | None = None
    processed_by: str | None = None
    created_at: datetime
    updated_at: datetime
    metadata: dict | None = None


class DocumentSummary(BaseModel):
    """Summary response for document list."""

    id: uuid.UUID
    source_type: str
    original_filename: str
    file_hash: str
    file_size: int
    mime_type: str
    status: str
    received_at: datetime
    processed_at: datetime | None = None
    created_at: datetime


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""

    items: list[DocumentSummary]
    page: int
    page_size: int
    total: int


class ExtractedDataResponse(BaseModel):
    """Response model for extracted data."""

    id: uuid.UUID
    document_id: uuid.UUID
    document_type: str
    confidence: float
    extracted_fields: dict | None = None
    validation_errors: list | None = None
    created_at: datetime
    updated_at: datetime


class ProcessingAttemptResponse(BaseModel):
    """Response model for a processing attempt."""

    id: uuid.UUID
    document_id: uuid.UUID
    attempt_number: int
    step: str
    status: str
    error_type: str | None = None
    error_message: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
    created_at: datetime


class StateTransitionResponse(BaseModel):
    """Response model for a state transition."""

    id: uuid.UUID
    document_id: uuid.UUID
    from_state: str
    to_state: str
    reason: str | None = None
    created_by: str
    created_at: datetime


class ReprocessResponse(BaseModel):
    """Response model for reprocess action."""

    document_id: uuid.UUID
    status: str
    message: str
