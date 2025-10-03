"""Logging configuration for the speaker-id service.

We configure a global logger at import time so that all modules can do:

    from app.core.logging import logger
    logger.info("...")

Notes
-----
- Logging level and format are set once, globally, using `basicConfig`.
- The level defaults to INFO here; you can override it with the `LOG_LEVEL`
  environment variable if you want more/less verbosity (see config.py).
- Log format includes timestamp, level, logger name, and message.
"""

import logging

# Configure the root logger.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

# Create a module-level logger with a fixed name for consistency.
logger = logging.getLogger("speaker-id")
