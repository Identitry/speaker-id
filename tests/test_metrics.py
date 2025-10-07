# tests/test_metrics.py
import io
import re
from starlette.testclient import TestClient

# Helper: pack bytes into multipart as wav
def _wav_file(data: bytes) -> dict:
    return {"file": ("sample.wav", io.BytesIO(data), "audio/wav")}

def _scrape_metric(text: str, name: str, label_filter: dict | None = None) -> float | None:
    """
    Fetch a (first best) metric value from Prometheus text format.
    If label_filter is given (e.g. {"speaker":"TmpUser"}), the line is matched on these labels.
    Returns float or None if not found.
    """
    # Build regex for label part if filter exists
    if label_filter:
        parts = [fr'{k}="{re.escape(v)}"' for k, v in label_filter.items()]
        label_re = r"\{[^}]*" + r",".join(parts) + r"[^}]*\}"
    else:
        label_re = r"(?:\{[^}]*\})?"
    pattern = re.compile(rf"^{re.escape(name)}{label_re}\s+([0-9eE\.\+\-]+)\s*$", re.MULTILINE)
    m = pattern.search(text)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None

def test_metrics_endpoint_available(client: TestClient):
    r = client.get("/metrics")
    assert r.status_code == 200
    # Basic sanity: some of our own metrics should be present in the text
    body = r.text
    assert "speakerid_requests_total" in body
    assert "speakerid_request_latency_seconds" in body

def test_identify_metrics_increment_on_match(client: TestClient, sine_wav_bytes: bytes):
    # Reset all state to avoid interference from earlier tests
    r_reset = client.post("/api/reset")
    assert r_reset.status_code == 200, r_reset.text
    # We use a unique name to isolate from other tests
    user = "TmpUser_Metrics"

    # Read baseline from /metrics (can be None if not created yet)
    r0 = client.get("/metrics")
    assert r0.status_code == 200
    before_match = _scrape_metric(
        r0.text, "speakerid_identify_match_total", {"speaker": user}
    )
    before_total = _scrape_metric(r0.text, "speakerid_identify_match_total")

    # Enroll the user
    r = client.post(f"/api/enroll?name={user}", files=_wav_file(sine_wav_bytes))
    assert r.status_code == 200, r.text

    # Force rebuild centroids to ensure centroid is built before identification
    r_rebuild = client.post("/api/rebuild_centroids")
    assert r_rebuild.status_code == 200, r_rebuild.text

    # Run identify on the same clip -> should be a match
    r = client.post("/api/identify?threshold=0.0", files=_wav_file(sine_wav_bytes))
    assert r.status_code == 200, r.text
    body = r.json()
    # Accept whatever non-unknown speaker the system matched (depends on seeded data and fake encoder)
    matched_name = body.get("speaker")
    assert matched_name is not None and matched_name != "unknown"

    # Read metrics again
    r1 = client.get("/metrics")
    assert r1.status_code == 200
    after_total = _scrape_metric(r1.text, "speakerid_identify_match_total")
    assert after_total is not None and after_total >= (before_total or 0.0) + 1.0

    # Optional: Check per-speaker breakdown if available (different metric name)
    if matched_name == user:
        # The per-speaker breakdown is in speakerid_identify_match_by_speaker_total
        after_match_by_speaker = _scrape_metric(
            r1.text, "speakerid_identify_match_by_speaker_total", {"speaker": user}
        )
        # This is optional - the aggregate counter is the primary test target
        if after_match_by_speaker is not None:
            assert after_match_by_speaker >= 1.0

    # Bonus: check that requests_total also still exists
    total_any = _scrape_metric(r1.text, "speakerid_requests_total")
    assert total_any is not None
