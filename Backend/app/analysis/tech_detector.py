"""Detect technologies from dependency manifests (no LLM needed)."""
import json
import re
from pathlib import Path

from .file_utils import SKIP_DIRS, read_text

# package name -> (display name, side, category)
KNOWN = {
    # JS frontend
    "react": ("React", "frontend", "UI library"), "react-dom": ("React DOM", "frontend", "UI library"),
    "next": ("Next.js", "frontend", "Framework"), "vue": ("Vue", "frontend", "UI library"),
    "nuxt": ("Nuxt", "frontend", "Framework"), "@angular/core": ("Angular", "frontend", "Framework"),
    "svelte": ("Svelte", "frontend", "UI library"), "@sveltejs/kit": ("SvelteKit", "frontend", "Framework"),
    "vite": ("Vite", "frontend", "Build tool"), "webpack": ("Webpack", "frontend", "Build tool"),
    "react-scripts": ("Create React App", "frontend", "Build tool"),
    "tailwindcss": ("Tailwind CSS", "frontend", "Styling"), "bootstrap": ("Bootstrap", "frontend", "Styling"),
    "styled-components": ("styled-components", "frontend", "Styling"), "sass": ("Sass", "frontend", "Styling"),
    "@mui/material": ("Material UI", "frontend", "Component library"),
    "antd": ("Ant Design", "frontend", "Component library"),
    "@chakra-ui/react": ("Chakra UI", "frontend", "Component library"),
    "redux": ("Redux", "frontend", "State management"), "@reduxjs/toolkit": ("Redux Toolkit", "frontend", "State management"),
    "zustand": ("Zustand", "frontend", "State management"), "mobx": ("MobX", "frontend", "State management"),
    "react-router-dom": ("React Router", "frontend", "Routing"), "react-router": ("React Router", "frontend", "Routing"),
    "axios": ("Axios", "frontend", "HTTP client"), "swr": ("SWR", "frontend", "Data fetching"),
    "@tanstack/react-query": ("TanStack Query", "frontend", "Data fetching"),
    "react-hook-form": ("React Hook Form", "frontend", "Forms"), "formik": ("Formik", "frontend", "Forms"),
    "mermaid": ("Mermaid", "frontend", "Diagrams"), "d3": ("D3", "frontend", "Charts"),
    "chart.js": ("Chart.js", "frontend", "Charts"), "recharts": ("Recharts", "frontend", "Charts"),
    "jest": ("Jest", "frontend", "Testing"), "vitest": ("Vitest", "frontend", "Testing"),
    "cypress": ("Cypress", "frontend", "Testing"), "@playwright/test": ("Playwright", "frontend", "Testing"),
    "typescript": ("TypeScript", "frontend", "Language"),
    # JS backend
    "express": ("Express", "backend", "Web framework"), "fastify": ("Fastify", "backend", "Web framework"),
    "koa": ("Koa", "backend", "Web framework"), "@nestjs/core": ("NestJS", "backend", "Web framework"),
    "hapi": ("Hapi", "backend", "Web framework"), "socket.io": ("Socket.IO", "backend", "Realtime"),
    "mongoose": ("Mongoose (MongoDB)", "backend", "Database"), "mongodb": ("MongoDB", "backend", "Database"),
    "pg": ("PostgreSQL", "backend", "Database"), "mysql2": ("MySQL", "backend", "Database"),
    "mysql": ("MySQL", "backend", "Database"), "sqlite3": ("SQLite", "backend", "Database"),
    "redis": ("Redis", "backend", "Cache"), "ioredis": ("Redis", "backend", "Cache"),
    "prisma": ("Prisma", "backend", "ORM"), "@prisma/client": ("Prisma", "backend", "ORM"),
    "sequelize": ("Sequelize", "backend", "ORM"), "typeorm": ("TypeORM", "backend", "ORM"),
    "jsonwebtoken": ("JWT", "backend", "Auth"), "passport": ("Passport", "backend", "Auth"),
    "bcrypt": ("bcrypt", "backend", "Auth"), "bcryptjs": ("bcrypt", "backend", "Auth"),
    "cors": ("CORS", "backend", "Middleware"), "dotenv": ("dotenv", "backend", "Config"),
    "multer": ("Multer", "backend", "File upload"), "nodemailer": ("Nodemailer", "backend", "Email"),
    "bull": ("Bull", "backend", "Queue"), "bullmq": ("BullMQ", "backend", "Queue"),
    "openai": ("OpenAI SDK", "backend", "LLM"), "@anthropic-ai/sdk": ("Anthropic SDK", "backend", "LLM"),
    "langchain": ("LangChain", "backend", "LLM"), "graphql": ("GraphQL", "backend", "API"),
    "apollo-server": ("Apollo Server", "backend", "API"),
    # Python
    "fastapi": ("FastAPI", "backend", "Web framework"), "flask": ("Flask", "backend", "Web framework"),
    "django": ("Django", "backend", "Web framework"), "uvicorn": ("Uvicorn", "backend", "Server"),
    "gunicorn": ("Gunicorn", "backend", "Server"), "starlette": ("Starlette", "backend", "Web framework"),
    "sqlalchemy": ("SQLAlchemy", "backend", "ORM"), "alembic": ("Alembic", "backend", "Migrations"),
    "psycopg2": ("PostgreSQL", "backend", "Database"), "psycopg2-binary": ("PostgreSQL", "backend", "Database"),
    "psycopg": ("PostgreSQL", "backend", "Database"), "pymongo": ("MongoDB", "backend", "Database"),
    "pydantic": ("Pydantic", "backend", "Validation"), "celery": ("Celery", "backend", "Queue"),
    "requests": ("Requests", "backend", "HTTP client"), "httpx": ("HTTPX", "backend", "HTTP client"),
    "pandas": ("pandas", "backend", "Data"), "numpy": ("NumPy", "backend", "Data"),
    "scikit-learn": ("scikit-learn", "backend", "ML"), "torch": ("PyTorch", "backend", "ML"),
    "tensorflow": ("TensorFlow", "backend", "ML"), "anthropic": ("Anthropic SDK", "backend", "LLM"),
    "google-genai": ("Google Gemini SDK", "backend", "LLM"), "mcp": ("MCP SDK", "backend", "LLM tooling"),
    "langchain-core": ("LangChain", "backend", "LLM"), "chromadb": ("ChromaDB", "backend", "Vector DB"),
    "faiss-cpu": ("FAISS", "backend", "Vector DB"), "pytest": ("pytest", "backend", "Testing"),
    "python-dotenv": ("python-dotenv", "backend", "Config"), "python-multipart": ("python-multipart", "backend", "File upload"),
    "pyjwt": ("JWT", "backend", "Auth"),
    # other ecosystems
    "spring-boot": ("Spring Boot", "backend", "Web framework"), "gin-gonic/gin": ("Gin", "backend", "Web framework"),
    "laravel/framework": ("Laravel", "backend", "Web framework"), "rails": ("Ruby on Rails", "backend", "Web framework"),
}


