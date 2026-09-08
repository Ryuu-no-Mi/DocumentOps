"""Tests for data validation."""

from documentops.domain.models import InvoiceData
from documentops.processing.validation import DataValidator


class TestDataValidator:
    def test_validate_complete_invoice(self) -> None:
        data = InvoiceData(
            issuer="Endesa",
            invoice_number="2026/92837",
            date="2026-09-01",
            total=84.32,
            currency="EUR",
        )
        validator = DataValidator()
        result = validator.validate_invoice(data)
        assert result.is_valid
        assert result.errors == []
        assert result.confidence == 1.0

    def test_validate_missing_fields(self) -> None:
        data = InvoiceData(issuer="Endesa")
        validator = DataValidator()
        result = validator.validate_invoice(data)
        assert not result.is_valid
        assert len(result.errors) == 4
        assert result.confidence == 0.2

    def test_validate_negative_total(self) -> None:
        data = InvoiceData(
            issuer="Endesa",
            invoice_number="001",
            date="2026-09-01",
            total=-10.0,
            currency="EUR",
        )
        validator = DataValidator()
        result = validator.validate_invoice(data)
        assert not result.is_valid
        assert any("non-negative" in e for e in result.errors)

    def test_validate_partial_data(self) -> None:
        data = InvoiceData(
            issuer="Endesa",
            invoice_number="001",
            date="2026-09-01",
        )
        validator = DataValidator()
        result = validator.validate_invoice(data)
        assert not result.is_valid
        assert len(result.errors) == 2
        assert result.confidence == 0.6
