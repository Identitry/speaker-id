

import pytest


def _wav_file(sine_wav_bytes):
    return {"file": ("sample.wav", sine_wav_bytes, "audio/wav")}


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_identify_unknown_before_enroll(client, sine_wav_bytes):
    # With an empty index, identification should return unknown
    r = client.post("/api/identify?threshold=0.8", files=_wav_file(sine_wav_bytes))
    assert r.status_code == 200
    body = r.json()
    assert body["speaker"] == "unknown"
    assert 0.0 <= body["confidence"] <= 1.0


def test_enroll_then_identify(client, sine_wav_bytes):
    # Enroll a voice sample
    r = client.post("/api/enroll?name=Henrik", files=_wav_file(sine_wav_bytes))
    assert r.status_code == 200
    assert r.json().get("ok") is True

    # Identify the same sample and expect a match
    r = client.post("/api/identify?threshold=0.5", files=_wav_file(sine_wav_bytes))
    assert r.status_code == 200
    body = r.json()
    assert body["speaker"] == "Henrik"
    assert body["confidence"] >= 0.5
    assert body["topN"] and body["topN"][0]["name"] == "Henrik"


def test_profiles_lists_enrolled(client, sine_wav_bytes):
    # Ensure profile exists from previous test or enroll anew
    client.post("/api/enroll?name=Henrik", files=_wav_file(sine_wav_bytes))

    r = client.get("/api/profiles")
    assert r.status_code == 200
    body = r.json()
    assert "profiles" in body
    assert "Henrik" in body["profiles"]


def test_rebuild_centroids_endpoint(client, sine_wav_bytes):
    # Enroll a couple of samples to trigger centroid work
    client.post("/api/enroll?name=Henrik", files=_wav_file(sine_wav_bytes))

    r = client.post("/api/rebuild_centroids")
    assert r.status_code == 200
    body = r.json()
    # We at least expect ok True and updated >= 0 (fake client may return 1)
    assert body.get("ok") is True
    assert isinstance(body.get("updated"), int)
