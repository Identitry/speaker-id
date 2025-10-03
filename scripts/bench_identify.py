#!/usr/bin/env python3
"""
Benchmark client for the speaker-id API (/identify).

This script repeatedly sends small WAV audio clips to your FastAPI service's
`/identify` endpoint and measures latency and accuracy. It's useful for
stress-testing, tuning thresholds, and verifying that the service keeps up
under concurrency.

Quick usage examples:
  python scripts/bench_identify.py --url http://localhost:8080/identify \
      --clips data/test_wavs --runs 100 --warmup 5 --threshold 0.82

  # Concurrency (8 parallel workers)
  python scripts/bench_identify.py --url http://localhost:8080/identify \
      --clips data/test_wavs --runs 200 --concurrency 8

Notes:
- Expects a directory containing `.wav` files (mono/stereo, any sample rate).
  The **server** is responsible for resampling to 16 kHz mono, so we don't do
  any audio processing here. We simply stream files as-is.
- Reports latency percentiles (p50/p90/p95/p99), success rate, per-speaker
  distribution, and the share of `unknown` results.
- Optional JSON output can be enabled with `--json` for dashboards/pipelines.
"""
from __future__ import annotations

# --- Standard library imports ---
import argparse
import random
import statistics as stats
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import List

# --- Third-party imports ---
# `requests` is used for simple HTTP multipart uploads to the FastAPI endpoint.
import requests

# Default endpoint used when --url is not provided.
DEFAULT_URL = "http://localhost:8080/identify"


@dataclass
class BenchResult:
    """Holds the outcome for a single HTTP request.

    Attributes
    ----------
    lat_ms : float
        Round-trip latency in **milliseconds** for the HTTP request.
    ok : bool
        True if the server returned a 2xx status code.
    speaker : str | None
        The predicted speaker name (or "unknown"). None when request failed.
    confidence : float | None
        The confidence score returned by the server. None when failed.
    error : str | None
        Error text for non-2xx responses or client-side exceptions.
    file : str | None
        Path to the WAV file that was sent for this request.
    """

    lat_ms: float
    ok: bool
    speaker: str | None
    confidence: float | None
    error: str | None = None
    file: str | None = None


def iter_wavs(path: Path) -> List[Path]:
    """Collect all `.wav` files under a directory (recursively).

    Parameters
    ----------
    path : Path
        Directory containing test audio clips.

    Returns
    -------
    List[Path]
        A list of file paths to WAV files.
    """
    if not path.exists() or not path.is_dir():
        raise SystemExit(f"No such directory: {path}")
    files = [p for p in path.rglob("*.wav") if p.is_file()]
    if not files:
        raise SystemExit(f"No .wav files found under: {path}")
    return files


def do_call(
    url: str,
    wav_path: Path,
    threshold: float | None,
    topk: int | None,
    timeout: float,
) -> BenchResult:
    """Send a single WAV file to `/identify` and measure latency.

    This function builds a `multipart/form-data` request with the audio clip
    and optional query parameters (threshold/topk). It returns a `BenchResult`
    capturing latency, predicted speaker, confidence, and any error.
    """
    t0 = time.perf_counter()
    try:
        # Build multipart payload. The key must be named "file" to match the API.
        with wav_path.open("rb") as fh:
            files = {"file": (wav_path.name, fh, "audio/wav")}
            params = {}
            if threshold is not None:
                params["threshold"] = str(threshold)
            if topk is not None:
                params["topk"] = str(topk)

            # POST the audio to the API. The server does the heavy lifting.
            resp = requests.post(url, files=files, params=params, timeout=timeout)

        # Measure wall-clock time for the request/response round trip.
        dt = (time.perf_counter() - t0) * 1000.0

        if resp.ok:
            # Parse JSON body on success. Expected fields: speaker, confidence.
            j = resp.json()
            speaker = j.get("speaker")
            conf = j.get("confidence")
            return BenchResult(lat_ms=dt, ok=True, speaker=speaker, confidence=conf, file=str(wav_path))
        else:
            # Non-2xx HTTP status. Keep the body text to help debugging.
            return BenchResult(
                lat_ms=dt,
                ok=False,
                speaker=None,
                confidence=None,
                error=f"HTTP {resp.status_code}: {resp.text}",
                file=str(wav_path),
            )
    except Exception as e:
        # Network/file/JSON errors end up here.
        dt = (time.perf_counter() - t0) * 1000.0
        return BenchResult(lat_ms=dt, ok=False, speaker=None, confidence=None, error=str(e), file=str(wav_path))


def percentile(values: List[float], p: float) -> float:
    """Compute the p-th percentile (float) for a sorted list.

    We implement a small interpolation ourselves to avoid pulling in NumPy for
    such a tiny task. Input *must* be pre-sorted for accurate results.
    """
    if not values:
        return 0.0
    k = (len(values) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(values) - 1)
    if f == c:
        return values[f]
    d0 = values[f] * (c - k)
    d1 = values[c] * (k - f)
    return d0 + d1


