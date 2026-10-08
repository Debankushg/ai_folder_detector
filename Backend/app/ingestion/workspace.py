"""Temporary working folders for incoming projects."""
import tempfile
from pathlib import Path


def new_workdir() -> Path:
    return Path(tempfile.mkdtemp(prefix="flowmap_"))


def collapse_single_root(path: Path) -> Path:
    """If the archive/clone has one top-level folder, use that as the project root."""
    entries = [p for p in path.iterdir() if p.name != "__MACOSX"]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return path
