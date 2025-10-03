"""Admin endpoints.

Small maintenance API:
- POST /rebuild_centroids  -> recompute all user centroids
- GET  /health             -> simple liveness check
"""
from __future__ import annotations

from fastapi import APIRouter

from app.schemas.common import StatusOK

from app.services.centroid import rebuild_all_centroids

router = APIRouter()


@router.post("/rebuild_centroids")
def rebuild() -> dict:
    """Rebuild centroids for all users that have a master profile."""
    n = rebuild_all_centroids()
    return {"ok": True, "updated": int(n)}


@router.get("/health", response_model=StatusOK)
def health() -> dict:
    """Simple liveness probe."""
    return {"status": "ok"}
