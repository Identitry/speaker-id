

"""
Timing utilities for profiling and logging execution durations.
"""

import time
import logging
from contextlib import contextmanager
from functools import wraps

logger = logging.getLogger("speaker-id")

@contextmanager
def time_block(label: str):
    """Context manager to measure execution time of a block.

    Example
    -------
    with time_block("embedding"):
        vec = encoder.encode(wav)
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = (time.perf_counter() - start) * 1000
        logger.info("%s took %.2f ms", label, elapsed)

def timeit(func):
    """Decorator to measure and log execution time of a function.

    Example
    -------
    @timeit
    def compute():
        ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        logger.info("%s took %.2f ms", func.__name__, elapsed)
        return result
    return wrapper
