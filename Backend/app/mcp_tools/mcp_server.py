"""MCP server (stdio) exposing read-only tools over one project directory.

Launched by mcp_client.py as a subprocess (python -m app.mcp_tools.mcp_server) with
PROJECT_ROOT set. The LLM calls these tools through the MCP protocol to explore the code.
"""
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from ..analysis.file_utils import SKIP_DIRS
from ..rag.code_index import CodeIndex

ROOT = Path(os.environ["PROJECT_ROOT"]).resolve()


mcp = FastMCP("project-explorer")


_index: CodeIndex | None = None


def _safe(rel: str) -> Path:
    p = (ROOT / rel).resolve()
    if not p.is_relative_to(ROOT):
        raise ValueError("Path escapes project root.")
    return p


@mcp.tool()
def list_files(subdir: str = "") -> str:
    """List files and folders (one level) inside a project subdirectory."""
    d = _safe(subdir)
    if not d.is_dir():
        return "Not a directory."
    rows = []
    for p in sorted(d.iterdir()):
        if p.name in SKIP_DIRS:
            continue
        rows.append(p.name + ("/" if p.is_dir() else ""))
    return "\n".join(rows[:200]) or "(empty)"


@mcp.tool()
def read_file(path: str, max_chars: int = 6000) -> str:
    """Read the start of a source file (path relative to project root)."""
    p = _safe(path)
    if not p.is_file():
        return "File not found."
    return p.read_text(encoding="utf-8", errors="ignore")[: min(max_chars, 12000)]


@mcp.tool()
def search_code(query: str, k: int = 5) -> str:
    """RAG search: return the most relevant code chunks for a natural-language query."""
    global _index
    if _index is None:
        _index = CodeIndex(ROOT)
    hits = _index.search(query, min(k, 8))
    if not hits:
        return "No matches."
    return "\n\n".join(f"### {h['file']}:{h['start']} (score {h['score']})\n{h['text'][:1200]}" for h in hits)


if __name__ == "__main__":
    mcp.run()
