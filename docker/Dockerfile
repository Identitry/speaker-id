FROM python:3.11-slim as builder

# Install build dependencies (minimal set)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get autoremove -y \
    && apt-get clean

WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock* /app/

# Install poetry and dependencies
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root --no-interaction --no-ansi --only main

# Pre-download Resemblyzer model to avoid first-request delay
RUN python -c "from resemblyzer import VoiceEncoder; VoiceEncoder()" && \
    echo "Model cache created at:" && \
    find /root -name "*.pt" -o -name "*.pth" 2>/dev/null || echo "No .pt files found"

# Final stage - use distroless-style minimal image
FROM python:3.11-slim

# Install only essential runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /tmp/* /var/tmp/* \
    && find /usr/local -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Remove unnecessary files from Python packages to reduce image size
RUN find /usr/local/lib/python3.11/site-packages -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.11/site-packages -type d -name "test" -exec rm -rf {} + 2>/dev/null || true && \
    find /usr/local/lib/python3.11/site-packages -name "*.pyc" -delete && \
    find /usr/local/lib/python3.11/site-packages -name "*.pyo" -delete && \
    find /usr/local/lib/python3.11/site-packages -name "*.dist-info" -type d -exec sh -c 'rm -rf "$1"/RECORD "$1"/WHEEL' _ {} \; 2>/dev/null || true

# Copy application code
COPY app /app/app

# Compile Python bytecode for faster startup
RUN python -m compileall -q /app/app

# Environment variables
ENV TORCH_HOME=/root/.torch \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "-m", "uvicorn", "app.main:APP", "--host", "0.0.0.0", "--port", "8080"]
