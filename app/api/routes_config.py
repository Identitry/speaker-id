"""Runtime configuration endpoints for the speaker-id API.

These endpoints expose minimal configuration knobs that can be adjusted
at runtime without redeploying:

- GET /config
    Return current runtime settings (threshold, top-k, use_ecapa flag).

- POST /config
    Update the decision threshold. This modifies the in‑process settings
    object only; it is not persisted. After a restart the default value
    from environment/config will be restored.

Notes
-----
For a production deployment you might want to back these changes with a
persistent store (file, database, secret manager) or restrict access to
authorized users only.
"""
from fastapi import APIRouter, Query

from app.core.config import settings

router = APIRouter()


@router.get("/config")
def get_cfg():
    """Return current runtime configuration values.

    Returns
    -------
    dict
        Keys:
          - threshold: float, current acceptance threshold [0..1]
          - topk: int, number of nearest neighbors considered in identification
          - use_ecapa: bool, whether ECAPA model is used instead of Resemblyzer
    """
    return {
        "threshold": settings.default_threshold,
        "topk": settings.topk,
        "use_ecapa": settings.use_ecapa,
    }


@router.post("/config")
def set_cfg(threshold: float = Query(..., description="New threshold [0..1]")):
    """Update the runtime decision threshold.

    Parameters
    ----------
    threshold : float
        New threshold in [0..1]. Values outside are clipped to this range.

    Returns
    -------
    dict
        { "ok": true, "threshold": <clamped value> }
    """
    # Clamp to valid [0..1] range
    settings.default_threshold = max(0.0, min(1.0, threshold))
    return {"ok": True, "threshold": settings.default_threshold}
