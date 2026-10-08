"""Validate and sanitise the graph JSON returned by the LLM."""
import re

from ..analysis.tech_detector import clean_tech

NODE_TYPES = ["entry", "ui", "api", "service", "data", "external", "config", "module"]


def clean_graph(d: dict) -> dict:
    ids, nodes = set(), []
    for n in d.get("nodes", [])[:30]:
        nid = re.sub(r"\W", "_", str(n.get("id", ""))) or f"n{len(nodes)}"
        if nid in ids:
            continue
        ids.add(nid)
        t = n.get("type") if n.get("type") in NODE_TYPES else "module"
        nodes.append({"id": nid, "label": str(n.get("label", nid))[:40], "type": t,
                      "description": str(n.get("description", ""))[:300],
                      "files": [str(f) for f in n.get("files", [])][:6]})
    edges = []
    for e in d.get("edges", [])[:60]:
        a, b = re.sub(r"\W", "_", str(e.get("from", ""))), re.sub(r"\W", "_", str(e.get("to", "")))
        if a in ids and b in ids and a != b:
            edges.append({"from": a, "to": b, "label": str(e.get("label", ""))[:30]})
    if not nodes:
        raise ValueError("Empty diagram")
    return {"summary": str(d.get("summary", ""))[:800], "nodes": nodes, "edges": edges,
            "tech": clean_tech(d.get("tech"))}
