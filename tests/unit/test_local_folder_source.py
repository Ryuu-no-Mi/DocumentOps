"""Tests for LocalFolderSource."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from documentops.sources.local_folder import LocalFolderSource


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestLocalFolderSource:
    @pytest.mark.asyncio
    async def test_poll_empty_directory(self, temp_dir: Path) -> None:
        source = LocalFolderSource(input_dir=temp_dir)
        requests = await source.poll()
        assert requests == []

    @pytest.mark.asyncio
    async def test_poll_detects_pdf(self, temp_dir: Path) -> None:
        (temp_dir / "factura.pdf").write_bytes(b"%PDF-1.4 fake content")
        source = LocalFolderSource(input_dir=temp_dir)
        requests = await source.poll()
        assert len(requests) == 1
        assert requests[0].original_filename == "factura.pdf"
        assert requests[0].source_type == "local_folder"
        assert requests[0].mime_type == "application/pdf"

    @pytest.mark.asyncio
    async def test_poll_ignores_hidden_files(self, temp_dir: Path) -> None:
        (temp_dir / ".hidden.pdf").write_bytes(b"%PDF-1.4")
        (temp_dir / "~temp.pdf").write_bytes(b"%PDF-1.4")
        (temp_dir / "visible.pdf").write_bytes(b"%PDF-1.4")
        source = LocalFolderSource(input_dir=temp_dir)
        requests = await source.poll()
        assert len(requests) == 1
        assert requests[0].original_filename == "visible.pdf"

    @pytest.mark.asyncio
    async def test_poll_ignores_directories(self, temp_dir: Path) -> None:
        (temp_dir / "subdir").mkdir()
        (temp_dir / "subdir" / "doc.pdf").write_bytes(b"%PDF-1.4")
        (temp_dir / "root.pdf").write_bytes(b"%PDF-1.4")
        source = LocalFolderSource(input_dir=temp_dir)
        requests = await source.poll()
        assert len(requests) == 1
        assert requests[0].original_filename == "root.pdf"

    @pytest.mark.asyncio
    async def test_poll_ignores_unsupported_extensions(self, temp_dir: Path) -> None:
        (temp_dir / "doc.pdf").write_bytes(b"%PDF-1.4")
        (temp_dir / "image.png").write_bytes(b"PNG")
        (temp_dir / "text.txt").write_bytes(b"hello")
        source = LocalFolderSource(input_dir=temp_dir)
        requests = await source.poll()
        assert len(requests) == 1
        assert requests[0].original_filename == "doc.pdf"

    @pytest.mark.asyncio
    async def test_poll_ignores_oversized_files(self, temp_dir: Path) -> None:
        (temp_dir / "huge.pdf").write_bytes(b"%PDF-1.4" + b"x" * 1000)
        source = LocalFolderSource(input_dir=temp_dir, max_file_size=10)
        requests = await source.poll()
        assert len(requests) == 0

    @pytest.mark.asyncio
    async def test_poll_ignores_empty_files(self, temp_dir: Path) -> None:
        (temp_dir / "empty.pdf").write_bytes(b"")
        source = LocalFolderSource(input_dir=temp_dir)
        requests = await source.poll()
        assert len(requests) == 0

    @pytest.mark.asyncio
    async def test_poll_nonexistent_directory(self) -> None:
        source = LocalFolderSource(input_dir="/nonexistent/path")
        requests = await source.poll()
        assert requests == []

    @pytest.mark.asyncio
    async def test_poll_multiple_files(self, temp_dir: Path) -> None:
        (temp_dir / "a.pdf").write_bytes(b"%PDF-1.4 content a")
        (temp_dir / "b.pdf").write_bytes(b"%PDF-1.4 content b")
        (temp_dir / "c.pdf").write_bytes(b"%PDF-1.4 content c")
        source = LocalFolderSource(input_dir=temp_dir)
        requests = await source.poll()
        assert len(requests) == 3
        filenames = {r.original_filename for r in requests}
        assert filenames == {"a.pdf", "b.pdf", "c.pdf"}

    def test_supported_extensions_from_settings(self) -> None:
        source = LocalFolderSource()
        assert ".pdf" in source.supported_extensions
