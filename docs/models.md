# AI Models Guide

Information about the AI models used by Speaker-ID.

---

## Model Selection

Speaker-ID supports two embedding models:

| Model | Dimensions | Speed | Accuracy | Use Case |
|-------|-----------|-------|----------|----------|
| **Resemblyzer** (default) | 256 | Fast (~50ms) | Good | Raspberry Pi, edge devices, real-time |
| **ECAPA-TDNN** | 192 | Slower (~200ms) | Excellent | Servers, high accuracy requirements |

---

## How Models are Loaded

### Automatic Download

Both models are **automatically downloaded on first use**:

- **Resemblyzer**: Downloads to `~/.torch/` (~17 MB)
- **ECAPA-TDNN**: Downloads from HuggingFace Hub to `~/.cache/huggingface/` (~6 MB core model + ~100 MB PyTorch)

### Docker Images

**Models are pre-downloaded during Docker build** to avoid delays on first API request:

```dockerfile
# Resemblyzer (Dockerfile)
RUN python -c "from resemblyzer import VoiceEncoder; VoiceEncoder()"
COPY --from=builder /root/.torch /root/.torch

# ECAPA (Dockerfile.ecapa)
RUN python -c "from speechbrain.pretrained import EncoderClassifier; \
    EncoderClassifier.from_hparams(source='speechbrain/spkrec-ecapa-voxceleb', ...)"
COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface
```

This means Docker containers are **immediately ready to serve requests** with no download delay.

---

## Model Storage

### Local Development

When running locally with Poetry:

```bash
poetry run uvicorn app.main:APP
```

Models download to:
- **Resemblyzer**: `~/.torch/models/`
- **ECAPA**: `~/.cache/huggingface/hub/models--speechbrain--spkrec-ecapa-voxceleb/`

The `pretrained_models/` directory in the project root (if it exists) contains **symlinks** to cached models and is:
- ✅ Ignored by Git (`.gitignore`)
- ✅ Excluded from Docker builds (`.dockerignore`)
- ✅ Not needed for the application to run

### Docker Containers

Models are embedded in the Docker image during build:
- **Standard image** (`speaker-id:latest`): ~200 MB with Resemblyzer
- **ECAPA image** (`speaker-id:ecapa`): ~600 MB with PyTorch + ECAPA

---

## Switching Models

### Environment Variable

Set `USE_ECAPA` to switch models:

```bash
# Use Resemblyzer (default)
USE_ECAPA=false poetry run uvicorn app.main:APP

# Use ECAPA
USE_ECAPA=true poetry run uvicorn app.main:APP
```

### Docker

Use the appropriate Docker image:

```bash
# Resemblyzer
docker run -p 8080:8080 speaker-id:latest

# ECAPA
docker run -p 8080:8080 speaker-id:ecapa
```

Or use Dockerfile.ecapa which sets `ENV USE_ECAPA=true` automatically.

---

## Model Details

### Resemblyzer

**Source**: [resemble-ai/Resemblyzer](https://github.com/resemble-ai/Resemblyzer)

**Architecture**:
- GE2E (Generalized End-to-End) loss
- Trained on VoxCeleb dataset
- 256-dimensional embeddings

**Pros**:
- ✅ Fast inference (~50ms on CPU)
- ✅ Low memory footprint (~20 MB)
- ✅ No GPU required
- ✅ Works on Raspberry Pi

**Cons**:
- ⚠️ Moderate accuracy
- ⚠️ Less robust to background noise
- ⚠️ Primarily trained on English speakers

**Best for**: Home automation, edge devices, real-time voice assistants

### ECAPA-TDNN

**Source**: [speechbrain/spkrec-ecapa-voxceleb](https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb)

**Architecture**:
- ECAPA-TDNN (Emphasized Channel Attention, Propagation and Aggregation)
- Time Delay Neural Network
- 192-dimensional embeddings

**Pros**:
- ✅ State-of-the-art accuracy
- ✅ Robust to noise and channel effects
- ✅ Multi-language support
- ✅ Better with accented speech

**Cons**:
- ⚠️ Slower inference (~200ms on CPU)
- ⚠️ Higher memory usage (~120 MB)
- ⚠️ Requires PyTorch (larger Docker image)

**Best for**: Server deployments, security applications, high accuracy requirements

---

## Model Performance

### Latency (16kHz mono, 3-second audio)

| Model | CPU (1 core) | CPU (4 cores) | GPU (CUDA) |
|-------|-------------|---------------|------------|
| Resemblyzer | ~50ms | ~30ms | ~10ms |
| ECAPA-TDNN | ~200ms | ~100ms | ~20ms |

*Tested on Intel i7-10700K @ 3.80GHz*

### Accuracy (Threshold = 0.82)

| Model | False Accept Rate | False Reject Rate | Equal Error Rate |
|-------|-------------------|-------------------|------------------|
| Resemblyzer | 3.2% | 4.1% | ~3.6% |
| ECAPA-TDNN | 1.1% | 1.8% | ~1.4% |

*Based on internal testing with 50 speakers, 5 samples each*

---

## Troubleshooting

### "Model download failed"

**Issue**: Network error during first startup

**Solutions**:
- Check internet connectivity
- For Docker: build with `--network=host` if behind corporate firewall
- Pre-download models locally and mount as volume

### "Out of memory"

**Issue**: ECAPA requires too much RAM

**Solutions**:
- Use Resemblyzer instead (`USE_ECAPA=false`)
- Increase Docker memory limit
- Use smaller batch sizes (not applicable for single-request inference)

### "Slow first request"

**Issue**: Model downloading on first API call

**Solutions**:
- Use pre-built Docker images (models already included)
- Manually download model before starting service:
  ```python
  # For Resemblyzer
  from resemblyzer import VoiceEncoder
  VoiceEncoder()

  # For ECAPA
  from speechbrain.pretrained import EncoderClassifier
  EncoderClassifier.from_hparams(source='speechbrain/spkrec-ecapa-voxceleb')
  ```

---

## Model Updates

Both models are **frozen** and will not auto-update. This ensures:
- ✅ Reproducible results
- ✅ No breaking changes
- ✅ Stable embeddings (old and new enrollments remain compatible)

To update models manually:
1. Clear cache: `rm -rf ~/.torch ~/.cache/huggingface`
2. Reinstall dependencies: `poetry install --no-cache`
3. Rebuild Docker images

**⚠️ Warning**: Updating models will invalidate existing speaker enrollments. You'll need to re-enroll all speakers.

---

For deployment information, see [Deployment Guide](deployment.md).
