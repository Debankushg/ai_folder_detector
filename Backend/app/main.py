"""FlowMap API entry point: creates the app, enables CORS, mounts the routes."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .config import cors_origins

app = FastAPI(title="FlowMap API")
app.add_middleware(CORSMiddleware, allow_origins=cors_origins(), allow_methods=["*"], allow_headers=["*"])
app.include_router(router)
