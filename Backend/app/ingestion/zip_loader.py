"""Unpack an uploaded project .zip safely."""
import zipfile
from pathlib import Path

from .workspace import collapse_single_root

MAX_UPLOAD_BYTES = 100 * 1024 * 1024
MAX_UNZIPPED_BYTES = 300 * 1024 * 1024


def extract_zip(zip_path: Path, dest: Path) -> Path:
    with zipfile.ZipFile(zip_path) as zf:
        total = sum(i.file_size for i in zf.infolist())
        if total > MAX_UNZIPPED_BYTES:
            raise ValueError("Archive is too large once extracted.")
        dest_resolved = dest.resolve()
        for info in zf.infolist():
            target = (dest / info.filename).resolve()
            if not target.is_relative_to(dest_resolved):  # zip-slip guard
                raise ValueError("Archive contains unsafe paths.")
        zf.extractall(dest)
    return collapse_single_root(dest)
