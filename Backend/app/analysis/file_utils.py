"""Shared helpers for walking and reading project files."""
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build",
             ".next", ".idea", ".vscode", "target", "vendor", "coverage", ".cache"}


TEXT_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".java", ".go", ".rs",
            ".rb", ".php", ".cs", ".c", ".cpp", ".h", ".md", ".json", ".yml", ".yaml",
            ".toml", ".sql", ".html", ".css", ".sh", ".env.example", ".txt"}


MAX_FILES = 3000


MAX_FILE_BYTES = 200_000


def iter_files(root: Path):
    count = 0
    for p in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in p.relative_to(root).parts):
            continue
        if p.is_file() and p.suffix.lower() in TEXT_EXT and p.stat().st_size <= MAX_FILE_BYTES:
            yield p
            count += 1
            if count >= MAX_FILES:
                return


def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
