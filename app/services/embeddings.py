"""Audio embedding backend for the speaker-id service.

This module turns raw audio bytes (e.g., a short WAV/MP3 clip) into a fixed-size
vector embedding suitable for speaker identification.

Two interchangeable backends are supported:
- **Resemblyzer (default)**: lightweight, fast, 256‑D embeddings.
- **ECAPA‑TDNN (SpeechBrain)**: higher accuracy/robustness, slightly heavier.

Backend is selected at process start from settings (supports both
`settings.USE_ECAPA` and `settings.use_ecapa`).

Design goals
------------
- Keep a single encoder instance per process for performance (warm model once).
- Accept arbitrary PCM formats; normalize to **mono 16 kHz float32**.
- Return `np.ndarray` of dtype float32 to match Qdrant expectations.
"""
from __future__ import annotations

import io
from typing import Optional

import numpy as np
import soundfile as sf

from app.core.config import settings

# Target sample rate for all embeddings. Most speaker models are trained at 16 kHz.
SR: int = 16000

# --- Backend selection (singleton encoder per process) -----------------------
# Be tolerant to either `USE_ECAPA` or `use_ecapa` on the settings object.
USE_ECAPA: bool = bool(getattr(settings, "USE_ECAPA", getattr(settings, "use_ecapa", False)))

if USE_ECAPA:
    # SpeechBrain ECAPA-TDNN pretrained on VoxCeleb.
    # Runs fine on CPU for short clips; expect slightly higher latency than
    # Resemblyzer but improved discrimination in noisy conditions.
    from speechbrain.pretrained import EncoderClassifier  # type: ignore

    _ecapa = EncoderClassifier.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        run_opts={"device": "cpu"},  # force CPU; adjust if you have GPU
    )
else:
    # Resemblyzer VoiceEncoder: small, fast, widely used for speaker embeddings.
    from resemblyzer import VoiceEncoder  # type: ignore

    _enc = VoiceEncoder()


# --- Embedding dimension helper ---------------------------------------------

def get_embedding_dim() -> int:
    """Return the dimensionality of the active embedding backend.

    Resemblyzer yields 256-D embeddings. ECAPA (SpeechBrain spkrec-ecapa-voxceleb)
    yields 192-D embeddings. Keeping Qdrant collection dimensions in sync with
    the chosen backend avoids server-side 500 errors.
    """
    return 192 if USE_ECAPA else 256


# --- Audio normalization helpers --------------------------------------------

def _wav_to_mono16k(data: bytes) -> np.ndarray:
    """Decode audio bytes to mono 16 kHz float32 waveform.

    Parameters
    ----------
    data : bytes
        Raw bytes from an uploaded audio file. `soundfile` handles WAV/FLAC/OGG
        and more; for MP3 you typically need libsndfile with mpg123 support.

    Returns
    -------
    np.ndarray
        1‑D float32 numpy array sampled at 16 kHz, amplitude in roughly [-1, 1].
    """
    import librosa  # imported lazily to keep import time lighter

    # Read with soundfile into float32. `always_2d=False` returns shape (N,) for mono
    # and (N, C) for multi-channel; we handle both.
    wav, sr = sf.read(io.BytesIO(data), dtype="float32", always_2d=False)

    # Downmix to mono if needed by averaging channels. This is simple and works
    # well for speech; if you need phase-aware mixing, handle upstream.
    if getattr(wav, "ndim", 1) > 1:
        wav = wav.mean(axis=1)

    # Resample to target SR if necessary. Librosa uses high-quality resampling
    # and returns float32.
    if sr != SR:
        wav = librosa.resample(wav, orig_sr=sr, target_sr=SR)

    return wav


# --- Public API --------------------------------------------------------------

def embed_audio(data: bytes) -> np.ndarray:
    """Embed an audio clip into a fixed-size float32 vector.

    Steps
    -----
    1) Decode + normalize to mono 16 kHz via :func:`_wav_to_mono16k`.
    2) Feed the waveform to the selected backend to produce an embedding.

    Parameters
    ----------
    data : bytes
        Raw audio file contents.

    Returns
    -------
    np.ndarray
        Embedding vector (float32). For Resemblyzer this is 256‑D. For ECAPA it
        is 192‑D for the default model.
    """
    wav = _wav_to_mono16k(data)

    if USE_ECAPA:
        # ECAPA expects a 2D tensor of shape (batch, time). We run on CPU.
        import torch  # imported lazily to avoid import cost when unused

        sig = torch.from_numpy(wav).unsqueeze(0)
        with torch.no_grad():
            emb = (
                _ecapa.encode_batch(sig)
                .squeeze(0)
                .squeeze(0)
                .numpy()
                .astype("float32")
            )
    else:
        # Resemblyzer's `embed_utterance` performs internal VAD/segmentation and
        # returns a single 256‑D vector for the whole utterance.
        emb = _enc.embed_utterance(wav).astype("float32")

    return emb
