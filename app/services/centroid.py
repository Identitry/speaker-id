"""Centroid maintenance helpers.

This module provides utilities to (re)compute the per‑user "master" embeddings
stored in the `speakers_master` collection. A master embedding is simply the
centroid (arithmetic mean) of all raw enrollment vectors for a user.

Why centroids?
--------------
Using a centroid per user keeps the online identification path fast: we search
against one vector per user instead of many raw clips. Rebuilding centroids
periodically (or incrementally at enroll time) lets the representation drift
with new audio while remaining robust to outliers.
"""
from __future__ import annotations

from typing import Iterable, Set

from app.services.qdrant_repo import iter_master, rebuild_master_for


def rebuild_all_centroids() -> int:
    """Recompute centroids for all users present in the MASTER collection.

    Returns
    -------
    int
        Number of users for which a centroid was (re)computed. Users without
        any raw clips will yield 0 from `rebuild_master_for` and do not count
        toward the total.

    Notes
    -----
    - This function operates on the list of names *already* present in the
      MASTER collection. If you want to include users who only have raw clips
      but no master yet, add a pass over `speakers_raw` to collect names.
    - Intended for admin/maintenance tasks (e.g., a nightly job) rather than
      per-request use.
    """
    # Collect unique user names from existing master points. `iter_master()`
    # returns up to ~10k points in a single page which is fine for most home
    # deployments; for larger sets, switch to a paginated scroll.
    pts = iter_master()
    names: Set[str] = {
        p.payload.get("name")  # type: ignore[assignment]
        for p in pts
        if p.payload and p.payload.get("name")
    }

    updated = 0
    for nm in names:
        # `rebuild_master_for` returns the number of raw clips used. Count this
        # user as updated if at least one clip was found.
        updated += 1 if rebuild_master_for(nm) else 0
    return updated
