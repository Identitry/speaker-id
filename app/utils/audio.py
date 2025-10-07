import numpy as np
import soundfile as sf
import resampy
from scipy.signal import lfilter


def apply_preemphasis(wav: np.ndarray, coef: float = 0.97) -> np.ndarray:
    """Apply pre-emphasis filter to boost high frequencies.

    This helps the model focus on higher frequency components which are
    important for speaker characteristics.

    Parameters
    ----------
    wav : np.ndarray
        Input waveform
    coef : float
        Pre-emphasis coefficient (typically 0.95-0.97)

    Returns
    -------
    np.ndarray
        Pre-emphasized waveform
    """
    return lfilter([1, -coef], [1], wav)


def normalize_audio(wav: np.ndarray, target_level: float = 0.9) -> np.ndarray:
    """Normalize audio to a target peak level.

    Ensures consistent volume across all recordings, which improves
    embedding quality and similarity scores.

    Parameters
    ----------
    wav : np.ndarray
        Input waveform
    target_level : float
        Target peak amplitude (0-1), default 0.9 to avoid clipping

    Returns
    -------
    np.ndarray
        Normalized waveform
    """
    peak = np.abs(wav).max()
    if peak > 0:
        wav = wav * (target_level / peak)
    return wav


def trim_silence(wav: np.ndarray, sr: int, top_db: int = 30, frame_length: int = 2048, hop_length: int = 512) -> np.ndarray:
    """Remove leading and trailing silence from audio.

    Uses energy-based voice activity detection to remove non-speech segments.
    This helps the model focus on actual speech content.

    Parameters
    ----------
    wav : np.ndarray
        Input waveform
    sr : int
        Sample rate
    top_db : int
        Threshold in dB below peak to consider as silence
    frame_length : int
        Frame size for energy calculation
    hop_length : int
        Hop size between frames

    Returns
    -------
    np.ndarray
        Trimmed waveform
    """
    # Calculate energy in dB for each frame
    energy = np.array([
        10 * np.log10(np.sum(wav[i:i+frame_length]**2) + 1e-10)
        for i in range(0, len(wav) - frame_length, hop_length)
    ])

    # Find threshold
    peak_energy = energy.max()
    threshold = peak_energy - top_db

    # Find first and last frames above threshold
    above_threshold = np.where(energy > threshold)[0]

    if len(above_threshold) == 0:
        # No speech detected, return original
        return wav

    start_frame = above_threshold[0]
    end_frame = above_threshold[-1]

    start_sample = start_frame * hop_length
    end_sample = min((end_frame + 1) * hop_length + frame_length, len(wav))

    return wav[start_sample:end_sample]


def select_best_speech_segment(wav: np.ndarray, sr: int, target_duration: float = 3.0) -> np.ndarray:
    """Select the most energetic speech segment of specified duration.

    This helps focus on the clearest, most informative part of the audio.
    Particularly useful when audio contains pauses, breaths, or varying quality.

    Parameters
    ----------
    wav : np.ndarray
        Input waveform (should be after VAD/trimming)
    sr : int
        Sample rate
    target_duration : float
        Target duration in seconds (default 3.0)

    Returns
    -------
    np.ndarray
        Best segment of audio
    """
    target_samples = int(target_duration * sr)

    # If audio is shorter than target, return as-is
    if len(wav) <= target_samples:
        return wav

    # Calculate RMS energy for overlapping windows
    hop_length = sr // 4  # 250ms hop
    window_length = target_samples

    best_energy = -np.inf
    best_start = 0

    for start in range(0, len(wav) - window_length, hop_length):
        segment = wav[start:start + window_length]
        energy = np.sqrt(np.mean(segment ** 2))  # RMS energy

        if energy > best_energy:
            best_energy = energy
            best_start = start

    return wav[best_start:best_start + window_length]


def validate_audio_duration(wav: np.ndarray, sr: int, min_duration: float = 1.0) -> bool:
    """Check if audio meets minimum duration requirement.

    Parameters
    ----------
    wav : np.ndarray
        Input waveform
    sr : int
        Sample rate
    min_duration : float
        Minimum required duration in seconds

    Returns
    -------
    bool
        True if audio is long enough
    """
    duration = len(wav) / sr
    return duration >= min_duration


