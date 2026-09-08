"""Tests for document classification."""

from documentops.domain.models import DocumentType
from documentops.processing.classification import DocumentClassifier


class TestDocumentClassifier:
    def test_classify_empty_text(self) -> None:
        classifier = DocumentClassifier()
        doc_type, confidence = classifier.classify("")
        assert doc_type == DocumentType.UNKNOWN
        assert confidence == 0.0

    def test_classify_invoice_spanish(self) -> None:
        text = """
        ENDESA ENERGÍA
        Factura nº 2026/92837
        Fecha de emisión: 01/09/2026
        Total a pagar: 84,32 EUR
        IVA incluido
        """
        classifier = DocumentClassifier()
        doc_type, confidence = classifier.classify(text)
        assert doc_type == DocumentType.INVOICE
        assert confidence > 0.3

    def test_classify_invoice_english(self) -> None:
        text = """
        ACME Corp
        Invoice Number: INV-2026-001
        Due Date: 15/09/2026
        Total: $150.00
        Tax included
        """
        classifier = DocumentClassifier()
        doc_type, confidence = classifier.classify(text)
        assert doc_type == DocumentType.INVOICE
        assert confidence > 0.3

    def test_classify_unknown_document(self) -> None:
        text = """
        This is just a regular letter with no invoice-related content.
        It talks about weather and sports.
        """
        classifier = DocumentClassifier()
        doc_type, confidence = classifier.classify(text)
        assert doc_type == DocumentType.UNKNOWN

    def test_classify_known_issuer(self) -> None:
        text = "Endesa factura nº 12345 total 100 EUR"
        classifier = DocumentClassifier()
        doc_type, confidence = classifier.classify(text)
        assert doc_type == DocumentType.INVOICE

    def test_confidence_scales_with_matches(self) -> None:
        text_minimal = "factura"
        text_full = """
        ENDESA ENERGÍA
        Factura nº 2026/92837
        Fecha de emisión: 01/09/2026
        Total a pagar: 84,32 EUR
        IVA: 21%
        """
        classifier = DocumentClassifier()
        _, conf_minimal = classifier.classify(text_minimal)
        _, conf_full = classifier.classify(text_full)
        assert conf_full > conf_minimal
