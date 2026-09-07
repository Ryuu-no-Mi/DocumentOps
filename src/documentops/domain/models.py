"""Pydantic domain models for DocumentOps."""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    """Possible states for a document in the processing pipeline."""

    DETECTED = "DETECTED"
    PROCESSING = "PROCESSING"
    TEXT_EXTRACTED = "TEXT_EXTRACTED"
    CLASSIFIED = "CLASSIFIED"
    DATA_EXTRACTED = "DATA_EXTRACTED"
    VALIDATED = "VALIDATED"
    ORGANIZED = "ORGANIZED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class DocumentType(str, Enum):
    """Supported document types."""

    INVOICE = "invoice"
    UNKNOWN = "unknown"


class ErrorType(str, Enum):
    """Categories of processing errors."""

    TRANSIENT = "TRANSIENT"
    PERMANENT = "PERMANENT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    MIME_TYPE_MISMATCH = "MIME_TYPE_MISMATCH"
    EXTRACTED_TEXT_TOO_LARGE = "EXTRACTED_TEXT_TOO_LARGE"


class AttemptStatus(str, Enum):
    """Status of a processing attempt."""

    SUCCESS = "success"
    FAILED = "failed"


class SourceContext(BaseModel):
    """Context information from the document source."""

    source_type: str = Field(description="Type of source (local_folder, email, etc.)")
    source_id: str = Field(description="Identifier of the source instance")
    original_filename: str = Field(description="Original filename as received")
    received_at: datetime = Field(description="When the document was detected")
    metadata: dict = Field(default_factory=dict, description="Additional source metadata")


class DocumentCreate(BaseModel):
    """Data required to create a new document record."""

    source_type: str
    source_id: str
    original_filename: str
    internal_filename: str
    file_hash: str = Field(min_length=64, max_length=64)
    file_size: int = Field(gt=0)
    mime_type: str
    raw_path: str
    metadata: dict = Field(default_factory=dict)


class DocumentSummary(BaseModel):
    """Summary view of a document."""

    id: uuid.UUID
    source_type: str
    original_filename: str
    file_hash: str
    file_size: int
    mime_type: str
    status: DocumentStatus
    received_at: datetime
    processed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class DocumentDetail(DocumentSummary):
    """Detailed view of a document including source context."""

    source_id: str
    internal_filename: str
    raw_path: str
    processed_path: str | None = None
    processing_started_at: datetime | None = None
    processing_lease_expires_at: datetime | None = None
    processed_by: str | None = None
    metadata: dict | None = None


class ExtractedDataCreate(BaseModel):
    """Data required to create extracted data for a document."""

    document_type: DocumentType
    confidence: float = Field(ge=0.0, le=1.0)
    extracted_text: str | None = None
    extracted_fields: dict | None = None
    validation_errors: list | None = None


class ExtractedDataSummary(BaseModel):
    """Summary of extracted data."""

    id: uuid.UUID
    document_id: uuid.UUID
    document_type: DocumentType
    confidence: float
    extracted_fields: dict | None = None
    validation_errors: list | None = None
    created_at: datetime
    updated_at: datetime


class InvoiceData(BaseModel):
    """Structured data extracted from an invoice."""

    issuer: str | None = None
    invoice_number: str | None = None
    date: str | None = None
    total: float | None = None
    currency: str | None = None


class ProcessingAttemptCreate(BaseModel):
    """Data required to create a processing attempt."""

    document_id: uuid.UUID
    attempt_number: int = Field(gt=0)
    step: str
    status: AttemptStatus
    error_type: ErrorType | None = None
    error_message: str | None = None
    started_at: datetime
    finished_at: datetime | None = None


class ProcessingAttemptSummary(BaseModel):
    """Summary of a processing attempt."""

    id: uuid.UUID
    document_id: uuid.UUID
    attempt_number: int
    step: str
    status: AttemptStatus
    error_type: str | None = None
    error_message: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
    created_at: datetime


class StateTransitionCreate(BaseModel):
    """Data required to create a state transition record."""

    document_id: uuid.UUID
    from_state: DocumentStatus
    to_state: DocumentStatus
    reason: str | None = None
    created_by: str = "system"


class StateTransitionSummary(BaseModel):
    """Summary of a state transition."""

    id: uuid.UUID
    document_id: uuid.UUID
    from_state: str
    to_state: str
    reason: str | None = None
    created_by: str
    created_at: datetime
