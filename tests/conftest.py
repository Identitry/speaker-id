import io
import os
import struct
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import pytest
from fastapi.testclient import TestClient

try:
    from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
except Exception:
    Counter = None
    Histogram = None
    generate_latest = None
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

@pytest.fixture(scope="session", autouse=True)
def _enable_metrics_env():
    """Ensure Prometheus metrics are enabled for the entire test session.

    This runs before the app is imported (session autouse), so the `/metrics`
    endpoint is mounted when `app.main` builds the FastAPI app.
    """
    mp = pytest.MonkeyPatch()
    mp.setenv("METRICS_ENABLED", "1")
    mp.setenv("ENABLE_METRICS", "1")
    mp.setenv("PROMETHEUS_ENABLED", "1")
    try:
        yield
    finally:
        mp.undo()

# ------------------------------
# Dummy encoder (192-dim) & helpers
# ------------------------------
class DummyEncoder:
    dim: int = 192

    def embed_vector(self, wav: np.ndarray, sr: int) -> np.ndarray:
        # Deterministic pseudo-embedding based on length to avoid all-zeros degeneracy
        rng = np.random.default_rng(len(wav))
        v = rng.normal(size=self.dim).astype(np.float32)
        # L2-normalize to play nice with cosine
        n = np.linalg.norm(v)
        return (v / n) if n > 0 else v


# ------------------------------
# Prometheus metrics used by tests
# ------------------------------
# NOTE: We no longer define metrics here; instead we import from app.observability.metrics
# to avoid duplicate registration errors. The real metrics module is the source of truth.
try:
    from app.observability import metrics as real_metrics
    SPEAKERID_REQUESTS_TOTAL = getattr(real_metrics, 'REQUESTS', None)
    SPEAKERID_IDENTIFY_MATCH_TOTAL = getattr(real_metrics, 'IDENTIFY_MATCH_TOTAL', None)
    SPEAKERID_REQUEST_LATENCY_SECONDS = getattr(real_metrics, 'REQUEST_LATENCY', None)
except Exception:
    SPEAKERID_REQUESTS_TOTAL = None
    SPEAKERID_IDENTIFY_MATCH_TOTAL = None
    SPEAKERID_REQUEST_LATENCY_SECONDS = None


# ------------------------------
# Fake Qdrant client (minimal features for tests)
# ------------------------------
class FakeQdrantClient:
    def __init__(self, dim: int = 192):
        self.dim = dim
        # collections: name -> list of point dicts {id, vector(np.ndarray), payload(dict)}
        self._collections: Dict[str, List[Dict[str, Any]]] = {
            "speakers_raw": [],
            "speakers_master": [],
        }

    # --- collection management ---
    def get_collections(self):
        cols = [SimpleNamespace(name=name) for name in self._collections.keys()]
        return SimpleNamespace(collections=cols)

    def recreate_collection(self, collection_name: str, **kwargs):
        # reset the collection
        self._collections[collection_name] = []
        return SimpleNamespace(result=True)

    # --- data ops ---
    def upsert(self, collection_name: str, points: Iterable[Dict[str, Any]], **kwargs):
        store = self._collections.setdefault(collection_name, [])
        for p in points:
            pid = p.get("id")
            vec = p.get("vector")
            payload = p.get("payload") or {}
            v = np.asarray(vec, dtype=np.float32)
            if v.shape[0] != self.dim:
                raise ValueError(f"Vector dim mismatch: expected {self.dim}, got {v.shape[0]}")
            # replace if id exists
            existing = next((i for i, it in enumerate(store) if it.get("id") == pid), None)
            rec = {"id": pid, "vector": v, "payload": payload}
            if existing is not None:
                store[existing] = rec
            else:
                store.append(rec)
        return SimpleNamespace(result=True)

    def search(self, collection_name: str, query_vector: Iterable[float], limit: int = 5, with_payload: bool = True, **kwargs):
        # cosine distance (lower better). We'll return objects with .score and .payload
        q = np.asarray(list(query_vector), dtype=np.float32)
        if q.shape[0] != self.dim:
            # mimic server-side validation error message
            raise RuntimeError(f"Wrong input: Vector dimension error: expected dim: {self.dim}, got {q.shape[0]}")
        res = []
        for p in self._collections.get(collection_name, []):
            v = p["vector"]
            # cosine distance = 1 - cosine similarity
            denom = (np.linalg.norm(q) * np.linalg.norm(v))
            sim = float(q @ v / denom) if denom != 0 else 0.0
            dist = 1.0 - sim
            res.append(SimpleNamespace(score=dist, payload=p.get("payload", {})))
        res.sort(key=lambda r: r.score)
        return res[:limit]

    def scroll(self, collection_name: str, limit: int = 100, with_payload: bool = True, filter: Optional[Dict[str, Any]] = None, **kwargs):
        items = self._collections.get(collection_name, [])
        if filter and "must" in filter:
            # very tiny filter implementation for payload name equality
            name = None
            for cond in filter["must"]:
                if cond.get("key") == "name":
                    m = cond.get("match") or {}
                    name = m.get("value")
            if name is not None:
                items = [p for p in items if p.get("payload", {}).get("name") == name]
        # emulate API result shape as a tuple (points, next_page)
        pts = [SimpleNamespace(id=p["id"], payload=p.get("payload", {}), vector=p["vector"]) for p in items[:limit]]
        next_page = None
        return pts, next_page

    def delete(self, collection_name: str, points_selector: Dict[str, Any], **kwargs):
        ids = set(points_selector.get("points", []))
        before = len(self._collections.get(collection_name, []))
        self._collections[collection_name] = [p for p in self._collections.get(collection_name, []) if p.get("id") not in ids]
        return SimpleNamespace(result=(len(self._collections[collection_name]) != before))


