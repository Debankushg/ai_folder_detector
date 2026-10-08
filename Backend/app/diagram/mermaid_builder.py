"""Turn graph JSON (nodes + edges) into Mermaid flowchart text."""


def to_mermaid(graph: dict) -> str:
    lines = ["flowchart TD"]
    for n in graph["nodes"]:
        label = n["label"].replace('"', "'")
        lines.append(f'  {n["id"]}["{label}"]:::{n["type"]}')
    for e in graph["edges"]:
        lbl = e["label"].replace('"', "'").replace("|", "/")
        lines.append(f'  {e["from"]} -->|"{lbl}"| {e["to"]}' if lbl else f'  {e["from"]} --> {e["to"]}')
    lines += [
        "  classDef entry fill:#fde68a,stroke:#b45309,color:#111",
        "  classDef ui fill:#bfdbfe,stroke:#1d4ed8,color:#111",
        "  classDef api fill:#bbf7d0,stroke:#15803d,color:#111",
        "  classDef service fill:#ddd6fe,stroke:#6d28d9,color:#111",
        "  classDef data fill:#fecaca,stroke:#b91c1c,color:#111",
        "  classDef external fill:#e5e7eb,stroke:#4b5563,color:#111",
        "  classDef config fill:#fef3c7,stroke:#a16207,color:#111",
        "  classDef module fill:#f1f5f9,stroke:#475569,color:#111",
    ]
    return "\n".join(lines)
