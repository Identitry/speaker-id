#!/usr/bin/env python3
"""
Initialize Qdrant collections for the speaker-id project.

What this script does
---------------------
- Connects to a running Qdrant instance
- Ensures two collections exist (creating them if missing):
    * speakers_raw
        One point per enrollment clip. Useful for auditing, advanced
        verification (e.g., re-check against nearest raw clips), or
        re-computing centroids later.
    * speakers_master
        One point per user (rolling mean / centroid of all their raw clips).
        This is the fast path used for /identify search.

You can run this multiple times safely. Pass --recreate if you want to drop and
recreate both collections (dangerous in production!).

Environment
-----------
QDRANT_URL  Base URL to Qdrant, e.g. http://localhost:6333 (default)

Examples
--------
  # Create collections if missing
  python scripts/init_qdrant.py

  # Drop and recreate both collections
  python scripts/init_qdrant.py --recreate
"""
from __future__ import annotations

import argparse
import os
import sys

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

# Collection names used by the app. Keep these in sync with the API code.
RAW = "speakers_raw"
MASTER = "speakers_master"

# Vector dimensionality. Resemblyzer embeddings are 256-D. If you later switch
# to a different backend that outputs another size (e.g. 192), update this.
DIM = 256


def ensure_collections(client: QdrantClient, recreate: bool = False) -> None:
    """Ensure both collections exist with the expected configuration.

    Parameters
    ----------
    client : QdrantClient
        Connected client to your Qdrant instance.
    recreate : bool
        If True, delete and recreate the collections.
    """
    # List currently available collections (names only).
    existing = {c.name for c in client.get_collections().collections}

    if recreate:
        # Dangerous in production: drops both collections entirely.
        if RAW in existing:
            client.delete_collection(RAW)
            existing.remove(RAW)
        if MASTER in existing:
            client.delete_collection(MASTER)
            existing.remove(MASTER)

    if RAW not in existing:
        client.recreate_collection(
            collection_name=RAW,
            vectors_config=VectorParams(size=DIM, distance=Distance.COSINE),
        )

    if MASTER not in existing:
        client.recreate_collection(
            collection_name=MASTER,
            vectors_config=VectorParams(size=DIM, distance=Distance.COSINE),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize Qdrant collections")
    parser.add_argument(
        "--url",
        default=os.getenv("QDRANT_URL", "http://localhost:6333"),
        help="Qdrant base URL (default: %(default)s)",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Drop and recreate both collections (data loss!)",
    )
    args = parser.parse_args()

    try:
        client = QdrantClient(url=args.url)
        ensure_collections(client, recreate=args.recreate)
    except Exception as e:
        print(f"❌ Failed to initialize Qdrant at {args.url}: {e}")
        return 1

    print(f"Qdrant ready at {args.url} — collections ensured: {RAW}, {MASTER}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
