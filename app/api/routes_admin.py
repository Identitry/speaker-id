"""Admin endpoints.

Small maintenance API:
- POST /rebuild_centroids  -> recompute all user centroids
- GET  /health             -> simple liveness check
- GET  /config             -> system configuration
"""
from __future__ import annotations

from fastapi import APIRouter

from app.schemas.common import StatusOK
from app.core.config import settings
from app.services.centroid import rebuild_all_centroids
from app.services.embeddings import get_embedding_dim

router = APIRouter()


@router.post("/rebuild_centroids")
def rebuild() -> dict:
    """Rebuild centroids for all users that have a master profile."""
    n = rebuild_all_centroids()
    return {"status": "rebuilt", "speakers_updated": int(n), "message": f"Successfully rebuilt centroids for {int(n)} speakers"}


@router.get("/health", response_model=StatusOK)
def health() -> dict:
    """Simple liveness probe."""
    return {"status": "ok"}


@router.get("/config")
def get_config() -> dict:
    """Get system configuration."""
    use_ecapa = getattr(settings, "USE_ECAPA", getattr(settings, "use_ecapa", False))

    return {
        "model": "ECAPA-TDNN" if use_ecapa else "Resemblyzer",
        "embedding_dim": get_embedding_dim(),
        "sample_rate": getattr(settings, "SAMPLE_RATE", getattr(settings, "sample_rate", 16000)),
        "default_threshold": getattr(settings, "DEFAULT_THRESHOLD", getattr(settings, "default_threshold", 0.82)),
        "version": "1.0.0"
    }
