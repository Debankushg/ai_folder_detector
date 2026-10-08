"""HTTP endpoints."""
import shutil
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..analysis.code_scanner import scan
from ..diagram.mermaid_builder import to_mermaid
from ..ingestion.github_loader import clone_github
from ..ingestion.workspace import new_workdir
from ..ingestion.zip_loader import MAX_UPLOAD_BYTES, extract_zip
from ..llm.llm_service import build_graph, select_provider
from .schemas import GithubRequest

router = APIRouter(prefix="/api")


async def _analyze(root: Path, name: str) -> dict:
    s = scan(root)
    if s["file_count"] == 0:
        raise HTTPException(400, "No readable source files found.")
    graph, mode, warning = await build_graph(root, s)
    return {"name": name, "mode": mode, "warning": warning, "summary": graph["summary"],
            "tech": graph["tech"], "nodes": graph["nodes"], "edges": graph["edges"],
            "mermaid": to_mermaid(graph),
            "stats": {"files": s["file_count"], "languages": s["languages"],
                      "entry_points": s["entry_points"]}}


@router.get("/health")
def health():
    return {"ok": True, "llm": select_provider()}


@router.post("/analyze/github")
async def analyze_github(req: GithubRequest):
    work = new_workdir()
    try:
        root = clone_github(req.url, work)
        return await _analyze(root, req.url.rstrip("/").split("/")[-1])
    except ValueError as e:
        raise HTTPException(400, str(e))
    finally:
        shutil.rmtree(work, ignore_errors=True)


@router.post("/analyze/upload")
async def analyze_upload(file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(400, "Please upload the project folder as a .zip file.")
    work = new_workdir()
    try:
        zpath = work / "upload.zip"
        size = 0
        with zpath.open("wb") as f:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "Upload too large (max 100 MB).")
                f.write(chunk)
        dest = work / "src"
        dest.mkdir()
        root = extract_zip(zpath, dest)
        return await _analyze(root, Path(file.filename).stem)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        if type(e).__name__ == "BadZipFile":
            raise HTTPException(400, "Invalid zip file.")
        raise
    finally:
        shutil.rmtree(work, ignore_errors=True)
