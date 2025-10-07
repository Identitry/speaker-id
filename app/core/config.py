"""Application configuration for the speaker-id service.

Configuration values are read once at process startup from environment
variables. They are stored in a simple `Settings` object that can be
imported anywhere in the app.

Notes
-----
- All values are read eagerly at import time. If you change environment
  variables after startup, you must restart the process.
- Types are parsed from strings: ports/ints, floats, booleans.
"""

import os


class Settings:
    """Central configuration object populated from environment variables."""

    # Host/port where FastAPI should bind.
    host: str = os.getenv("APP_HOST", "0.0.0.0")
    port: int = int(os.getenv("APP_PORT", "8080"))

    # Qdrant connection URL.
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")

    # Sampling settings.
    sample_rate: int = int(os.getenv("SAMPLE_RATE", "16000"))
    force_mono: bool = os.getenv("FORCE_MONO", "true").lower() == "true"
    accept_stereo: bool = os.getenv("ACCEPT_STEREO", "true").lower() == "true"

    # Identification settings.
    default_threshold: float = float(os.getenv("DEFAULT_THRESHOLD", "0.82"))
    topk: int = int(os.getenv("TOPK", "5"))
    use_ecapa: bool = os.getenv("USE_ECAPA", "false").lower() == "true"

    # Audio preprocessing settings
    # Enable advanced audio enhancement (VAD, normalization, pre-emphasis) for better confidence
    audio_enhancement: bool = os.getenv("AUDIO_ENHANCEMENT", "true").lower() == "true"
    # Select best speech segment (most energetic 3 seconds) from longer recordings
    select_best_segment: bool = os.getenv("SELECT_BEST_SEGMENT", "true").lower() == "true"
    # Minimum audio duration in seconds (after VAD trimming)
    min_audio_duration: float = float(os.getenv("MIN_AUDIO_DURATION", "1.0"))

    # Score calibration settings
    # Enable score calibration to improve discrimination between matches
    score_calibration: bool = os.getenv("SCORE_CALIBRATION", "true").lower() == "true"


    # Logging verbosity for the service (DEBUG/INFO/WARNING/ERROR).
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Prometheus metrics settings
    metrics_enabled: bool = os.getenv("METRICS_ENABLED", "true").lower() == "true"
    metrics_path: str = os.getenv("METRICS_PATH", "/metrics")


# Instantiate a single shared settings object for import across modules.
settings = Settings()
