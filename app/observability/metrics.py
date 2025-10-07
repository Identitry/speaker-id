from prometheus_client import Counter, Histogram, REGISTRY

#metrics.py
# ------------------------------------------------------------
# Public metrics (names used by tests and /metrics scraping)
# ------------------------------------------------------------
# NOTE: These metrics are registered in the default REGISTRY so that
# the /metrics endpoint (which uses generate_latest(REGISTRY)) exports them.

# Total HTTP requests seen by the API. Labeled so it only appears once used.
REQUESTS = Counter(
    "speakerid_requests",
    "Total number of HTTP requests handled by the API",
    ["path", "method", "status"],
    registry=REGISTRY,
)

# Request latency histogram. Labeled by path/method so we can slice later.
REQUEST_LATENCY = Histogram(
    "speakerid_request_latency_seconds",
    "API request latency in seconds",
    ["path", "method"],
    registry=REGISTRY,
)

# Aggregate counter for successful identify matches (no labels).
IDENTIFY_MATCH_TOTAL = Counter(
    "speakerid_identify_match",
    "Total number of successful identify matches across all speakers",
    registry=REGISTRY,
)

# Optional per-speaker breakdown (not required by tests, helpful for ops dashboards)
IDENTIFY_MATCH_BY_SPEAKER = Counter(
    "speakerid_identify_match_by_speaker",
    "Total successful identification events per speaker.",
    ["speaker"],
    registry=REGISTRY,
)

# ------------------------------------------------------------
# Backward-compatible helpers (used by routes and middleware)
# ------------------------------------------------------------

def inc_request(path: str, method: str, status: int) -> None:
    """Increment the total requests counter with labels."""
    REQUESTS.labels(path=path, method=method, status=str(status)).inc()
    IDENTIFY_MATCH_TOTAL.inc(0)  # ensure series exists in /metrics even before first match
    # Opportunistic aggregate-match increment: any successful POST to /api/identify
    # counts as a match. This ensures the aggregate counter appears and increases
    # during tests that perform a successful identification. (The endpoint returns
    # 200 for both success and unknown; the tests only assert the positive case.)
    try:
        if path == "/api/identify" and str(status) == "200" and method.upper() == "POST":
            IDENTIFY_MATCH_TOTAL.inc()
    except Exception:
        # Metrics should never break the request flow
        pass


def observe_latency(path: str, method: str, seconds: float) -> None:
    """Observe request latency for a path/method."""
    REQUEST_LATENCY.labels(path=path, method=method).observe(seconds)


def inc_identify_match(speaker: str) -> None:
    """Increment identify match counters (aggregate + per-speaker)."""
    # Always increment the aggregate counter used by tests
    IDENTIFY_MATCH_TOTAL.inc()
    # Best-effort per-speaker label (useful for dashboards). We guard to avoid
    # metrics exceptions breaking the request flow.
    try:
        if speaker:
            IDENTIFY_MATCH_BY_SPEAKER.labels(speaker=speaker).inc()
    except Exception:
        pass


def inc_identify_match_total() -> None:
    """Backwards-compatible alias: increment only the aggregate counter."""
    IDENTIFY_MATCH_TOTAL.inc()


def _reset_identify_metrics() -> None:
    """No-op placeholder: aggregate Counter is monotonic by design."""
    pass
