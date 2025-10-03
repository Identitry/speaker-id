"""Embedding backends for the speaker-id service.

This module provides a *single source of truth* for generating speaker embeddings
from a waveform. All decoding/resampling/channel handling should be done
*outside* this module (see `app.utils.audio`). Here we accept a NumPy waveform
(`float32`, mono preferred) plus its sample rate, and return a fixed-size
embedding vector.

Backends:
- Resemblyzer (default): 256-D embeddings
- ECAPA-TDNN (SpeechBrain): 192-D embeddings (enabled by USE_ECAPA)

Selection:
- Controlled by `settings.USE_ECAPA` (bool) or `settings.use_ecapa`.
- We keep exactly one backend instance per process (cached).
"""
from __future__ import annotations

from functools import lru_cache
from typing import Callable

import numpy as np

from app.core.config import settings

# --- Backend selection --------------------------------------------------------

# Be tolerant to either `USE_ECAPA` or `use_ecapa` attribute on settings.
USE_ECAPA: bool = bool(getattr(settings, "USE_ECAPA", getattr(settings, "use_ecapa", False)))

# Canonical embedding dimensions per backend
_RESEMBLYZER_DIM = 256
_ECAPA_DIM = 192

# --- Public helpers -----------------------------------------------------------

def get_embedding_dim() -> int:
    """Return the embedding dimensionality for the active backend.

    Provided for other modules (e.g., Qdrant collection setup) that need to
    know the dimension without materializing the model.
    """
    return _ECAPA_DIM if USE_ECAPA else _RESEMBLYZER_DIM

# Backwards-compat alias (older code may import get_dim)
get_dim = get_embedding_dim


def get_encoder() -> Callable[[np.ndarray, int], np.ndarray]:
    """Return a callable `(wav: np.ndarray, sr: int) -> np.ndarray` that embeds audio.

    The callable expects:
    - `wav`: float32 NumPy array with shape (T,) for mono or (T, C) for multi-channel.
      If multi-channel is provided, we downmix to mono by averaging channels.
    - `sr`: sample rate in Hz. Preferably 16k (models are trained at 16k). If you
      pass other sample rates, ensure you resampled beforehand in `utils.audio`.
    """
    if USE_ECAPA:
        model = _get_ecapa()

        def _encode(wav: np.ndarray, sr: int) -> np.ndarray:  # noqa: ARG001 - sr kept for API symmetry
            # Defensive normalization: shape -> (T,)
            if wav.ndim == 2:
                wav_mono = wav.mean(axis=1).astype("float32", copy=False)
            else:
                wav_mono = wav.astype("float32", copy=False)

            # ECAPA expects a 2D tensor (batch, time). We run on CPU by default.
            import torch

            sig = torch.from_numpy(wav_mono).unsqueeze(0)
            with torch.no_grad():
                # encode_batch -> shape (batch, 1, dim). Squeeze to 1D.
                emb = (
                    model.encode_batch(sig)
                    .squeeze(0)
                    .squeeze(0)
                    .cpu()
                    .numpy()
                    .astype("float32", copy=False)
                )
            return emb

        return _encode

    # Resemblyzer
    encoder = _get_resemblyzer()

    def _encode(wav: np.ndarray, sr: int) -> np.ndarray:  # noqa: ARG001 - sr kept for API symmetry
        # Defensive normalization: shape -> (T,)
        if wav.ndim == 2:
            wav_mono = wav.mean(axis=1).astype("float32", copy=False)
        else:
            wav_mono = wav.astype("float32", copy=False)

        emb = encoder.embed_utterance(wav_mono).astype("float32", copy=False)
        return emb

    return _encode


def embed_wav(wav: np.ndarray, sr: int) -> np.ndarray:
    """Convenience wrapper to embed a waveform using the active backend."""
    encode = get_encoder()
    return encode(wav, sr)


# --- Backend factories (cached) ----------------------------------------------

@lru_cache(maxsize=1)
def _get_ecapa():
    """Load ECAPA-TDNN (SpeechBrain) once per process."""
    from speechbrain.pretrained import EncoderClassifier  # type: ignore

    # Force CPU by default; adjust `run_opts` if you have a GPU available.
    model = EncoderClassifier.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        run_opts={"device": "cpu"},
    )
    return model


@lru_cache(maxsize=1)
def _get_resemblyzer():
    """Load Resemblyzer VoiceEncoder once per process."""
    from resemblyzer import VoiceEncoder  # type: ignore

    return VoiceEncoder()


# Public API of this module
__all__ = [
    "get_encoder",
    "embed_wav",
    "get_embedding_dim",
    "get_dim",
]
