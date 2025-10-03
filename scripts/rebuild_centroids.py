

#!/usr/bin/env python3
"""
Trigger centroid rebuild via the FastAPI admin endpoint.

What this script does
---------------------
It sends a POST request to your running speaker-id API at `/rebuild_centroids`.
That endpoint should recompute each user's "master" embedding (centroid = mean
vector of that user's raw enrollment clips). This is useful when you've added
new clips and want the master vectors to reflect the latest data.

How to run
----------
  python scripts/rebuild_centroids.py --url http://localhost:8080

Environment variables
---------------------
- API_URL: default base URL for the API (e.g., http://localhost:8080)

Exit codes
----------
- 0 on success
- 1 if the HTTP request failed
"""
from __future__ import annotations

import argparse
import os
import sys

# Third-party: lightweight HTTP client for making the POST request.
import requests

# Read default API base URL from env, fallback to localhost.
DEFAULT_API = os.getenv("API_URL", "http://localhost:8080")


def main() -> int:
    """CLI entrypoint: parse args, call the endpoint, print a friendly result."""
    parser = argparse.ArgumentParser(description="Rebuild centroids via API")
    parser.add_argument(
        "--url",
        default=DEFAULT_API,
        help="Base URL of the speaker-id API (default: %(default)s)",
    )
    args = parser.parse_args()

    # Normalize base URL and append our admin path.
    url = args.url.rstrip("/") + "/rebuild_centroids"

    try:
        # Send POST request. There's no body required for this endpoint.
        resp = requests.post(url, timeout=30)
    except requests.RequestException as e:
        # Network/connection errors end up here.
        print(f"Request error: {e}")
        return 1

    if not resp.ok:
        # Non-2xx response. Print status and body to help debugging.
        print(f"HTTP {resp.status_code}: {resp.text}")
        return 1

    # Expected JSON: { "ok": true, "updated": <count> }
    try:
        data = resp.json()
    except ValueError:
        print("Response was not valid JSON.")
        return 1

    updated = data.get("updated")
    print(f"Rebuilt centroids — updated: {updated} users")
    return 0


if __name__ == "__main__":
    # Exit with the return code so this plays nice in CI/Make.
    sys.exit(main())
