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

    def test_extract_endesa_real_format(self) -> None:
        text = """
        ENDESA ENERGÍA
        CIF: A12345678
        Factura nº 2026/92837
        Fecha de emisión: 01/09/2026
        Total a pagar 84,32 EUR
        """
        data = DataExtractor().extract(DocumentType.INVOICE, text)
        assert data is not None
        assert data.issuer == "Endesa"
        assert data.invoice_number == "2026/92837"
        assert data.date == "2026-09-01"
        assert data.total == 84.32
        assert data.currency == "EUR"

    def test_extract_kaixo_real_format(self) -> None:
        text = """
        Factura
        Kaixo Delivery SL
        AV Manoteras, 24 2º
        TOTAL 493,68€
        Factura nº 00002
        13 de febrero de 2026
        """
        data = DataExtractor().extract(DocumentType.INVOICE, text)
        assert data is not None
        assert data.issuer == "Kaixo Delivery SL"
        assert data.invoice_number == "00002"
        assert data.date == "2026-02-13"
        assert data.total == 493.68
        assert data.currency == "EUR"

    def test_extract_sencilla_real_format(self) -> None:
        text = """
        DISTRIBUCIONES FICTICIAS DE PRUEBA
        NIF/CIF: X0000000T
        FECHA Nº FACTURA PÁGINA
        24-11-2012 98765 1
        Exento I.V.A. Base I.V.A. Cuota I.V.A. TOTAL FACTURA
        1.026,00 215,46 1.241,46
        """
        data = DataExtractor().extract(DocumentType.INVOICE, text)
        assert data is not None
        assert data.issuer == "DISTRIBUCIONES FICTICIAS DE PRUEBA"
        assert data.invoice_number == "98765"
        assert data.date == "2012-11-24"
        assert data.total == 1241.46
        assert data.currency is None

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
        assert extractor._extract_invoice_number("Factura\nKaixo Delivery SL") is None
        assert extractor._extract_invoice_number("FECHA Nº FACTURA PÁGINA\n24-11-2012 98765 1") == "98765"

    def test_extract_date_formats(self) -> None:
        extractor = DataExtractor()

        assert extractor._extract_date("01/09/2026") == "2026-09-01"
        assert extractor._extract_date("2026-09-01") == "2026-09-01"
        assert extractor._extract_date("13 de febrero de 2026") == "2026-02-13"
        assert extractor._extract_date("24-11-2012") == "2012-11-24"

    def test_extract_total_prefers_final_total(self) -> None:
        extractor = DataExtractor()
        text = "SUB-TOTAL 408 €\nIVA 85,68\nTOTAL 493,68€"
        assert extractor._extract_total(text) == 493.68

    def test_extract_total_on_following_line(self) -> None:
        extractor = DataExtractor()
        text = "SUB-TOTAL\n408 €\nTOTAL\n493,68€"
        assert extractor._extract_total(text) == 493.68

    def test_extract_currency_eur(self) -> None:
        extractor = DataExtractor()
        assert extractor._extract_currency("Total: 84,32 EUR") == "EUR"
        assert extractor._extract_currency("Total: 84,32 €") == "EUR"

    def test_extract_currency_usd(self) -> None:
        extractor = DataExtractor()
        assert extractor._extract_currency("Total: $100.00") == "USD"