def summarize(results: List[BenchResult], unknown_name: str = "unknown") -> str:
    """Pretty print a human-readable summary of all runs.

    The summary includes:
    - total requests and error count
    - latency mean and selected percentiles
    - speaker distribution and unknown ratio
    - up to 5 error messages for quick troubleshooting
    """
    # Latencies for successful requests only (in milliseconds).
    lats = sorted([r.lat_ms for r in results if r.ok])
    # Collect failures for error reporting.
    errs = [r for r in results if not r.ok]
    # Speakers predicted by successful requests.
    speakers = [r.speaker for r in results if r.ok and r.speaker]
    unknowns = [s for s in speakers if s == unknown_name]

    lines = []
    lines.append(f"Total requests: {len(results)}")
    lines.append(f"Success: {len(lats)}  Errors: {len(errs)} ({(len(errs)/len(results))*100:.1f}% fail)")

    if lats:
        lines.append("Latency (ms):")
        lines.append(
            f"  mean {stats.mean(lats):.1f}  "
            f"p50 {percentile(lats,50):.1f}  "
            f"p90 {percentile(lats,90):.1f}  "
            f"p95 {percentile(lats,95):.1f}  "
            f"p99 {percentile(lats,99):.1f}"
        )

    if speakers:
        # Histogram of predicted speakers across successful requests.
        c = Counter(speakers)
        lines.append("Predicted speakers:")
        for name, cnt in c.most_common():
            lines.append(f"  {name:>10}: {cnt} ({(cnt/len(speakers))*100:.1f}%)")
        lines.append(f"Unknown ratio: {(len(unknowns)/len(speakers))*100:.1f}%")

    if errs:
        # Show a small sample of errors to keep output compact.
        lines.append("Errors (up to 5):")
        for e in errs[:5]:
            lines.append(f"  {e.error}  [file={e.file}]")

    return "\n".join(lines)


def main(argv: List[str] | None = None) -> int:
    """Command-line entrypoint.

    Parses arguments, warms up the service, runs the benchmark (optionally with
    concurrency), prints a human summary, and optionally prints a JSON payload
    that is easy to ingest into dashboards or CI logs.
    """
    ap = argparse.ArgumentParser(description="Benchmark the /identify endpoint")
    ap.add_argument("--url", default=DEFAULT_URL, help="Identify endpoint URL (default: %(default)s)")
    ap.add_argument("--clips", type=Path, required=True, help="Directory with .wav files")
    ap.add_argument("--runs", type=int, default=100, help="Total number of requests to send")
    ap.add_argument("--warmup", type=int, default=5, help="Warmup requests (not measured)")
    ap.add_argument("--threshold", type=float, default=None, help="Override threshold query param")
    ap.add_argument("--topk", type=int, default=None, help="Override topk query param")
    ap.add_argument("--concurrency", type=int, default=1, help="Number of parallel workers")
    ap.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout seconds")
    ap.add_argument("--seed", type=int, default=42, help="RNG seed for file sampling")
    ap.add_argument("--json", action="store_true", help="Print machine-readable JSON summary as well")

    args = ap.parse_args(argv)

    # Deterministic file sampling for reproducible runs.
    random.seed(args.seed)
    wavs = iter_wavs(args.clips)

    # --- Warmup phase ---
    # Sends a few requests that are NOT included in the final statistics.
    # This lets the server initialize models/caches, so the real run reflects
    # steady-state performance.
    if args.warmup > 0:
        for _ in range(args.warmup):
            do_call(args.url, random.choice(wavs), args.threshold, args.topk, args.timeout)

    # --- Benchmark phase ---
    results: List[BenchResult] = []

    if args.concurrency <= 1:
        # Sequential mode: simple for-loop.
        for _ in range(args.runs):
            wav = random.choice(wavs)
            res = do_call(args.url, wav, args.threshold, args.topk, args.timeout)
            results.append(res)
    else:
        # Concurrent mode: fire multiple requests in parallel using threads.
        # ThreadPool is fine here because `requests` is I/O-bound.
        with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
            futures = [
                ex.submit(do_call, args.url, random.choice(wavs), args.threshold, args.topk, args.timeout)
                for _ in range(args.runs)
            ]
            for fut in as_completed(futures):
                results.append(fut.result())

    # Human-friendly summary.
    print(summarize(results))

    # Optional machine-readable JSON for automation.
    if args.json:
        import json
        lats = [r.lat_ms for r in results if r.ok]
        out = {
            "total": len(results),
            "success": len(lats),
            "errors": len(results) - len(lats),
            "latency_ms": {
                "mean": (stats.mean(lats) if lats else 0.0),
                "p50": percentile(lats, 50) if lats else 0.0,
                "p90": percentile(lats, 90) if lats else 0.0,
                "p95": percentile(lats, 95) if lats else 0.0,
                "p99": percentile(lats, 99) if lats else 0.0,
            },
            # List of (speaker, count) tuples sorted by frequency.
            "by_speaker": Counter([r.speaker for r in results if r.ok and r.speaker]).most_common(),
        }
        print("\nJSON:\n" + json.dumps(out, indent=2))

    return 0


if __name__ == "__main__":
    # `SystemExit` with the return value makes the script friendly to CI and Makefiles.
    raise SystemExit(main())
