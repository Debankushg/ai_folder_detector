# FlowMap
Upload a project (.zip) or paste a GitHub link → get a block diagram of how it flows.

- **Backend/** FastAPI. Ingest → static scan (imports graph) → RAG (TF-IDF over code chunks) →
  an LLM (Gemini or Claude) explores the code through an **MCP server** (`list_files`, `read_file`, `search_code`)
  → diagram JSON → Mermaid. Without an API key it falls back to an import-based diagram.
- **Frontend/** Next.js, renders the Mermaid diagram.

## Run
```bash
# Backend
cd Backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env     # set LLM_PROVIDER and GEMINI_API_KEY (free) or ANTHROPIC_API_KEY
.venv/bin/python run.py  # http://localhost:8000

# Frontend
cd Frontend && npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL -> backend URL
npm run dev              # http://localhost:3000
```
Link between the two: Frontend `NEXT_PUBLIC_API_URL` ↔ Backend `CORS_ORIGINS`.

## Technology used

### Frontend (`Frontend/`)
| Area | Technology |
|---|---|
| Framework | Next.js 15 (App Router) |
| UI library | React 19 |
| Language | TypeScript 5 |
| Diagram rendering | Mermaid 11 (flowchart rendered as SVG in the browser) |
| Styling | Plain CSS (`globals.css`), dark theme |
| Data fetching | Browser `fetch` and `FormData` (zip upload) |
| Config | `.env.local` → `NEXT_PUBLIC_API_URL` |
| Tooling | npm, Node.js 22 |

### Backend (`Backend/`)
| Area | Technology |
|---|---|
| Language | Python 3.14 |
| Web framework | FastAPI + Uvicorn |
| File upload | python-multipart |
| Config | python-dotenv (`.env`), CORS middleware |
| Project intake | `zipfile` (zip-slip guard), `git clone --depth 1` for GitHub links |
| Code analysis | Python `ast` + regex for JS/TS imports → module import graph |
| RAG | scikit-learn (TF-IDF + cosine similarity) over code chunks, fully local |
| MCP | Official `mcp` Python SDK (v1.x): stdio MCP server with `list_files`, `read_file`, `search_code`; backend is the MCP client |
| LLM | Google Gemini (`google-genai`, default `gemini-3.8-flash`) or Anthropic Claude (`anthropic`, default `claude-sonnet-5-5`), selected by `LLM_PROVIDER` |
| LLM method | Tool-calling loop over MCP tools → JSON nodes/edges → Mermaid |
| Fallback | Static import-graph diagram when no key is set or the LLM call fails |
| Tooling | pip, venv |

## Tech detection
The result page lists the technologies the analysed project uses, split into **Frontend**, **Backend** and **Other**. `Backend/app/analysis/tech_detector.py` detects them from `package.json`, `requirements.txt`, `pyproject.toml`, Dockerfiles etc.; the LLM then verifies and extends the list by reading the code.

## Backend folder structure

```
Backend/
├── run.py                      # starts the server (uvicorn)
├── requirements.txt
├── .env / .env.example         # API keys, provider, CORS
└── app/
    ├── main.py                 # creates the FastAPI app, CORS, mounts routes
    ├── config.py               # loads .env, shared settings
    ├── api/
    │   ├── routes.py           # /api/health, /api/analyze/github, /api/analyze/upload
    │   └── schemas.py          # request models
    ├── ingestion/              # get the project onto disk
    │   ├── github_loader.py    # safe shallow git clone
    │   ├── zip_loader.py       # safe unzip (zip-slip + size guards)
    │   └── workspace.py        # temp folders
    ├── analysis/               # understand the project without an LLM
    │   ├── file_utils.py       # walk/read files, skip node_modules etc.
    │   ├── code_scanner.py     # languages, entry points, import graph
    │   └── tech_detector.py    # technologies from package.json, requirements.txt...
    ├── rag/
    │   └── code_index.py       # TF-IDF code search (the RAG part)
    ├── mcp_tools/
    │   ├── mcp_server.py       # MCP tools: list_files, read_file, search_code
    │   └── mcp_client.py       # starts the MCP server, forwards LLM tool calls
    ├── llm/
    │   ├── llm_service.py      # picks provider, runs the flow, falls back on error
    │   ├── prompts.py          # system prompt + RAG-seeded first message
    │   ├── gemini_provider.py  # Gemini tool-calling loop (+ overload retry)
    │   ├── anthropic_provider.py  # Claude tool-calling loop
    │   └── response_parser.py  # extract JSON from the LLM reply
    └── diagram/
        ├── graph_cleaner.py    # validate/sanitise nodes, edges, tech
        ├── fallback_graph.py   # no-LLM diagram from imports
        └── mermaid_builder.py  # graph -> Mermaid text
```

## How a request flows (backend)

Think of it as a restaurant:

| File | Role | What it does |
|---|---|---|
| `api/routes.py` (+ `main.py`) | Reception desk | Receives the request, returns the final JSON answer |
| `ingestion/*` | Delivery person | Clones the GitHub repo / unzips the upload (safe-URL and zip-slip checks) |
| `analysis/code_scanner.py` | Inspector | Lists files, counts languages, finds which file imports which |
| `analysis/tech_detector.py` | Label reader | Detects technologies from `package.json`, `requirements.txt`, etc. |
| `rag/code_index.py` | Search index | TF-IDF search that finds the most relevant code chunks |
| `mcp_tools/mcp_server.py` | Library assistant | MCP tools for the AI: `list_files`, `read_file`, `search_code` |
| `mcp_tools/mcp_client.py` | Phone line | Starts the MCP server and relays the AI's tool calls |
| `llm/*` | Head chef | Asks Gemini/Claude to design the diagram and cleans the answer |
| `diagram/*` | Plating | Validates the result, builds the fallback, produces Mermaid text |

```
 YOU (browser, page.tsx)
   paste GitHub link or upload .zip
          |
          v
+------------------------------------------------------+
| 1. api/routes.py   "Reception"                       |
|    receives the request (/api/analyze/github|upload) |
+------------------------------------------------------+
          | "get me the project files"
          v
+------------------------------------------------------+
| 2. ingestion/   "Delivery"                           |
|    clones the GitHub repo / unzips the upload        |
|    (checks the link is safe, blocks bad zips)        |
+------------------------------------------------------+
          | project folder is now on disk
          v
+------------------------------------------------------+
| 3. analysis/code_scanner.py   "Inspector"            |
|    lists files, counts languages, finds who imports  |
|    whom --> tech_detector.py "what tech is used?"    |
+------------------------------------------------------+
          | report: files, imports, technologies
          v
+------------------------------------------------------+
| 4. llm/llm_service.py   "Head chef"                  |
|    Is there an API key?                              |
+------------------------------------------------------+
      | NO key / AI fails            | YES key
      v                              v
+-------------------+   +----------------------------------------+
| diagram/          |   | 5. rag/code_index.py: finds the most   |
| fallback_graph:   |   |    relevant code -> added to the       |
| draw diagram from |   |    question (llm/prompts.py)           |
| the import report |   +----------------------------------------+
| only              |   | 6. mcp_client.py starts mcp_server.py  |
+-------------------+   |    tools: list_files / read_file /     |
      |                 |    search_code                         |
      |                 +----------------------------------------+
      |                 | 7. AI loop (gemini_/anthropic_provider)|
      |                 |    AI asks "open this file" ->         |
      |                 |    mcp_server answers -> repeat ->     |
      |                 |    AI returns boxes, arrows, tech list |
      |                 +----------------------------------------+
      |                 | 8. graph_cleaner.py tidies the answer; |
      |                 |    merged with tech_detector findings  |
      |                 +----------------------------------------+
      +------------+-----------------+
                   v
+------------------------------------------------------+
| 9. diagram/mermaid_builder.py                        |
|    turns boxes and arrows into diagram text          |
+------------------------------------------------------+
                   v
+------------------------------------------------------+
| 10. api/routes.py   "Reception again"                |
|     packs summary + tech + blocks + diagram text     |
|     into one JSON answer and deletes the temp files  |
+------------------------------------------------------+
                   v
 YOU: page.tsx shows the tech lists,
      Diagram.tsx (Mermaid) draws the block diagram
```

### Step by step, in plain words
1. You paste a link or upload a zip, and **routes.py** receives it.
2. **ingestion/** downloads or unzips the project into a temporary folder.
3. **code_scanner.py** takes an inventory: files, languages, and which file uses which. It calls **tech_detector.py** to read the dependency lists.
4. **llm_service.py** checks whether an AI key exists.
   - **No key:** it draws a simple diagram straight from the inventory (`fallback_graph.py`).
   - **Key found:** it asks the AI for the real architecture (steps 5-8).
5. **code_index.py** picks the code pieces most relevant to "how does this app work" and **prompts.py** attaches them to the question.
6. **mcp_client.py** starts **mcp_server.py** so the AI can browse the project.
7. The AI opens the files it needs a few times, then answers with the blocks, arrows and tech list.
8. **graph_cleaner.py** cleans the answer and any technology **tech_detector.py** found that the AI missed is added.
9. **mermaid_builder.py** turns the blocks and arrows into Mermaid text, the language the diagram is drawn in.
10. **routes.py** packs everything into one reply and deletes the temporary folder. The browser draws the diagram and shows the tech lists.

If the AI fails at any point (e.g. a 503 or a bad key), the app does not crash: it shows a yellow warning and returns the simple import-based diagram instead.

### MCP tools
| Tool | Inputs | What it does |
|---|---|---|
| `list_files` | `subdir` | Lists files/folders one level deep (skips `node_modules`, `.git`...) |
| `read_file` | `path`, `max_chars` | Returns the start of a source file |
| `search_code` | `query`, `k` | RAG search: most relevant code chunks with file, line and score |

All tools are read-only and reject paths that leave the project folder.
