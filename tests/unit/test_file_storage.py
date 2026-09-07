"""Tests for file storage operations."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from documentops.infrastructure.storage.file_storage import (
    compute_file_hash,
    copy_to_raw,
    generate_internal_filename,
    sanitize_filename,
)


class TestSanitizeFilename:
    def test_keeps_safe_characters(self) -> None:
        assert sanitize_filename("factura_2026.pdf") == "factura_2026.pdf"

    def test_replaces_unsafe_characters(self) -> None:
        result = sanitize_filename("factura (copia) #1.pdf")
        assert "(" not in result
        assert ")" not in result
        assert "#" not in result
        assert result.endswith(".pdf")

    def test_preserves_extension(self) -> None:
        assert sanitize_filename("document.pdf").endswith(".pdf")

    def test_handles_empty_stem(self) -> None:
        result = sanitize_filename("...pdf")
        assert result.endswith(".pdf")
        assert len(result) > 4

    def test_handles_only_unsafe_characters(self) -> None:
        result = sanitize_filename("@@@.pdf")
        assert result.endswith(".pdf")


class TestComputeFileHash:
    def test_hash_deterministic(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"hello world")
            path = Path(f.name)
        try:
            h1 = compute_file_hash(path)
            h2 = compute_file_hash(path)
            assert h1 == h2
            assert len(h1) == 64
        finally:
            path.unlink()

    def test_hash_different_content(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"content A")
            path_a = Path(f.name)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"content B")
            path_b = Path(f.name)
        try:
            assert compute_file_hash(path_a) != compute_file_hash(path_b)
        finally:
            path_a.unlink()
            path_b.unlink()


class TestGenerateInternalFilename:
    def test_unique_filenames(self) -> None:
        names = {generate_internal_filename("test.pdf") for _ in range(100)}
        assert len(names) == 100

    def test_preserves_extension(self) -> None:
        name = generate_internal_filename("invoice.pdf")
        assert name.endswith(".pdf")

    def test_contains_original_stem(self) -> None:
        name = generate_internal_filename("factura_endesa.pdf")
        assert "factura_endesa" in name


class TestCopyToRaw:
    def test_copies_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.pdf"
            source.write_bytes(b"%PDF-1.4 test content")
            raw_dir = str(Path(tmpdir) / "raw")

            with patch("documentops.infrastructure.storage.file_storage.settings") as mock_settings:
                mock_settings.raw_dir = raw_dir
                result = copy_to_raw(source, "test_abc123.pdf")
                assert result.exists()
                assert result.read_bytes() == b"%PDF-1.4 test content"
