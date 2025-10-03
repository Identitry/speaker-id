#!/usr/bin/env python3
"""
Export speaker profiles from Qdrant to JSON or CSV.

Enhancements over the basic version:
- --collection: choose which collection to export (default: speakers_master)
- --no-vectors: skip exporting vectors to reduce file size and speed up export
- --limit: stop after N points (handy for quick tests)
- --indent / --delimiter: formatting options for JSON/CSV
- Better error handling with friendly messages if Qdrant is unreachable

Examples
--------
  # Export all master profiles to JSON (pretty)
  python scripts/export_profiles.py --out exports/profiles.json

  # Export raw enrollment points to CSV without vectors
  python scripts/export_profiles.py --collection speakers_raw \
      --no-vectors --out exports/raw.csv --format csv

  # Export first 100 master profiles as compact JSON
  python scripts/export_profiles.py --limit 100 --indent 0 --out exports/top100.json
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Iterable, List

from qdrant_client import QdrantClient
from qdrant_client.conversions.common_types import ScoredPoint
from qdrant_client.http import models as qmodels

DEFAULT_COLLECTION = "speakers_master"


def scroll_all(
    client: QdrantClient,
    collection: str,
    with_vectors: bool,
    limit: int | None = None,
) -> List[ScoredPoint]:
    """Scroll through a collection and return up to `limit` points.

    This uses Qdrant's `scroll` API which returns (points, next_page_offset).
    We keep calling it until we either run out of points or reach `limit`.
    """
    out: List[ScoredPoint] = []
    next_page = None
    remaining = limit if limit is not None else float("inf")

    while remaining > 0:
        batch_limit = int(min(1000, remaining)) if remaining != float("inf") else 1000
        points, next_page = client.scroll(
            collection_name=collection,
            with_payload=True,
            with_vectors=with_vectors,
            limit=batch_limit,
            offset=next_page,
        )
        out.extend(points)
        if limit is not None:
            remaining -= len(points)
        if not next_page or not points:
            break
    return out


def rows_from_points(points: Iterable[ScoredPoint], include_vectors: bool) -> List[dict]:
    """Convert Qdrant points to plain dictionaries suitable for JSON/CSV."""
    rows: List[dict] = []
    for p in points:
        payload = p.payload or {}
        row = {
            "id": p.id,
            "name": payload.get("name"),
            "n": payload.get("n"),
            "updated_at": payload.get("updated_at"),
        }
        if include_vectors:
            row["vector"] = p.vector
        rows.append(row)
    return rows


def write_json(rows: List[dict], path: Path, indent: int | None) -> None:
    """Write rows as JSON. `indent=0` produces compact output; None uses default."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Map indent=0 to None for most compact form without extra whitespace.
    _indent = None if indent == 0 else indent
    with path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=_indent)


def write_csv(rows: List[dict], path: Path, delimiter: str, include_vectors: bool) -> None:
    """Write rows as CSV. Vector is written as a semicolon-separated string."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=delimiter)
        headers = ["id", "name", "n", "updated_at"]
        if include_vectors:
            headers.append("vector")
        w.writerow(headers)
        for r in rows:
            row = [r.get("id"), r.get("name"), r.get("n"), r.get("updated_at")]
            if include_vectors:
                vec = r.get("vector") or []
                vec_str = ";".join(f"{x:.6f}" for x in vec)
                row.append(vec_str)
            w.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export speaker profiles from Qdrant")
    parser.add_argument("--url", default=os.getenv("QDRANT_URL", "http://localhost:6333"), help="Qdrant base URL")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION, help=f"Collection to export (default: {DEFAULT_COLLECTION})")
    parser.add_argument("--out", required=True, help="Output file path (.json or .csv)")
    parser.add_argument("--format", choices=["json", "csv"], help="Output format (overrides extension)")
    parser.add_argument("--no-vectors", action="store_true", help="Skip vectors in output (faster/smaller)")
    parser.add_argument("--limit", type=int, default=None, help="Max number of points to export")
    parser.add_argument("--indent", type=int, default=2, help="JSON indent (0 for compact; default 2)")
    parser.add_argument("--delimiter", default=",", help="CSV delimiter (default ',')")
    args = parser.parse_args()

    # Determine output format from --format or file extension
    out_path = Path(args.out)
    fmt = args.format or (out_path.suffix.lstrip(".").lower())
    if fmt not in {"json", "csv"}:
        raise SystemExit("Output format must be json or csv (match --format or file extension)")

    include_vectors = not args.no_vectors

    # Connect to Qdrant with friendly error handling.
    try:
        client = QdrantClient(url=args.url)
        # quick ping by listing collections — catches most connectivity issues early
        _ = client.get_collections()
    except Exception as e:
        print(f"Could not connect to Qdrant at {args.url}: {e}")
        return 1

    try:
        points = scroll_all(client, args.collection, with_vectors=include_vectors, limit=args.limit)
    except Exception as e:
        print(f"Failed to scroll collection '{args.collection}': {e}")
        return 1

    rows = rows_from_points(points, include_vectors=include_vectors)

    try:
        if fmt == "json":
            write_json(rows, out_path, indent=args.indent)
        else:
            write_csv(rows, out_path, delimiter=args.delimiter, include_vectors=include_vectors)
    except Exception as e:
        print(f"Failed to write output to {out_path}: {e}")
        return 1

    print(
        f"Exported {len(rows)} point(s) from '{args.collection}' to {out_path} "
        f"(vectors: {'yes' if include_vectors else 'no'})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
