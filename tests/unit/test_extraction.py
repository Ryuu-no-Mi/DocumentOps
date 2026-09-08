"""Tests for text extraction."""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from documentops.processing.extraction import TextExtractor


class TestTextExtractor:
    def test_extract_from_valid_pdf(self) -> None:
        import pymupdf

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            tmpfile = Path(f.name)

        try:
            doc = pymupdf.open()
            page = doc.new_page()
            page.insert_text((72, 72), "Hello World Invoice 12345")
            doc.save(str(tmpfile))
            doc.close()

            extractor = TextExtractor()
            text = extractor.extract(str(tmpfile))
            assert isinstance(text, str)
            assert "Hello World" in text
        finally:
            tmpfile.unlink()

    def test_extract_from_nonexistent_file(self) -> None:
        extractor = TextExtractor()
        with pytest.raises(RuntimeError, match="Cannot open PDF"):
            extractor.extract("/nonexistent/file.pdf")

    def test_extract_from_corrupt_file(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"this is not a valid PDF")
            tmpfile = Path(f.name)

        try:
            extractor = TextExtractor()
            with pytest.raises(RuntimeError, match="Cannot open PDF"):
                extractor.extract(str(tmpfile))
        finally:
            tmpfile.unlink()

    def test_extract_respects_max_length(self) -> None:
        import pymupdf

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            tmpfile = Path(f.name)

        try:
            doc = pymupdf.open()
            page = doc.new_page()
            page.insert_text((72, 72), "A" * 1000)
            doc.save(str(tmpfile))
            doc.close()

            extractor = TextExtractor()
            mock_settings = MagicMock()
            mock_settings.max_extracted_text_length = 5

            with patch("documentops.processing.extraction.settings", mock_settings):
                with pytest.raises(ValueError, match="exceeds maximum length"):
                    extractor.extract(str(tmpfile))
        finally:
            tmpfile.unlink()
