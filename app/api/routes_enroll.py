"""Enrollment endpoints for the speaker-id API.

This router handles adding and removing speaker profiles:

- POST /enroll
    Accepts an uploaded audio clip for a given user name, embeds it,
    stores the raw clip in Qdrant (`speakers_raw`), and updates/rebuilds
    the corresponding master centroid in `speakers_master`.

- POST /reset
    Deletes either all data or only the data for a specific user.

Notes
-----
Authentication/authorization is not implemented here for simplicity.
In production, secure these endpoints appropriately (e.g., API key, OAuth).
"""
from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, Query

from app.utils.audio import load_wav_normalized_from_bytes
from app.embeddings import get_encoder

from app.services.qdrant_repo import upsert_raw_and_update_master
from app.schemas.common import EnrollResponse, Message
router = APIRouter(prefix="/api", tags=["Enroll"])


@router.post("/enroll", response_model=EnrollResponse)
async def enroll(
    name: str = Query(..., description="Logical speaker name to associate with the clip"),
    file: UploadFile = File(..., description="Audio file containing the speaker's voice sample"),
):
    """Enroll a new clip for a given user name.

    Behavior
    --------
    - Reads the uploaded file into memory
    - Embeds it into a vector using the embedding backend
    - Stores the vector in the `speakers_raw` collection
    - Updates the per-user centroid in the `speakers_master` collection

    Parameters
    ----------
    name : str
        User name or identifier for the speaker being enrolled.
    file : UploadFile
        Audio clip (WAV/MP3/etc.).

    Returns
    -------
    dict
        { "ok": true, "name": <user name> }
    """
    data = await file.read()
    # Normalize channels/sample rate according to runtime settings
    wav = load_wav_normalized_from_bytes(data)
    # Embed with selected backend (ECAPA when USE_ECAPA=true, else Resemblyzer)
    vec = get_encoder().embed_vector(wav)
    upsert_raw_and_update_master(name=name, vec=vec)
    return {"ok": True, "name": name}


@router.post("/reset", response_model=Message)
async def reset(
    name: str | None = Query(None, description="If set, delete only this user's data"),
    all: bool = Query(False, description="If true, drop and recreate both collections"),
):
    """Reset enrolled profiles.

    Behavior
    --------
    - If `all=True`, drops both collections and recreates them
    - If `name` is given, deletes only that user's raw + master data
    - If neither is set, no action is taken

    Parameters
    ----------
    name : Optional[str]
        User name to reset (if any).
    all : bool
        Whether to drop all data.

    Returns
    -------
    dict
        { "ok": true }
    """
    from app.services.qdrant_repo import reset_profiles

    reset_profiles(name=name, drop_all=all)
    return {"ok": True}
