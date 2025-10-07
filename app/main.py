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
# Only expose metrics if enabled via settings
if settings.metrics_enabled:
    # Instrumentation is idempotent; in tests, multiple app lifecycles won't double-register.
    instrumentator = Instrumentator(
        should_respect_env_var=True,  # set PROMETHEUS_MULTIPROC or PROMETHEUS_DISABLED to control behavior
        excluded_handlers={"/health", "/", "/assets", settings.metrics_path},
        should_group_status_codes=True,
        should_ignore_untemplated=True,
    )

    # Add a few common metrics (request duration, size, etc.)
    instrumentator \
        .add(metrics.default()) \
        .add(metrics.latency()) \
        .add(metrics.requests()) \
        .add(metrics.response_size()) \
        .add(metrics.request_size()) \
        .instrument(APP) \
        .expose(APP, endpoint=settings.metrics_path, include_in_schema=False)

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
