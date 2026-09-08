"""Tests for structured data extraction."""

from documentops.domain.models import DocumentType
from documentops.processing.data_extraction import DataExtractor


class TestDataExtractor:
    def test_extract_invoice_endesa(self) -> None:
        text = """
        ENDESA ENERGÍA
        Factura nº 2026/92837
        Fecha de emisión: 01/09/2026
        Total a pagar: 84,32 EUR
        """
        extractor = DataExtractor()
        data = extractor.extract(DocumentType.INVOICE, text)
        assert data is not None
        assert data.issuer == "Endesa"
        assert data.invoice_number == "2026/92837"
        assert data.date == "2026-09-01"
        assert data.total == 84.32
        assert data.currency == "EUR"

    def test_extract_unknown_returns_none(self) -> None:
        text = "Some random text"
        extractor = DataExtractor()
        data = extractor.extract(DocumentType.UNKNOWN, text)
        assert data is None

    def test_extract_partial_invoice(self) -> None:
        text = "Some random document without clear fields"
        extractor = DataExtractor()
        data = extractor.extract(DocumentType.INVOICE, text)
        assert data is not None
        assert data.issuer is None
        assert data.invoice_number is None

    def test_extract_invoice_number_formats(self) -> None:
        extractor = DataExtractor()

        assert extractor._extract_invoice_number("Factura nº 2026/92837") == "2026/92837"
        assert extractor._extract_invoice_number("Invoice Number: INV-001") == "INV-001"
        assert extractor._extract_invoice_number("Nº 12345") == "12345"

    def test_extract_date_formats(self) -> None:
        extractor = DataExtractor()

        assert extractor._extract_date("01/09/2026") == "2026-09-01"
        assert extractor._extract_date("2026-09-01") == "2026-09-01"

    def test_extract_currency_eur(self) -> None:
        extractor = DataExtractor()
        assert extractor._extract_currency("Total: 84,32 EUR") == "EUR"
        assert extractor._extract_currency("Total: 84,32 €") == "EUR"

    def test_extract_currency_usd(self) -> None:
        extractor = DataExtractor()
        assert extractor._extract_currency("Total: $100.00") == "USD"
