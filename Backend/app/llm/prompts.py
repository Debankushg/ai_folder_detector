"""Prompts sent to the LLM (system prompt + RAG-seeded first message)."""
import json
from pathlib import Path

from ..diagram.graph_cleaner import NODE_TYPES
from ..rag.code_index import CodeIndex

SYSTEM = f"""You are a software architect. Explain how a project works as a block diagram.
You can explore the code with tools (list_files, read_file, search_code). Use them to verify
the real flow instead of guessing; a few targeted calls are enough.
When done, reply with ONLY a JSON object:
{{"summary": "2-4 sentences", "nodes": [{{"id": "short_id", "label": "Name", "type": one of {NODE_TYPES},
 "description": "what it does", "files": ["key/file.py"]}}], "edges": [{{"from": "id", "to": "id", "label": "what flows"}}],
 "tech": {{"frontend": [{{"name": "React", "category": "UI library", "detail": "how it is used"}}],
           "backend": [...same shape...], "other": [...database, DevOps, hosting, CI...]}}}}
For "tech", list the technologies this project actually uses, verified from dependency files and code
(e.g. package.json, requirements.txt). Put client-side/UI technologies in frontend and server, API,
database and AI technologies in backend. A static detection result is provided; correct and extend it.
Use 6-16 nodes ordered from user/entry point through to data/external systems. Edge direction = flow of control/data."""


def build_first_message(root: Path, scan: dict) -> str:
    """RAG: pre-seed the prompt with code chunks relevant to "how does this app work"."""
    seed = CodeIndex(root).search("application entry point routes api database request flow", 6)
    seed_txt = "\n\n".join(f"### {h['file']}:{h['start']}\n{h['text'][:800]}" for h in seed)
    context = json.dumps({k: scan[k] for k in ("languages", "entry_points", "group_sizes", "group_edges", "tech")})
    return f"Static scan:\n{context}\n\nRetrieved code:\n{seed_txt}\n\nDescribe the project flow."
