"""Tests for file organizer."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from documentops.domain.models import DocumentType
from documentops.processing.organizer import FileOrganizer


class TestFileOrganizer:
    def test_organize_invoice_to_processed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.pdf"
            source.write_bytes(b"%PDF-1.4 content")

            with patch("documentops.processing.organizer.settings") as mock_s:
                mock_s.processed_dir = str(Path(tmpdir) / "processed")

                organizer = FileOrganizer()
                result = organizer.organize_to_processed(
                    source, DocumentType.INVOICE, "2026-09-01", "2026/92837", "abc12345"
                )
                assert result.exists()
                assert "processed" in str(result)
                assert "invoice" in str(result)
                assert "2026" in str(result)
                assert "abc12345" in result.name

    def test_organize_unknown_to_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.pdf"
            source.write_bytes(b"%PDF-1.4 content")

            with patch("documentops.processing.organizer.settings") as mock_s:
                mock_s.review_dir = str(Path(tmpdir) / "review")

                organizer = FileOrganizer()
                result = organizer.organize_to_processed(
                    source, DocumentType.UNKNOWN, None, None, "abc12345"
                )
                assert result.exists()
                assert "review" in str(result)
                assert "unknown" in str(result)

    def test_organize_to_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.pdf"
            source.write_bytes(b"%PDF-1.4 content")

            with patch("documentops.processing.organizer.settings") as mock_s:
                mock_s.failed_dir = str(Path(tmpdir) / "failed")

                organizer = FileOrganizer()
                result = organizer.organize_to_failed(source, "abc12345")
                assert result.exists()
                assert "failed" in str(result)
                assert "abc12345" in result.name

    def test_organize_to_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.pdf"
            source.write_bytes(b"%PDF-1.4 content")

            with patch("documentops.processing.organizer.settings") as mock_s:
                mock_s.review_dir = str(Path(tmpdir) / "review")

                organizer = FileOrganizer()
                result = organizer.organize_to_review(source, DocumentType.INVOICE, "abc12345")
                assert result.exists()
                assert "review" in str(result)
                assert "invoice" in str(result)

    def test_source_file_removed_after_move(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.pdf"
            source.write_bytes(b"%PDF-1.4 content")

            with patch("documentops.processing.organizer.settings") as mock_s:
                mock_s.processed_dir = str(Path(tmpdir) / "processed")

                organizer = FileOrganizer()
                organizer.organize_to_processed(
                    source, DocumentType.INVOICE, "2026-09-01", "001", "abc12345"
                )
                assert not source.exists()