# ------------------------------
# Pytest fixtures
# ------------------------------

@pytest.fixture(scope="session")
def dummy_encoder() -> DummyEncoder:
    return DummyEncoder()


@pytest.fixture(scope="session", autouse=True)
def patch_backends(dummy_encoder: DummyEncoder):
    """Patch heavy dependencies with our fakes for every test (session-wide).

    We avoid function-scoped `monkeypatch` to keep scope consistent.

    - app.services.embeddings.get_encoder -> returns callable (wav, sr) -> np.ndarray (192)
    - app.services.embeddings.get_embedding_dim -> returns 192
    - app.services.qdrant_repo._client -> FakeQdrantClient
    """
    mp = pytest.MonkeyPatch()

    # Avoid loading real models
    mp.setenv("USE_ECAPA", "false")

    # Import targets after setting env
    from app.services import embeddings as _emb
    from app.services import qdrant_repo as _repo

    def _get_encoder():
        def _enc(wav, sr):
            return dummy_encoder.embed_vector(np.asarray(wav), int(sr))
        return _enc

    mp.setattr(_emb, "get_encoder", _get_encoder, raising=True)
    mp.setattr(_emb, "get_embedding_dim", lambda: 192, raising=True)

    fake = FakeQdrantClient(dim=192)
    mp.setattr(_repo, "_client", fake, raising=True)

    # Expose fake client for optional debugging via attribute on function
    patch_backends.fake_qdrant = fake

    try:
        yield
    finally:
        mp.undo()


@pytest.fixture(scope="session")
def app_instance():
    # Import after patching so app wires the fakes
    from app.main import APP

    # Minimal request metrics middleware for tests
    if SPEAKERID_REQUESTS_TOTAL is not None:
        @APP.middleware("http")
        async def _metrics_request_mw(request, call_next):
            import time
            start = time.perf_counter()
            response = await call_next(request)
            duration = time.perf_counter() - start
            try:
                # Use the correct label names for the real metrics module
                # REQUESTS uses: path, method, status
                # REQUEST_LATENCY uses: path, method
                path = request.url.path
                method = request.method
                status = str(response.status_code)
                SPEAKERID_REQUESTS_TOTAL.labels(path=path, method=method, status=status).inc()
                if SPEAKERID_REQUEST_LATENCY_SECONDS is not None:
                    SPEAKERID_REQUEST_LATENCY_SECONDS.labels(path=path, method=method).observe(duration)
            except Exception:
                pass
            return response

    # The identify endpoint now handles metrics internally via app.observability.metrics
    # No need to wrap it here anymore

    # If the app doesn't already expose /metrics, add a minimal Prometheus endpoint for tests.
    has_metrics = False
    try:
        # Starlette routes can be of different types; safest is to check 'path' attr.
        for r in APP.router.routes:
            if getattr(r, "path", None) == "/metrics":
                has_metrics = True
                break
    except Exception:
        has_metrics = False

    if not has_metrics:
        from fastapi import Response

        @APP.get("/metrics")
        def _metrics():
            if generate_latest is None:
                return Response("metrics not available", media_type="text/plain")
            payload = generate_latest()
            return Response(payload, media_type=CONTENT_TYPE_LATEST)

    return APP


@pytest.fixture()
def client(app_instance) -> TestClient:
    return TestClient(app_instance)


@pytest.fixture(scope="session")
def sine_wav_bytes() -> bytes:
    """Generate a small 0.5s 440Hz mono WAV @16kHz to keep tests fast."""
    sr = 16000
    dur = 0.5
    t = np.arange(int(sr * dur)) / sr
    x = (0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    # Write WAV (PCM16)
    buf = io.BytesIO()
    # Minimal manual WAV header to avoid extra deps
    def _write(fmt: str, *vals):
        buf.write(struct.pack(fmt, *vals))

    data = (x * 32767).astype(np.int16).tobytes()
    # RIFF header
    buf.write(b"RIFF")
    _write("<I", 36 + len(data))
    buf.write(b"WAVE")
    # fmt chunk
    buf.write(b"fmt ")
    _write("<I", 16)  # PCM chunk size
    _write("<H", 1)   # PCM format
    _write("<H", 1)   # channels
    _write("<I", sr)  # sample rate
    _write("<I", sr * 2)  # byte rate
    _write("<H", 2)   # block align
    _write("<H", 16)  # bits per sample
    # data chunk
    buf.write(b"data")
    _write("<I", len(data))
    buf.write(data)

    return buf.getvalue()
