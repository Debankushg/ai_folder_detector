"""Orchestrates diagram generation: pick provider -> RAG prompt -> MCP + LLM -> graph (or fallback)."""
import os
from pathlib import Path

from ..analysis.tech_detector import merge_tech
from ..diagram.fallback_graph import fallback_graph
from ..mcp_tools.mcp_client import run_with_mcp
from .anthropic_provider import run_anthropic
from .gemini_provider import run_gemini
from .prompts import build_first_message


def _leaf(e: BaseException) -> BaseException:
    while isinstance(e, BaseExceptionGroup) and e.exceptions:
        e = e.exceptions[0]
    return e


def select_provider() -> str | None:
    """LLM_PROVIDER=gemini|anthropic, or auto-detect from whichever key is set."""
    choice = os.getenv("LLM_PROVIDER", "").lower()
    if choice in ("gemini", "anthropic"):
        return choice
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        return "gemini"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    return None


async def build_graph(root: Path, scan: dict) -> tuple[dict, str, str | None]:
    """Returns (graph, mode, warning)."""
    provider = select_provider()
    if provider:
        loop = run_gemini if provider == "gemini" else run_anthropic
        try:
            graph = await run_with_mcp(root, build_first_message(root, scan), loop)
            graph["tech"] = merge_tech(graph.get("tech"), scan["tech"])
            return graph, f"{provider}+rag+mcp", None
        except BaseException as e:  # keep the app usable if the LLM call fails
            if isinstance(e, (KeyboardInterrupt, SystemExit)):
                raise
            leaf = _leaf(e)
            return (fallback_graph(scan, root), "static",
                    f"{provider} analysis failed: {type(leaf).__name__}: {str(leaf)[:300]}")
    return (fallback_graph(scan, root), "static",
            "No LLM key set (GEMINI_API_KEY or ANTHROPIC_API_KEY) - showing import-based diagram only.")
