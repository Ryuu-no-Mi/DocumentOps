"""Document classification using deterministic rules."""

import logging
import re

from documentops.domain.models import DocumentType

logger = logging.getLogger(__name__)

INVOICE_PATTERNS = [
    r"(?i)factura",
    r"(?i)invoice",
    r"(?i)n[º°]\s*\d+",
    r"(?i)invoice\s*(?:number|no|#)",
    r"(?i)fecha\s*(?:de\s*)?emisi[oó]n",
    r"(?i)due\s*date",
    r"(?i)total\s*(?:a\s*pagar)?",
    r"(?i)importe\s*total",
    r"(?i)(?:iva|vat|tax)",
]

INVOICE_ISSUER_PATTERNS = [
    r"(?i)(endesa)",
    r"(?i)(iberdrola)",
    r"(?i)(naturgy)",
    r"(?i)(repsol)",
    r"(?i)(movistar)",
    r"(?i)(orange)",
    r"(?i)(vodafone)",
]


class DocumentClassifier:
    """Classifies documents using deterministic pattern matching."""

    def classify(self, text: str) -> tuple[DocumentType, float]:
        """Classify a document based on its text content.

        Returns:
            Tuple of (document_type, confidence).
        """
        if not text.strip():
            return DocumentType.UNKNOWN, 0.0

        matches = 0
        total_patterns = len(INVOICE_PATTERNS)

        for pattern in INVOICE_PATTERNS:
            if re.search(pattern, text):
                matches += 1

        if matches == 0:
            return DocumentType.UNKNOWN, 0.0

        confidence = matches / total_patterns

        if confidence >= 0.3:
            return DocumentType.INVOICE, min(confidence, 1.0)

        return DocumentType.UNKNOWN, confidence
