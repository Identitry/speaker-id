#!/usr/bin/env python3
"""
Slice WAV (or other audio) into fixed-length clips for benchmarking/enrollment.

This tool produces mono 16 kHz WAVs by default and saves slices like:
  input/foo.wav -> output/foo_000.wav, foo_001.wav, ...

Features
--------
- Input can be a single file or a directory tree (recursively).
- Output is a mirrored directory structure under --out.
- Resamples to 16 kHz mono, with optional RMS-based voice activity trimming.
- Fixed window length (--dur) and hop/stride (--hop) in seconds.
- Normalization options: peak or RMS target.

Examples
--------
  # Slice all WAVs in ./long_clips into 1.0 s non-overlapping chunks
  python scripts/slice_wavs.py --in long_clips --out data/test_wavs --dur 1.0 --hop 1.0

  # 1.5 s windows with 0.5 s hop (50% overlap), light RMS gate
  python scripts/slice_wavs.py --in speech.wav --out data/test_wavs --dur 1.5 --hop 0.5 --rms_gate -40
"""
from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import numpy as np
import soundfile as sf

SR = 16000  # target sample rate


@dataclass
class SliceSpec:
    dur: float  # seconds
    hop: float  # seconds
    rms_gate: float | None  # dBFS threshold (e.g., -40). None disables gating.
    norm: str | None  # one of {None, "peak", "rms"}
    rms_target: float  # dBFS target for RMS normalization


def find_audio_files(root: Path) -> List[Path]:
    """Find audio files recursively under `root` (wav/flac/ogg/mp3 if supported)."""
    exts = {".wav", ".flac", ".ogg", ".mp3", ".m4a"}
    if root.is_file():
        return [root]
    out: List[Path] = []
    for p in root.rglob("*"):
        if p.suffix.lower() in exts and p.is_file():
            out.append(p)
    if not out:
        raise SystemExit(f"No audio files found under: {root}")
    return out


def read_mono16k(path: Path) -> np.ndarray:
    """Load audio, downmix to mono, resample to 16 kHz float32 in [-1, 1]."""
    import librosa

    wav, sr = sf.read(path, dtype="float32", always_2d=False)
    if wav.ndim > 1:
        wav = wav.mean(axis=1)
    if sr != SR:
        wav = librosa.resample(wav, orig_sr=sr, target_sr=SR)
    return wav.astype(np.float32, copy=False)


def dbfs(x: np.ndarray) -> float:
    """Return RMS level in dBFS (0 dBFS corresponds to |x|==1 peak)."""
    rms = np.sqrt(np.mean(np.square(x), dtype=np.float64)) + 1e-12
    return 20.0 * math.log10(rms)


def apply_rms_gate(x: np.ndarray, gate_dbfs: float) -> np.ndarray:
    """Zero out the slice if its RMS is below `gate_dbfs` (simple VAD)."""
    if dbfs(x) < gate_dbfs:
        return np.zeros_like(x)
    return x


def normalize(x: np.ndarray, mode: str | None, rms_target_dbfs: float) -> np.ndarray:
    """Normalize audio by peak or RMS. Returns a new array (no in-place writes)."""
    if mode is None:
        return x
    y = x.astype(np.float32, copy=True)
    if mode == "peak":
        peak = float(np.max(np.abs(y)) + 1e-9)
        return (y / peak).clip(-1.0, 1.0)
    if mode == "rms":
        current = dbfs(y)
        gain_db = rms_target_dbfs - current
        gain = 10 ** (gain_db / 20.0)
        y *= gain
        return np.clip(y, -1.0, 1.0)
    raise ValueError("norm must be one of {None, 'peak', 'rms'}")


def slice_signal(x: np.ndarray, spec: SliceSpec) -> Iterable[np.ndarray]:
    """Yield fixed-length windows from `x` using seconds-based spec."""
    n_win = int(round(spec.dur * SR))
    n_hop = int(round(spec.hop * SR))
    if n_win <= 0 or n_hop <= 0:
        raise ValueError("dur and hop must be > 0")
    for start in range(0, max(0, len(x) - n_win + 1), n_hop):
        seg = x[start : start + n_win]
        if spec.rms_gate is not None:
            seg = apply_rms_gate(seg, spec.rms_gate)
        seg = normalize(seg, spec.norm, spec.rms_target)
        yield seg


def write_wav(path: Path, x: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, x, SR, subtype="PCM_16")


def rel_out_path(infile: Path, in_root: Path, out_root: Path, idx: int) -> Path:
    stem = infile.stem
    rel = infile.parent.relative_to(in_root) if in_root.is_dir() else Path(".")
    return out_root / rel / f"{stem}_{idx:03d}.wav"


def process_file(path: Path, in_root: Path, out_root: Path, spec: SliceSpec) -> int:
    x = read_mono16k(path)
    count = 0
    for i, seg in enumerate(slice_signal(x, spec)):
        out_path = rel_out_path(path, in_root, out_root, i)
        write_wav(out_path, seg)
        count += 1
    return count


def main() -> int:
    ap = argparse.ArgumentParser(description="Slice audio into fixed-length WAV clips")
    ap.add_argument("--in", dest="inp", required=True, help="Input file or directory")
    ap.add_argument("--out", dest="out", required=True, help="Output directory root")
    ap.add_argument("--dur", type=float, default=1.0, help="Window length in seconds (default 1.0)")
    ap.add_argument("--hop", type=float, default=1.0, help="Hop/stride in seconds (default 1.0)")
    ap.add_argument("--rms_gate", type=float, default=None, help="RMS gate in dBFS (e.g., -40). Below this, slice is zeroed")
    ap.add_argument("--norm", choices=["peak", "rms", "none"], default="none", help="Normalization mode")
    ap.add_argument("--rms_target", type=float, default=-20.0, help="RMS target in dBFS when --norm rms (default -20 dBFS)")
    args = ap.parse_args()

    spec = SliceSpec(
        dur=args.dur,
        hop=args.hop,
        rms_gate=args.rms_gate,
        norm=(None if args.norm == "none" else args.norm),
        rms_target=args.rms_target,
    )

    in_path = Path(args.inp).expanduser().resolve()
    out_root = Path(args.out).expanduser().resolve()

    files = find_audio_files(in_path)
    total_slices = 0
    for f in files:
        in_root = in_path if in_path.is_dir() else f.parent
        n = process_file(f, in_root, out_root, spec)
        total_slices += n
        print(f"Wrote {n:4d} slices from {f}")

    print(f"✅ Done. Total slices: {total_slices}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
