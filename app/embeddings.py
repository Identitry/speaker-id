

"""
Unified embedding backend for speaker-id.

- If env USE_ECAPA=true  -> use SpeechBrain ECAPA (192-dim).
- Else                    -> use Resemblyzer (256-dim).

Public API:
    get_encoder() -> Encoder
    Encoder.embed_vector(wav: np.ndarray) -> np.ndarray
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Protocol

import numpy as np


class Encoder(Protocol):
    def embed_vector(self, wav: np.ndarray) -> np.ndarray: ...


class _ResemblyzerEncoder:
    def __init__(self) -> None:
        from resemblyzer import VoiceEncoder  # lazy import
        # Use default (pretrained) model; CPU works fine
        self._enc = VoiceEncoder()

    def embed_vector(self, wav: np.ndarray) -> np.ndarray:
        """
        wav: mono float32 waveform in range [-1, 1], sample rate ~16k (we resampled earlier).
        returns: 256-d float32 numpy array
        """
        vec = self._enc.embed_utterance(wav.astype(np.float32, copy=False))
        return np.asarray(vec, dtype=np.float32)


class _EcapaEncoder:
    def __init__(self) -> None:
        # Lazy import to keep import-time light
        import torch
        from speechbrain.inference.speaker import EncoderClassifier

        # Will download the model once into ~/.cache/huggingface/...
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            run_opts={"device": self._device},
            savedir="pretrained_models/EncoderClassifier",
        )

    def embed_vector(self, wav: np.ndarray) -> np.ndarray:
        """
        wav: mono float32 waveform in range [-1, 1], sample rate ~16k (we resampled earlier).
        returns: 192-d float32 numpy array
        """
        import torch

        # SpeechBrain expects batch x time
        wav_t = torch.from_numpy(wav.astype(np.float32, copy=False)).unsqueeze(0).to(self._model.device)
        with torch.no_grad():
            # Get embeddings: shape (1, 192)
            emb = self._model.encode_batch(wav_t).squeeze(0).squeeze(0).cpu().numpy()
        emb = emb.astype(np.float32, copy=False)
        # Unit-normalize for good cosine behavior
        norm = np.linalg.norm(emb) + 1e-12
        return (emb / norm).astype(np.float32)


@lru_cache(maxsize=1)
def get_encoder() -> Encoder:
    """Return a memoized encoder instance based on USE_ECAPA env."""
    use_ecapa = os.getenv("USE_ECAPA", "false").lower() in ("1", "true", "yes", "y")
    if use_ecapa:
        return _EcapaEncoder()
    return _ResemblyzerEncoder()
