"""PDF text extraction using PyMuPDF."""

import logging

import pymupdf

from documentops.config.settings import settings

logger = logging.getLogger(__name__)


class TextExtractor:
    """Extracts text content from PDF files."""

    def extract(self, file_path: str) -> str:
        """Extract text from a PDF file.

        Raises:
            ValueError: If text exceeds MAX_EXTRACTED_TEXT_LENGTH.
            RuntimeError: If PDF cannot be read.
        """
        try:
            doc = pymupdf.open(file_path)
        except Exception as e:
            raise RuntimeError(f"Cannot open PDF: {e}") from e

        try:
            text_parts = []
            for page in doc:
                text_parts.append(page.get_text())

            full_text = "\n".join(text_parts)

            if len(full_text.encode("utf-8")) > settings.max_extracted_text_length:
                raise ValueError(
                    f"Extracted text exceeds maximum length "
                    f"({len(full_text.encode('utf-8'))} > {settings.max_extracted_text_length})"
                )

            return full_text.strip()

        finally:
            doc.close()
