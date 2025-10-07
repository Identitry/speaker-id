from prometheus_client import Counter, Histogram, REGISTRY

# ------------------------------------------------------------
# Public metrics (names used by tests and /metrics scraping)
# ------------------------------------------------------------
# NOTE: These metrics are registered in the default REGISTRY so that
# the /metrics endpoint (which uses generate_latest(REGISTRY)) exports them.

# Total HTTP requests seen by the API. Labeled so it only appears once used.
REQUESTS = Counter(
    "speakerid_requests_total",
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

# Successful identify matches — total (unlabeled) and per-speaker (labeled)
IDENTIFY_MATCH_TOTAL = Counter(
    "speakerid_identify_match_total",
    "Total successful identify matches (all speakers)",
    registry=REGISTRY,
)

IDENTIFY_MATCH_BY_SPEAKER = Counter(
    "speakerid_identify_match_by_speaker_total",
    "Successful identify matches per speaker",
    ["speaker"],
    registry=REGISTRY,
)

# ------------------------------------------------------------
# Backward-compatible helpers (used by routes and middleware)
# ------------------------------------------------------------

def inc_request(path: str, method: str, status: int) -> None:
    """Increment the total requests counter with labels."""
    REQUESTS.labels(path=path, method=method, status=str(status)).inc()


def observe_latency(path: str, method: str, seconds: float) -> None:
    """Observe request latency for a path/method."""
    REQUEST_LATENCY.labels(path=path, method=method).observe(seconds)


def inc_identify_match(speaker: str) -> None:
    """Increment both the total and per-speaker identify match counters."""
    IDENTIFY_MATCH_TOTAL.inc()
    IDENTIFY_MATCH_BY_SPEAKER.labels(speaker=speaker).inc()
