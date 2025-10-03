import numpy as np
import soundfile as sf
import resampy

def basic_wav_stats(wav_path):
    """
    Get basic statistics of a WAV file: sample rate, number of channels, and duration in seconds.

    Parameters:
    wav_path (str): Path to the WAV file.

    Returns:
    tuple: (sample_rate (int), channels (int), duration (float))
    """
    with sf.SoundFile(wav_path) as f:
        sample_rate = f.samplerate
        channels = f.channels
        frames = len(f)
        duration = frames / sample_rate
    return sample_rate, channels, duration

def ensure_mono(waveform):
    """
    Convert a stereo waveform to mono by averaging channels if necessary.

    Parameters:
    waveform (np.ndarray): Audio waveform array, shape (samples,) or (samples, channels).

    Returns:
    np.ndarray: Mono waveform array, shape (samples,)
    """
    if waveform.ndim == 1:
        # Already mono
        return waveform
    elif waveform.ndim == 2:
        # Average across channels to get mono
        return np.mean(waveform, axis=1)
    else:
        raise ValueError("Waveform array has unsupported number of dimensions.")

def load_wav(wav_path, target_sr=16000):
    """
    Load a WAV file, convert to mono, and resample to target sample rate if necessary.

    Parameters:
    wav_path (str): Path to the WAV file.
    target_sr (int): Desired sample rate.

    Returns:
    tuple: (waveform (np.ndarray), sample_rate (int))
        waveform is a mono numpy array, sample_rate is the sampling rate after resampling.
    """
    waveform, sample_rate = sf.read(wav_path)
    # Convert to mono if necessary
    waveform = ensure_mono(waveform)
    # Resample if sample rate differs from target
    if sample_rate != target_sr:
        waveform = resampy.resample(waveform, sample_rate, target_sr)
        sample_rate = target_sr
    return waveform, sample_rate

def save_wav(waveform, wav_path, sample_rate):
    """
    Save a waveform numpy array to a WAV file.

    Parameters:
    waveform (np.ndarray): Mono waveform array to save.
    wav_path (str): Path where to save the WAV file.
    sample_rate (int): Sample rate for the saved WAV file.
    """
    # Ensure waveform is 1D numpy array
    if waveform.ndim != 1:
        raise ValueError("Only mono waveforms (1D numpy arrays) are supported for saving.")
    sf.write(wav_path, waveform, sample_rate)


# --- Runtime-normalized loaders (used by API endpoints) --------------------
from app.core.config import settings
import io


def load_wav_normalized_from_bytes(data: bytes) -> np.ndarray:
    """Load audio bytes and normalize channels + sample rate according to settings.

    Policy (from Settings):
    - If `force_mono` is True: always average to mono.
    - Else if stereo and `accept_stereo` is False: take left channel.
    - Else: average to mono (most speaker encoders expect mono).
    - Finally, resample to `sample_rate` if needed.
    """
    # Read as float32, always_2d=True to keep (frames, channels)
    with sf.SoundFile(io.BytesIO(data)) as f:
        wav = f.read(always_2d=True, dtype="float32")
        sr = f.samplerate

    # Channel policy
    if settings.force_mono:
        wav = wav.mean(axis=1)
    else:
        if wav.shape[1] == 1:
            wav = wav[:, 0]
        else:
            if not settings.accept_stereo:
                wav = wav[:, 0]  # left channel only
            else:
                # Most encoders expect mono; averaging preserves energy reasonably.
                wav = wav.mean(axis=1)

    # Resample if sample rate differs
    if sr != settings.sample_rate:
        wav = resampy.resample(wav, sr, settings.sample_rate)

    return wav.astype("float32")


def load_wav_file_with_settings(wav_path: str) -> tuple[np.ndarray, int]:
    """Load a WAV file from path and apply the same normalization policy
    as `load_wav_normalized_from_bytes`. Returns (waveform, sample_rate).
    """
    with sf.SoundFile(wav_path) as f:
        wav = f.read(always_2d=True, dtype="float32")
        sr = f.samplerate

    if settings.force_mono:
        wav = wav.mean(axis=1)
    else:
        if wav.shape[1] == 1:
            wav = wav[:, 0]
        else:
            if not settings.accept_stereo:
                wav = wav[:, 0]
            else:
                wav = wav.mean(axis=1)

    if sr != settings.sample_rate:
        wav = resampy.resample(wav, sr, settings.sample_rate)
        sr = settings.sample_rate

    return wav.astype("float32"), sr
