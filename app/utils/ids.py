"""
Utility functions for generating and parsing point IDs.

We namespace IDs to avoid collisions between raw embeddings and master
centroids. Qdrant requires IDs to be either integers or UUIDs.
"""

import uuid
from typing import Union

# Types
PointId = Union[int, str]

def make_raw_id(name: str) -> str:
    """Generate a unique point ID for a raw embedding of a given speaker."""
    return f"raw::{name}::{uuid.uuid4().hex}"

def make_master_id(name: str) -> str:
    """Generate the deterministic master centroid ID for a speaker."""
    return f"master::{name}"

def is_master_id(pid: str) -> bool:
    """Return True if the given point ID is a master centroid ID."""
    return pid.startswith("master::")

def parse_id(pid: str) -> dict:
    """Parse a point ID into its components."""
    parts = pid.split("::")
    if parts[0] == "raw" and len(parts) == 3:
        return {"kind": "raw", "name": parts[1], "uuid": parts[2]}
    elif parts[0] == "master" and len(parts) == 2:
        return {"kind": "master", "name": parts[1]}
    else:
        return {"kind": "unknown", "id": pid}
