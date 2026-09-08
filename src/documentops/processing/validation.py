"""Validation of extracted document data."""

import logging

from pydantic import ValidationError

from documentops.domain.models import (
    DocumentType,
    ExtractedDataCreate,
    InvoiceData,
)

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of document data validation."""

    def __init__(
        self,
        is_valid: bool,
        errors: list[str] | None = None,
        confidence: float = 0.0,
    ) -> None:
        self.is_valid = is_valid
        self.errors = errors or []
        self.confidence = confidence


class DataValidator:
    """Validates extracted data against domain models."""

    def validate_invoice(self, data: InvoiceData) -> ValidationResult:
        """Validate invoice data.

        Returns ValidationResult with errors if any required fields are missing.
        """
        errors = []

        if not data.issuer:
            errors.append("Missing required field: issuer")
        if not data.invoice_number:
            errors.append("Missing required field: invoice_number")
        if not data.date:
            errors.append("Missing required field: date")
        if data.total is None:
            errors.append("Missing required field: total")
        if not data.currency:
            errors.append("Missing required field: currency")

        if data.total is not None and data.total < 0:
            errors.append("Invalid total: must be non-negative")

        confidence = self._calculate_confidence(data, errors)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors if errors else None,
            confidence=confidence,
        )

    def _calculate_confidence(self, data: InvoiceData, errors: list[str]) -> float:
        """Calculate confidence score based on fields found vs required."""
        required_fields = ["issuer", "invoice_number", "date", "total", "currency"]
        found = sum(
            1 for field in required_fields
            if getattr(data, field) is not None
        )
        return found / len(required_fields)
