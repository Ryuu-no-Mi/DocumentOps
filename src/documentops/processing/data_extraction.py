"""Structured data extraction from invoices."""

import logging
import re

from documentops.domain.models import DocumentType, InvoiceData

logger = logging.getLogger(__name__)


class DataExtractor:
    """Extracts structured data from classified documents."""

    def extract(self, document_type: DocumentType, text: str) -> InvoiceData | None:
        """Extract structured data based on document type.

        Returns:
            InvoiceData for invoices, None for unknown types.
        """
        if document_type != DocumentType.INVOICE:
            return None

        return InvoiceData(
            issuer=self._extract_issuer(text),
            invoice_number=self._extract_invoice_number(text),
            date=self._extract_date(text),
            total=self._extract_total(text),
            currency=self._extract_currency(text),
        )

    def _extract_issuer(self, text: str) -> str | None:
        """Extract issuer name from text."""
        known_issuers = [
            "endesa", "iberdrola", "naturgy", "repsol",
            "movistar", "orange", "vodafone", "eon",
        ]
        text_lower = text.lower()
        for issuer in known_issuers:
            if issuer in text_lower:
                return issuer.title()
        return None

    def _extract_invoice_number(self, text: str) -> str | None:
        """Extract invoice number from text."""
        patterns = [
            r"(?i)factura\s*(?:n[º°]?|number|no|#)?\s*[:.]?\s*([A-Za-z0-9/\-]+)",
            r"(?i)invoice\s*(?:number|no|#)?\s*[:.]?\s*([A-Za-z0-9/\-]+)",
            r"(?i)n[º°]\s*([A-Za-z0-9/\-]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return None

    def _extract_date(self, text: str) -> str | None:
        """Extract invoice date from text."""
        patterns = [
            r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})",
            r"(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})",
            r"(?i)fecha\s*(?:de\s*)?emisi[oó]n\s*[:.]?\s*(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    if len(groups[0]) == 4:
                        return f"{groups[0]}-{groups[1].zfill(2)}-{groups[2].zfill(2)}"
                    else:
                        return f"{groups[2]}-{groups[1].zfill(2)}-{groups[0].zfill(2)}"
        return None

    def _extract_total(self, text: str) -> float | None:
        """Extract total amount from text."""
        patterns = [
            r"(?i)total\s*(?:a\s*pagar)?\s*[:.]?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)",
            r"(?i)importe\s*total\s*[:.]?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)",
            r"(?i)(?:amount|total)\s*[:.]?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                amount_str = match.group(1)
                amount_str = amount_str.replace(".", "").replace(",", ".")
                try:
                    return float(amount_str)
                except ValueError:
                    continue
        return None

    def _extract_currency(self, text: str) -> str | None:
        """Extract currency from text."""
        if re.search(r"(?i)\bEUR\b|€", text):
            return "EUR"
        if re.search(r"(?i)\bUSD\b|\$", text):
            return "USD"
        if re.search(r"(?i)\bGBP\b|£", text):
            return "GBP"
        return None
