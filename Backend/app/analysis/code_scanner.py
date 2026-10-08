"""Static scan: file tree, languages, internal import graph, entry points."""
import ast
import re
from collections import Counter, defaultdict
from pathlib import Path

from .file_utils import iter_files, read_text
from .tech_detector import detect_tech

CODE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}


ENTRY_NAMES = {"main.py", "app.py", "manage.py", "wsgi.py", "asgi.py", "server.py", "index.js",
               "index.ts", "server.js", "server.ts", "main.ts", "main.js", "page.tsx",
               "layout.tsx", "Dockerfile", "docker-compose.yml", "package.json",
               "pyproject.toml", "requirements.txt"}


JS_IMPORT = re.compile(r"""(?:import\s[^'"]*?from\s*|import\s*|require\(\s*|import\(\s*)['"]([^'"]+)['"]""")


def _py_imports(rel: str, src: str):
    out = []
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return out
    pkg = rel.split("/")[:-1]
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out += [("abs", a.name) for a in n.names]
        elif isinstance(n, ast.ImportFrom):
            if n.level:
                base = pkg[: len(pkg) - (n.level - 1)] if n.level > 1 else pkg
                mod = ".".join(base + ([n.module] if n.module else []))
                out.append(("abs", mod))
                out += [("abs", f"{mod}.{a.name}") for a in n.names]
            elif n.module:
                out.append(("abs", n.module))
                out += [("abs", f"{n.module}.{a.name}") for a in n.names]
    return out


def _resolve_py(mod: str, modmap: dict[str, str]):
    parts = mod.split(".")
    while parts:
        key = ".".join(parts)
        if key in modmap:
            return modmap[key]
        parts.pop()
    return None


def _resolve_js(rel: str, spec: str, files: set[str]):
    if spec.startswith("."):
        base = Path(rel).parent / spec
        bases = [str(Path(*[p for p in base.parts if p != "."]))]
        norm = []
        for b in bases:
            stack = []
            for part in b.split("/"):
                if part == "..":
                    if stack:
                        stack.pop()
                elif part:
                    stack.append(part)
            norm.append("/".join(stack))
        bases = norm
    elif spec.startswith(("@/", "~/")):
        bases = [spec[2:], "src/" + spec[2:]]
    else:
        return None
    for b in bases:
        for suf in ("", ".ts", ".tsx", ".js", ".jsx", ".mjs", "/index.ts", "/index.tsx", "/index.js"):
            if b + suf in files:
                return b + suf
    return None


def _group_of(rel: str, depth: int) -> str:
    parts = rel.split("/")
    if len(parts) == 1:
        return "(root)"
    return "/".join(parts[:min(depth, len(parts) - 1)])


def scan(root: Path) -> dict:
    files = {str(p.relative_to(root)): p for p in iter_files(root)}
    fileset = set(files)
    langs = Counter(Path(f).suffix.lower() for f in files if Path(f).suffix.lower() in CODE_EXT)

    modmap = {}
    for f in files:
        if f.endswith(".py"):
            m = f[:-3].replace("/", ".")
            if m.endswith(".__init__"):
                m = m[: -len(".__init__")]
            modmap[m] = f
            # allow imports relative to a source root like backend/app -> app.x
            parts = m.split(".")
            for i in range(1, len(parts)):
                modmap.setdefault(".".join(parts[i:]), f)

    depth = 1  # go deeper until the diagram has enough blocks
    while depth < 3 and len({_group_of(f, depth) for f in files}) < 4:
        depth += 1

    edges: dict[tuple[str, str], int] = defaultdict(int)
    file_edges = []
    for rel, p in files.items():
        ext = p.suffix.lower()
        if ext not in CODE_EXT:
            continue
        src = read_text(p)
        targets = set()
        if ext == ".py":
            for _, m in _py_imports(rel, src):
                t = _resolve_py(m, modmap)
                if t and t != rel:
                    targets.add(t)
        else:
            for spec in JS_IMPORT.findall(src):
                t = _resolve_js(rel, spec, fileset)
                if t and t != rel:
                    targets.add(t)
        for t in targets:
            file_edges.append((rel, t))
            a, b = _group_of(rel, depth), _group_of(t, depth)
            if a != b:
                edges[(a, b)] += 1

    groups: dict[str, list[str]] = defaultdict(list)
    for f in files:
        groups[_group_of(f, depth)].append(f)

    entries = [f for f in files if Path(f).name in ENTRY_NAMES]
    return {
        "tech": detect_tech(root),
        "file_count": len(files),
        "languages": {k.lstrip("."): v for k, v in langs.most_common()},
        "entry_points": entries[:25],
        "groups": {g: fs[:40] for g, fs in groups.items()},
        "group_sizes": {g: len(fs) for g, fs in groups.items()},
        "group_edges": [{"from": a, "to": b, "weight": w} for (a, b), w in sorted(edges.items())],
        "file_edges": file_edges,
    }
