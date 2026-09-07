"""File storage operations."""

import hashlib
import re
import shutil
import uuid
from pathlib import Path

from documentops.config.settings import settings


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by removing unsafe characters.

    Keeps only alphanumeric, hyphens, underscores, dots.
    Preserves the original extension.
    """
    stem = Path(filename).stem
    suffix = Path(filename).suffix

    safe_stem = re.sub(r"[^a-zA-Z0-9_\-.]", "_", stem)
    safe_stem = safe_stem.strip("_.")
    if not safe_stem:
        safe_stem = "document"

    return f"{safe_stem}{suffix}"


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def generate_internal_filename(original_filename: str) -> str:
    """Generate a unique internal filename."""
    safe = sanitize_filename(original_filename)
    unique_id = uuid.uuid4().hex[:12]
    stem = Path(safe).stem
    suffix = Path(safe).suffix
    return f"{stem}_{unique_id}{suffix}"


def copy_to_raw(source_path: Path, internal_filename: str) -> Path:
    """Copy a file to the raw storage directory.

    Returns the relative path within raw/.
    """
    raw_dir = Path(settings.raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)

    destination = raw_dir / internal_filename
    shutil.copy2(source_path, destination)

    return destination


def ensure_storage_directories() -> None:
    """Create all storage directories if they don't exist."""
    for dir_path in [
        settings.input_dir,
        settings.raw_dir,
        settings.processed_dir,
        settings.failed_dir,
        settings.review_dir,
    ]:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
