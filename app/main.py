from __future__ import annotations

from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response

# Prometheus FastAPI instrumentation
from prometheus_fastapi_instrumentator import Instrumentator, metrics

from app.api import router as api_router
from app.core.lifecycle import on_startup, on_shutdown
from app.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    await on_startup()
    try:
        yield
    finally:
        await on_shutdown()

# FastAPI app instance
APP = FastAPI(title="speaker-id", lifespan=lifespan)


# ----- Prometheus metrics -----
# Setup metrics instrumentation (always enabled, can be disabled via PROMETHEUS_DISABLED env var)
instrumentator = Instrumentator(
    should_respect_env_var=True,  # respect PROMETHEUS_DISABLED env var
    excluded_handlers=["/health", "/", "/assets", "/metrics"],  # Don't instrument these endpoints
    should_group_status_codes=True,
    should_ignore_untemplated=True,
)

# Add standard prometheus-fastapi-instrumentator metrics
instrumentator \
    .add(metrics.default()) \
    .add(metrics.latency()) \
    .add(metrics.requests()) \
    .add(metrics.response_size()) \
    .add(metrics.request_size()) \
    .instrument(APP)

# Manually add /metrics endpoint using prometheus_client
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

@APP.get("/metrics", include_in_schema=False)
def metrics_endpoint():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

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
@APP.get("/health", tags=["health"])
def root_health() -> dict:
    """Root liveness endpoint (outside /api)."""
    return {"status": "ok"}


# ----- API router under /api -----
APP.include_router(api_router, prefix="/api")