FILE_HINTS = {  # file name -> (display, side, category)
    "Dockerfile": ("Docker", "other", "DevOps"), "docker-compose.yml": ("Docker Compose", "other", "DevOps"),
    "docker-compose.yaml": ("Docker Compose", "other", "DevOps"), "vercel.json": ("Vercel", "other", "Hosting"),
    "netlify.toml": ("Netlify", "other", "Hosting"), "Jenkinsfile": ("Jenkins", "other", "CI/CD"),
    "tsconfig.json": ("TypeScript", "frontend", "Language"), ".eslintrc.json": ("ESLint", "other", "Tooling"),
}


LANG_NAMES = {".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript (JSX)", ".ts": "TypeScript",
              ".tsx": "TypeScript (TSX)", ".java": "Java", ".go": "Go", ".rs": "Rust", ".rb": "Ruby",
              ".php": "PHP", ".cs": "C#", ".sql": "SQL", ".html": "HTML", ".css": "CSS"}


def _manifests(root: Path):
    for p in root.rglob("*"):
        rel = p.relative_to(root)
        if len(rel.parts) > 4 or any(x in SKIP_DIRS for x in rel.parts) or not p.is_file():
            continue
        yield p, str(rel)


def _py_names(text: str) -> list[str]:
    names = []
    for line in text.splitlines():
        line = line.split("#")[0].strip()
        if line and not line.startswith(("-", "git+", "http")):
            names.append(re.split(r"[<>=!~\[; ]", line)[0].lower().replace("_", "-"))
    return names


def detect_tech(root: Path) -> dict:
    found: dict[str, dict] = {}

    def add(name, side, category, source):
        found.setdefault(name, {"name": name, "category": category, "detail": f"found in {source}", "side": side})

    for p, rel in _manifests(root):
        base = p.name
        if base in FILE_HINTS:
            n, side, cat = FILE_HINTS[base]
            add(n, side, cat, rel)
        deps: list[str] = []
        if base == "package.json":
            try:
                d = json.loads(read_text(p))
                deps = list(d.get("dependencies", {})) + list(d.get("devDependencies", {}))
            except ValueError:
                continue
        elif re.fullmatch(r"requirements.*\.txt", base):
            deps = _py_names(read_text(p))
        elif base == "pyproject.toml":
            text = read_text(p)
            deps = _py_names("\n".join(re.findall(r'^\s*"([^"]+)"', text, re.M)))
        elif base in ("pom.xml", "build.gradle", "go.mod", "composer.json", "Gemfile"):
            low = read_text(p).lower()
            deps = [k for k in KNOWN if "/" in k or k in ("rails", "spring-boot")]
            deps = [k for k in deps if k.split("/")[-1] in low or k in low]
        for dep in deps:
            if dep.lower() in KNOWN:
                n, side, cat = KNOWN[dep.lower()]
                add(n, side, cat, rel)

    langs = {}
    for p, rel in _manifests(root):
        n = LANG_NAMES.get(p.suffix.lower())
        if n:
            langs[n] = langs.get(n, 0) + 1
    for n, _ in sorted(langs.items(), key=lambda kv: -kv[1])[:4]:
        side = "backend" if n in ("Python", "Java", "Go", "Rust", "Ruby", "PHP", "C#") else (
            "frontend" if n in ("HTML", "CSS", "JavaScript (JSX)", "TypeScript (TSX)") else "other")
        add(n, side, "Language", "source files")

    out = {"frontend": [], "backend": [], "other": []}
    for item in found.values():
        out[item.pop("side")].append(item)
    return out


def merge_tech(llm: dict | None, static: dict) -> dict:
    """LLM list first, then add anything static detection found that the LLM missed."""
    out = {k: list((llm or {}).get(k, [])) for k in ("frontend", "backend", "other")}
    seen = {i["name"].lower() for lst in out.values() for i in lst}
    for k in out:
        for item in static.get(k, []):
            if item["name"].lower() not in seen:
                out[k].append(item)
                seen.add(item["name"].lower())
    return out


def clean_tech(raw) -> dict:
    out = {"frontend": [], "backend": [], "other": []}
    if not isinstance(raw, dict):
        return out
    for k in out:
        for i in (raw.get(k) or [])[:25]:
            if isinstance(i, dict) and i.get("name"):
                out[k].append({"name": str(i["name"])[:40], "category": str(i.get("category", ""))[:30],
                               "detail": str(i.get("detail", ""))[:200]})
    return out
