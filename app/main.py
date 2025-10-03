from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response

from app.api import router as api_router
from app.core.lifecycle import on_startup, on_shutdown

# FastAPI app instance
APP = FastAPI(title="speaker-id")


# ----- Lifecycle hooks -----
@APP.on_event("startup")
async def _startup() -> None:
    await on_startup()


@APP.on_event("shutdown")
async def _shutdown() -> None:
    await on_shutdown()


# ----- Static web UI -----
WEB_DIR = Path(__file__).parent / "web"
if WEB_DIR.exists():
    APP.mount("/assets", StaticFiles(directory=str(WEB_DIR)), name="assets")


@APP.get("/", response_class=HTMLResponse)
def index() -> Response:
    index_path = WEB_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("<h1>speaker-id</h1><p>Web UI not found.</p>")


# ----- Health endpoints -----
@APP.get("/health")
def root_health() -> dict:
    """Root liveness endpoint (outside /api)."""
    return {"status": "ok"}


# ----- API router under /api -----
APP.include_router(api_router, prefix="/api")
