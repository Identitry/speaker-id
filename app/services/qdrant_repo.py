"""Qdrant repository helpers for the speaker-id service.

This module encapsulates all direct interaction with Qdrant.
We maintain two collections:

- `speakers_raw`    : one point per enrollment clip (kept for auditing and
                      optional fine-grained verification).
- `speakers_master` : one point per user, representing the centroid (mean
                      embedding) of all that user's raw clips. This is the
                      fast path used by `/identify` queries.

Notes on metrics and scores
---------------------------
We configure both collections with **COSINE** distance. Newer Qdrant client
versions typically return a *distance* for cosine (lower = better), not a
similarity. If you want a similarity-like score in [0..1], a common approach
is `score = 1 - distance`. See `app/services/identify.py` for how the result
is normalized on the read path.

Vector dimensionality
---------------------
The embedding dimension is taken from the active embedding backend.
"""
from __future__ import annotations

import hashlib
import time
from typing import List
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct

from app.core.config import settings
from app.core.logging import logger
from app.services.embeddings import get_embedding_dim

# Collection names used across the app. Keep these in sync with other modules.
RAW = "speakers_raw"
MASTER = "speakers_master"

# Embedding size dynamically obtained from the active backend.
DIM = get_embedding_dim()

# Single shared client process-wide. FastAPI workers typically reuse this.
_client = QdrantClient(url=settings.qdrant_url)


def ensure_collections() -> None:
    """Ensure both collections exist with COSINE distance and the right size.

    Safe to call multiple times (idempotent). We intentionally use
    `recreate_collection` upon creation to ensure correct params if the
    collection was missing. We do **not** drop existing collections here; use
    admin scripts if you need to reset.
    """
    cols = {c.name for c in _client.get_collections().collections}

    if RAW not in cols:
        logger.info("Creating Qdrant collection %s (dim=%s, metric=COSINE)", RAW, DIM)
        _client.recreate_collection(
            collection_name=RAW,
            vectors_config=VectorParams(size=DIM, distance=Distance.COSINE),
        )

    if MASTER not in cols:
        logger.info("Creating Qdrant collection %s (dim=%s, metric=COSINE)", MASTER, DIM)
        _client.recreate_collection(
            collection_name=MASTER,
            vectors_config=VectorParams(size=DIM, distance=Distance.COSINE),
        )


# Small helpers to keep payloads and ids consistent
_def_payload = lambda name: {"name": name, "ts": int(time.time())}
# Stable per-user point id for the MASTER collection (derived from name)
_def_id = lambda name: int(
    hashlib.sha1(f"{name}-master".encode()).hexdigest()[:12], 16
)


def upsert_raw_and_update_master(name: str, vec) -> None:
    """Insert a raw clip point and refresh that user's master centroid.

    Parameters
    ----------
    name : str
        Logical user name (used in payload and the master-id derivation).
    vec : numpy.ndarray or list[float]
        Embedding vector (assumed length DIM). Will be sent as list[float].

    Behavior
    --------
    - Inserts a new point into `speakers_raw` with a timestamp payload.
    - Calls `rebuild_master_for(name)` to recompute the mean vector and upsert
      (create/update) the single "master" point in `speakers_master`.
    """
    ensure_collections()

    _client.upsert(
        collection_name=RAW,
        points=[
            {
                "id": str(uuid4()),
                "vector": (vec.tolist() if hasattr(vec, "tolist") else vec),
                "payload": _def_payload(name),
            }
        ],
        wait=True,
    )

    # Update per-user centroid used by /identify
    rebuild_master_for(name)


def list_master_profiles() -> List[str]:
    """Return a list of user names present in the MASTER collection.

    We only need payloads here (names), so we don't request vectors.
    """
    ensure_collections()
    res = _client.scroll(collection_name=MASTER, limit=1000, with_payload=True)
    # `scroll` returns (points, next_page). We only fetch the first page here
    # because this is for UI/debug listings. Extend if you expect >1000 users.
    return [p.payload.get("name", "?") for p in res[0]]


def reset_profiles(name: str | None = None, drop_all: bool = False) -> None:
    """Delete data either globally or for a single user.

    Parameters
    ----------
    name : Optional[str]
        When provided, delete only that user's data (raw + master).
    drop_all : bool
        If True, drop **both** collections entirely and recreate them.
    """
    ensure_collections()

    if drop_all:
        logger.warning("Dropping both Qdrant collections: %s, %s", RAW, MASTER)
        _client.delete_collection(RAW)
        _client.delete_collection(MASTER)
        ensure_collections()
        return

    if name is None:
        # Nothing to do if no name and not dropping all
        return

    # Delete all raw points where payload.name == name
    _client.delete(
        collection_name=RAW,
        points_selector={
            "filter": {"must": [{"key": "name", "match": {"value": name}}]}
        },
    )

    # Delete the single master point (stable id derived from name)
    _client.delete(
        collection_name=MASTER,
        points_selector={"points": [_def_id(name)]},
    )


def rebuild_master_for(name: str) -> int:
    """Recompute and upsert the centroid for a single user.

    Returns
    -------
    int
        Number of raw clips found for this user (0 if none; in that case no
        master point is written).
    """
    ensure_collections()

    # Build a filter to scroll only this user's raw points.
    from qdrant_client.http.models import Filter, FieldCondition, MatchValue

    flt = Filter(must=[FieldCondition(key="name", match=MatchValue(value=name))])

    # Fetch up to 10k raw points for this user. If you expect more, implement
    # proper pagination (another scroll loop).
    pts, _ = _client.scroll(
        collection_name=RAW,
        scroll_filter=flt,
        with_payload=False,
        with_vectors=True,
        limit=10000,
    )
    if not pts:
        return 0

    # Compute the arithmetic mean (centroid). This is a strong baseline for
    # speaker verification and keeps the query side fast.
    import numpy as np

    mat = np.vstack([p.vector for p in pts]).astype("float32")
    mean = mat.mean(axis=0)

    _client.upsert(
        collection_name=MASTER,
        points=[
            {
                "id": _def_id(name),
                "vector": (mean.tolist() if hasattr(mean, "tolist") else mean),
                "payload": {"name": name, "n": len(pts)},
            }
        ],
        wait=True,
    )
    return len(pts)


def iter_master():
    """Return all points from MASTER (single page up to 10k) with payloads.

    For admin/maintenance tasks. If you need to handle more than 10k users,
    convert this to a proper scroll loop like in `scripts/export_profiles.py`.
    """
    pts, _ = _client.scroll(collection_name=MASTER, with_payload=True, limit=10000)
    return pts
