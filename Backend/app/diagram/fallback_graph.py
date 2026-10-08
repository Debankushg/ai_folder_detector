"""No-LLM diagram built from the static import analysis."""
import re
from pathlib import Path

NOISE = re.compile(r"(^|/)(tests?|docs?|examples?|\.github|\.devcontainer|scripts?|migrations?)(/|$)|(^|/)(test_|conftest)|\.(test|spec)\.|__init__\.py$")


TYPE_HINTS = [("ui", ("page", "component", "view", "layout", "template", "frontend", "client")),
              ("api", ("route", "api", "server", "handler", "controller", "app", "main", "cli")),
              ("data", ("model", "db", "database", "schema", "store", "repo", "orm")),
              ("config", ("config", "settings", "env")),
              ("service", ("service", "core", "engine", "worker", "task", "utils", "util"))]


def _guess_type(path: str, entry: bool) -> str:
    low = Path(path).stem.lower()
    for t, keys in TYPE_HINTS:
        if any(k in low for k in keys):
            return "entry" if entry and t == "api" else t
    return "entry" if entry else "module"


def _folder_graph(scan: dict) -> dict:
    nodes, ids = [], {}
    for g, size in sorted(scan["group_sizes"].items(), key=lambda kv: -kv[1])[:14]:
        if NOISE.search(g + "/"):
            continue
        nid = "g_" + re.sub(r"\W", "_", g)
        ids[g] = nid
        nodes.append({"id": nid, "label": g, "type": _guess_type(g, False), "description": f"{size} files",
                      "files": scan["groups"][g][:5]})
    edges = [{"from": ids[e["from"]], "to": ids[e["to"]], "label": f"{e['weight']} imports"}
             for e in scan["group_edges"] if e["from"] in ids and e["to"] in ids]
    return {"nodes": nodes, "edges": edges}


def fallback_graph(scan: dict, root: Path) -> dict:
    """No-LLM diagram: the most connected source modules, linked by real imports."""
    entries = set(scan["entry_points"])
    pairs = [(a, b) for a, b in set(scan["file_edges"]) if not NOISE.search(a) and not NOISE.search(b)]
    degree: dict[str, int] = {}
    for a, b in pairs:
        degree[a] = degree.get(a, 0) + 1
        degree[b] = degree.get(b, 0) + 1
    keep = set(sorted(degree, key=lambda f: (f not in entries, -degree[f]))[:14])
    nodes = [{"id": "m_" + re.sub(r"\W", "_", f), "label": Path(f).name, "type": _guess_type(f, f in entries),
              "description": f"{f} (connected to {degree[f]} modules)", "files": [f]}
             for f in sorted(keep, key=lambda f: -degree[f])]
    edges = [{"from": "m_" + re.sub(r"\W", "_", a), "to": "m_" + re.sub(r"\W", "_", b), "label": "imports"}
             for a, b in sorted(pairs) if a in keep and b in keep]
    graph = {"nodes": nodes, "edges": edges}
    if len(nodes) < 3 or len(edges) < 2:
        graph = _folder_graph(scan)
    langs = ", ".join(f"{k} ({v})" for k, v in list(scan["languages"].items())[:4]) or "unknown"
    graph["tech"] = scan["tech"]
    graph["summary"] = (f"Static analysis of {scan['file_count']} files; main languages: {langs}. "
                        "Arrows point from a module to the module it imports. "
                        "Set GEMINI_API_KEY (free) or ANTHROPIC_API_KEY in Backend/.env for an LLM-written architecture view.")
    return graph
