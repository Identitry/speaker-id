"""Identification endpoints for the speaker-id API.

This router exposes the primary public-facing endpoints:

- POST /identify
    Accepts an uploaded audio file, embeds it into a vector, searches Qdrant's
    `speakers_master` collection, and returns the predicted speaker (or
    "unknown" if below threshold).

- GET /profiles
    Returns the list of currently enrolled speaker names (from master profiles).

Notes
-----
Authentication/authorization is skipped here for simplicity. In a production
deployment, you should protect these routes via API keys, OAuth, or ingress-
level policies depending on your environment.
"""
from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, Query, HTTPException
from app.schemas.identify import IdentifyResult

from app.core.config import settings
from app.utils.audio import load_wav_normalized_from_bytes
from app.embeddings import get_encoder
from app.services.identify import identify_best

router = APIRouter(prefix="/api", tags=["Identify"])


@router.post("/identify", response_model=IdentifyResult)
async def identify(
    file: UploadFile = File(...),
    threshold: float | None = Query(None, description="Override confidence threshold [0..1]"),
    topk: int | None = Query(None, description="Override number of nearest neighbors to consider"),
):
    """Identify the most likely speaker given an uploaded audio clip.

    Parameters
    ----------
    file : UploadFile
        Audio file (typically WAV or MP3). The embedding service handles
        decoding and feature extraction.
    threshold : Optional[float]
        If provided, overrides the default decision threshold (otherwise taken
        from settings.default_threshold).
    topk : Optional[int]
        If provided, overrides the number of neighbors to fetch from Qdrant
        (otherwise taken from settings.topk).

    Returns
    -------
    dict
        JSON payload with keys:
          - speaker: str, predicted name or "unknown"
          - confidence: float, normalized similarity score
          - topN: list of {name, score} entries for debugging/telemetry
    """
    # Read the raw bytes of the uploaded file into memory
    data = await file.read()

    # Convert audio to embedding vector using runtime normalization settings
    wav = load_wav_normalized_from_bytes(data)
    vec = get_encoder().embed_vector(wav)

    # Apply default values if query params are missing
    th = threshold if threshold is not None else settings.default_threshold
    k = topk if topk is not None else settings.topk

    # Perform search in Qdrant
    res = identify_best(vec, topk=k, threshold=th)
    if res is None:
        # No profiles enrolled yet -> cannot identify anyone
        raise HTTPException(400, "No profiles enrolled")

    return res


@router.get("/profiles")
async def list_profiles():
    """Return the list of enrolled speaker names (from MASTER collection)."""
    from app.services.qdrant_repo import list_master_profiles

    return {"profiles": list_master_profiles()}