def enhance_audio_for_speaker_recognition(wav: np.ndarray, sr: int, select_best_segment: bool = True) -> np.ndarray:
    """Apply full audio enhancement pipeline for speaker recognition.

    This is the main preprocessing function that should be called before
    generating embeddings. It applies:
    1. Silence trimming (removes non-speech)
    2. Best segment selection (uses most energetic/clear 3 seconds)
    3. Normalization (consistent volume)
    4. Pre-emphasis (boosts high frequencies)

    Parameters
    ----------
    wav : np.ndarray
        Input waveform
    sr : int
        Sample rate
    select_best_segment : bool
        If True, select the best 3-second segment based on energy

    Returns
    -------
    np.ndarray
        Enhanced waveform ready for embedding
    """
    # Step 1: Remove silence
    wav = trim_silence(wav, sr)

    # Validate minimum duration
    if not validate_audio_duration(wav, sr, min_duration=1.0):
        # Too short after trimming - return original with basic processing
        wav = normalize_audio(wav)
        wav = apply_preemphasis(wav)
        return wav

    # Step 2: Select best segment (optional, helps with long/noisy recordings)
    if select_best_segment and len(wav) / sr > 3.5:
        wav = select_best_speech_segment(wav, sr, target_duration=3.0)

    # Step 3: Normalize volume
    wav = normalize_audio(wav)

    # Step 4: Apply pre-emphasis
    wav = apply_preemphasis(wav)

    return wav


# Helper function to centralize channel and sample rate policy based on settings
def _apply_channel_and_sr_policy(wav: np.ndarray, sr: int) -> tuple[np.ndarray, int]:
    """
    Apply channel and sample rate normalization policy based on global settings.

    Ensures waveform is mono or stereo as per settings:
    - If force_mono is True, average all channels to mono.
    - Else if single channel, squeeze to 1D.
    - Else if stereo not accepted, take left channel only.
    - Else (stereo accepted), still average to mono because most speaker encoders expect mono.
    Resamples waveform if sample rate differs from settings.sample_rate.
    """
    from app.core.config import settings

    if wav.ndim == 1:
        wav = wav[:, None]  # reshape to (N,1) for consistent logic

    if settings.force_mono:
        wav = wav.mean(axis=1)
    else:
        if wav.shape[1] == 1:
            wav = wav[:, 0]
        else:
            if not settings.accept_stereo:
                wav = wav[:, 0]  # left channel only
            else:
                # Most speaker encoders expect mono; averaging preserves energy reasonably.
                wav = wav.mean(axis=1)

    if sr != settings.sample_rate:
        wav = resampy.resample(wav, sr, settings.sample_rate)
        sr = settings.sample_rate

    return wav.astype("float32"), sr

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
    return waveform.astype("float32"), sample_rate

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
    # Ensure values are in [-1.0, 1.0] and dtype float32 before writing
    waveform = np.asarray(waveform, dtype="float32")
    waveform = np.clip(waveform, -1.0, 1.0)
    sf.write(wav_path, waveform, sample_rate)


# --- Runtime-normalized loaders (used by API endpoints) --------------------
from app.core.config import settings
import io


def load_wav_normalized_from_bytes(data: bytes, enhance: bool = None) -> np.ndarray:
    """Load audio bytes and normalize channels + sample rate according to settings.

    Uses centralized policy function to handle mono/stereo and resampling.
    Returns mono waveform as float32 numpy array.

    Parameters
    ----------
    data : bytes
        Audio file data
    enhance : bool, optional
        If True, apply audio enhancement (VAD, normalization, pre-emphasis).
        If None (default), uses settings.audio_enhancement

    Returns
    -------
    np.ndarray
        Processed audio waveform
    """
    if enhance is None:
        enhance = settings.audio_enhancement

    with sf.SoundFile(io.BytesIO(data)) as f:
        wav = f.read(always_2d=True, dtype="float32")
        sr = f.samplerate

    wav, sr = _apply_channel_and_sr_policy(wav, sr)

    if enhance:
        wav = enhance_audio_for_speaker_recognition(
            wav, sr,
            select_best_segment=settings.select_best_segment
        )

    return wav


def load_wav_file_with_settings(wav_path: str, enhance: bool = None) -> tuple[np.ndarray, int]:
    """Load a WAV file from path and apply the same normalization policy
    as `load_wav_normalized_from_bytes`. Returns (waveform, sample_rate).

    Parameters
    ----------
    wav_path : str
        Path to audio file
    enhance : bool, optional
        If True, apply audio enhancement (VAD, normalization, pre-emphasis).
        If None (default), uses settings.audio_enhancement

    Returns
    -------
    tuple[np.ndarray, int]
        Processed waveform and sample rate
    """
    if enhance is None:
        enhance = settings.audio_enhancement

    with sf.SoundFile(wav_path) as f:
        wav = f.read(always_2d=True, dtype="float32")
        sr = f.samplerate

    wav, sr = _apply_channel_and_sr_policy(wav, sr)

    if enhance:
        wav = enhance_audio_for_speaker_recognition(
            wav, sr,
            select_best_segment=settings.select_best_segment
        )

    return wav, sr
