"""Identify the best-matching speaker from the MASTER collection.

This module contains the read-path used by the `/identify` endpoint.
It queries Qdrant's `speakers_master` collection (one centroid per user)
with a query vector and returns the most likely speaker together with a
confidence score.

Scoring notes
-------------
We treat Qdrant's returned `score` as a similarity in [0..1] where **higher is
better** for cosine. If your cluster/client returns distance instead, switch
`max` to `min` in the selection below and/or normalize accordingly.

Thresholding
------------
`threshold` is applied to the best candidate's score to decide whether we
accept the prediction as a named speaker or fall back to "unknown".
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.core.config import settings  # imported for consistency (not used here)
from app.services.qdrant_repo import _client, MASTER


def identify_best(vec, topk: int, threshold: float) -> Optional[Dict[str, Any]]:
    """Search Qdrant for the nearest master profile and return a summary dict.

    Parameters
    ----------
    vec : numpy.ndarray or list[float]
        Query embedding representing the voice snippet to identify.
    topk : int
        Number of nearest neighbors to fetch from Qdrant (used for `topN`).
    threshold : float
        Acceptance threshold in [0..1] applied to the normalized score. If the
        best score is below `threshold`, the function returns `speaker="unknown"`.

    Returns
    -------
    dict | None
        A dictionary with keys `speaker`, `confidence`, and `topN` when search
        succeeds; `None` if there are no points in the collection.
    """
    # Execute a vector search against the MASTER collection. We request payloads
    # to read the user names for each point.
    # NOTE: Qdrant usually expects a Python list for vectors, hence `tolist()`.
    res = _client.search(
        collection_name=MASTER,
        query_vector=(vec.tolist() if hasattr(vec, "tolist") else vec),
        limit=topk,
        with_payload=True,
    )

    if not res:
        # No profiles indexed yet.
        return None

    # For COSINE similarity, a larger `r.score` is better.
    best = max(res, key=lambda r: r.score)
    score = float(best.score)

    # Extract user name; default to "unknown" if missing in payload.
    name = best.payload.get("name", "unknown")

    # Apply threshold to decide whether we trust the match.
    speaker = name if score >= threshold else "unknown"

    # Prepare a small leaderboard of the top-k results for debugging/telemetry.
    topN: List[Dict[str, float]] = [
        {"name": r.payload.get("name", "?"), "score": float(r.score)} for r in res
    ]

    return {"speaker": speaker, "confidence": score, "topN": topN}
