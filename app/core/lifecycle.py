"""Application lifecycle hooks (startup/shutdown).

FastAPI allows registering callables that run on application startup and
shutdown. We keep these hooks minimal and side‑effect free so they complete
quickly and make readiness/liveness probes happy.

Current responsibilities
------------------------
- on_startup: ensure Qdrant collections exist before the first request.
- on_shutdown: emit a clean shutdown log message (placeholder for future cleanup).

If you later add background tasks (e.g., periodic centroid rebuilds, metrics
exporters), this is a good place to initialize and tear them down cleanly.
"""
from __future__ import annotations

from app.core.logging import logger
from app.services.qdrant_repo import ensure_collections


async def on_startup() -> None:
    """Run once when the FastAPI app starts.

    We keep startup fast; the only operation is to ensure Qdrant collections
    are present with the expected schema. If Qdrant is unavailable, consider
    failing fast so the container restarts, or add retry/backoff here.
    """
    logger.info("startup: ensuring Qdrant collections")
    ensure_collections()


async def on_shutdown() -> None:
    """Run once when the FastAPI app is shutting down.

    Placeholder for future resource cleanup (timers, background tasks, etc.).
    """
    logger.info("shutdown")
