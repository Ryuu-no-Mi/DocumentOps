"""Structured data extraction from invoices."""

import logging
import re
from datetime import date

from documentops.domain.models import DocumentType, InvoiceData

logger = logging.getLogger(__name__)

SPANISH_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

AMOUNT_PATTERN = r"\d{1,3}(?:[.\s]\d{3})*(?:,\d{2})|\d+(?:[.,]\d{2})?"


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

        ignored = re.compile(
            r"^(factura|cliente|descripci[oó]n|fecha|forma de pago|"
            r"n[º°o]?\s*factura|nif|cif|iban|direcci[oó]n|telf\.?|fax)\b",
            re.IGNORECASE,
        )
        for line in (line.strip() for line in text.splitlines()):
            if not line or ignored.search(line):
                continue
            if re.search(r"\b(?:S\.?L\.?|S\.?A\.?|S\.?L\.?U\.?)\b", line, re.IGNORECASE):
                return line
            if line == line.upper() and len(line) >= 5 and any(char.isalpha() for char in line):
                return line
        return None

    def _extract_invoice_number(self, text: str) -> str | None:
        """Extract invoice number from text."""
        patterns = [
            r"(?im)\bfactura\s*(?:n[º°o.]|número|numero|num\.?|number|no\.?|#)\s*[:.]?\s*([A-Z0-9][A-Z0-9./-]*\d[A-Z0-9./-]*)\b",
            r"(?im)\binvoice\s*(?:number|no\.?|#)\s*[:.]?\s*([A-Z0-9][A-Z0-9./-]*\d[A-Z0-9./-]*)\b",
            r"(?im)^\s*fecha\s+n[º°o]?\s+factura\s+p[áa]gina.*\n\s*\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\s+([A-Z0-9][A-Z0-9./-]*\d[A-Z0-9./-]*)\b",
            r"(?im)\bn[º°o]?\s+factura\s*[:.]?\s*([A-Z0-9][A-Z0-9./-]*\d[A-Z0-9./-]*)\b",
            r"(?im)\bn[º°o]\s*([A-Z0-9][A-Z0-9./-]*\d[A-Z0-9./-]*)\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return None

    def _extract_date(self, text: str) -> str | None:
        """Extract invoice date from text."""
        patterns = [
            r"(?i)(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})",
            r"(?<!\d)(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})(?!\d)",
            r"(?<!\d)(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})(?!\d)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    if groups[1].lower() in SPANISH_MONTHS:
                        year, month, day = int(groups[2]), SPANISH_MONTHS[groups[1].lower()], int(groups[0])
                        return self._format_date(year, month, day)
                    if len(groups[0]) == 4:
                        return self._format_date(int(groups[0]), int(groups[1]), int(groups[2]))
                    else:
                        return self._format_date(int(groups[2]), int(groups[1]), int(groups[0]))
        return None

    def _extract_total(self, text: str) -> float | None:
        """Extract total amount from text."""
        total_line_patterns = [
            rf"(?im)^\s*total\s+a\s+pagar[ \t]*[:.]?[ \t]*({AMOUNT_PATTERN})",
            rf"(?im)^\s*total\s+factura[ \t]*[:.]?[ \t]*({AMOUNT_PATTERN})",
            rf"(?im)^\s*total[ \t]*[:.]?[ \t]*({AMOUNT_PATTERN})",
            rf"(?im)^\s*importe\s+total[ \t]*[:.]?[ \t]*({AMOUNT_PATTERN})",
        ]
        for pattern in total_line_patterns:
            matches = list(re.finditer(pattern, text))
            if matches:
                return self._parse_amount(matches[-1].group(1))

        table_total = re.search(r"(?im)\btotal\s+factura\b.*\n([^\n]+)", text)
        if table_total:
            amounts = re.findall(AMOUNT_PATTERN, table_total.group(1))
            if amounts:
                return self._parse_amount(amounts[-1])

        total_next_lines = list(re.finditer(r"(?im)^\s*total[ \t]*\n\s*([^\n]+)", text))
        for total_next_line in reversed(total_next_lines):
            amounts = re.findall(AMOUNT_PATTERN, total_next_line.group(1))
            if amounts:
                return self._parse_amount(amounts[-1])
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

    @staticmethod
    def _parse_amount(value: str) -> float | None:
        """Parse common European and US amount formats."""
        normalized = value.replace(" ", "")
        if "," in normalized and "." in normalized:
            if normalized.rfind(",") > normalized.rfind("."):
                normalized = normalized.replace(".", "").replace(",", ".")
            else:
                normalized = normalized.replace(",", "")
        elif "," in normalized:
            normalized = normalized.replace(".", "").replace(",", ".")
        elif normalized.count(".") > 1:
            normalized = normalized.replace(".", "")
        try:
            return float(normalized)
        except ValueError:
            return None

    @staticmethod
    def _format_date(year: int, month: int, day: int) -> str | None:
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            return None
