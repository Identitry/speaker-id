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

Score Calibration
-----------------
Cosine similarity scores can sometimes be compressed (all scores clustering in
a narrow range). We apply optional score calibration to better spread the scores
and improve discrimination between correct and incorrect matches.

Thresholding
------------
`threshold` is applied to the best candidate's score to decide whether we
accept the prediction as a named speaker or fall back to "unknown".
"""
from __future__ import annotations

import numpy as np
from typing import Any, Dict, List, Optional

from app.core.config import settings  # imported for consistency (not used here)
from app.services.qdrant_repo import _client, MASTER


def calibrate_score(raw_score: float, scores_list: List[float]) -> float:
    """Calibrate/normalize score to improve discrimination.

    Uses score spreading technique: if all scores are clustered in a narrow range,
    we expand the differences to make the best match stand out more.

    Parameters
    ----------
    raw_score : float
        The raw similarity score to calibrate
    scores_list : List[float]
        All candidate scores for context

    Returns
    -------
    float
        Calibrated score (clipped to [0, 1])
    """
    if len(scores_list) < 2:
        return raw_score

    scores_array = np.array(scores_list)

    # Calculate score statistics
    mean_score = scores_array.mean()
    std_score = scores_array.std()

    # If scores are very compressed (low std), apply stronger calibration
    if std_score < 0.05:
        # Apply sigmoid-based score spreading
        # This pushes high scores higher and low scores lower
        z_score = (raw_score - mean_score) / (std_score + 1e-6)
        calibrated = 1 / (1 + np.exp(-2 * z_score))  # Sigmoid with scaling

        # Blend with original score (80% calibrated, 20% original)
        return float(np.clip(0.8 * calibrated + 0.2 * raw_score, 0, 1))

    # If scores already well-spread, apply mild normalization
    # This ensures the best score is emphasized
    score_range = scores_array.max() - scores_array.min()
    if score_range > 0:
        normalized = (raw_score - scores_array.min()) / score_range
        # Blend normalized with original (50/50)
        return float(np.clip(0.5 * normalized + 0.5 * raw_score, 0, 1))

    return raw_score


def identify_best(vec, topk: int, threshold: float, use_calibration: bool = None) -> Optional[Dict[str, Any]]:
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
    use_calibration : bool, optional
        If True, apply score calibration. If None, uses settings.score_calibration

    Returns
    -------
    dict | None
        A dictionary with keys `speaker`, `confidence`, and `topN` when search
        succeeds; `None` if there are no points in the collection.
    """
    if use_calibration is None:
        use_calibration = settings.score_calibration

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

    # Extract all raw scores
    raw_scores = [float(r.score) for r in res]

    # For COSINE similarity, a larger `r.score` is better.
    best = max(res, key=lambda r: r.score)
    raw_score = float(best.score)

    # Apply score calibration if enabled
    # This helps when scores are compressed in a narrow range
    if use_calibration:
        final_score = calibrate_score(raw_score, raw_scores)
    else:
        final_score = raw_score

    # Extract user name; default to "unknown" if missing in payload.
    name = best.payload.get("name", "unknown")

    # Apply threshold to decide whether we trust the match.
    speaker = name if final_score >= threshold else "unknown"

    # Prepare a small leaderboard of the top-k results
    topN: List[Dict[str, float]] = [
        {
            "name": r.payload.get("name", "?"),
            "score": calibrate_score(float(r.score), raw_scores) if use_calibration else float(r.score)
        }
        for r in res
    ]

    return {"speaker": speaker, "confidence": final_score, "topN": topN}
