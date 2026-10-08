"""Central settings: loads Backend/.env once and exposes values used across the app."""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

MAX_LLM_TURNS = 12  # max tool-calling rounds between the LLM and the MCP server


def cors_origins() -> list[str]:
    return [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")]
