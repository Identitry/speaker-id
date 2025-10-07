# Deployment Guide

Production deployment options for Speaker-ID.

---

## Docker Images

**Official Images**: Available on GitHub Container Registry (GHCR)

```bash
# Pull the latest image (includes both Resemblyzer and ECAPA models)
docker pull ghcr.io/identitry/speaker-id:latest
```

**Platforms**: linux/amd64, linux/arm64

**Tags**:
- `latest` - Latest stable build from main branch
- `v1.0.0` - Specific version tags
- `main-<commit-sha>` - Commit-specific builds

**Model Selection**:
- Default: Resemblyzer (faster, lower memory)
- Set `USE_ECAPA=true` for ECAPA-TDNN (more accurate)

**Automatic Publishing**:
Images are automatically built and published via GitHub Actions when code changes are pushed to the repository.

---

## Docker Compose (Recommended)

Easiest production deployment with automatic restarts and data persistence.

**docker-compose.yml**:
```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - ./qdrant_data:/qdrant/storage
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:6333/"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  speaker-id:
    image: ghcr.io/identitry/speaker-id:latest
    ports:
      - "8080:8080"
    environment:
      - QDRANT_URL=http://qdrant:6333
      - USE_ECAPA=false  # Set to true for ECAPA model
      - AUDIO_ENHANCEMENT=true
      - SCORE_CALIBRATION=true
      - LOG_LEVEL=INFO
    depends_on:
      qdrant:
        condition: service_healthy
    restart: unless-stopped
```

**Deploy**:
```bash
docker compose up -d
```

---

## Kubernetes with Helm

For large-scale deployments.

**values.yaml**:
```yaml
replicaCount: 2

image:
  repository: ghcr.io/identitry/speaker-id
  tag: latest

env:
  QDRANT_URL: "http://qdrant:6333"
  USE_ECAPA: "false"  # Set to "true" for ECAPA model
  AUDIO_ENHANCEMENT: "true"
  SCORE_CALIBRATION: "true"

resources:
  limits:
    cpu: "1000m"
    memory: "1Gi"  # Increase if using ECAPA
  requests:
    cpu: "500m"
    memory: "512Mi"
```

---

## Systemd Service

For bare-metal deployments.

```ini
[Unit]
Description=Speaker-ID Service
After=network.target

[Service]
Type=simple
User=speakerid
WorkingDirectory=/opt/speaker-id
ExecStart=/usr/bin/docker-compose up
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Monitoring

Use the `/metrics` endpoint with Prometheus:

```yaml
scrape_configs:
  - job_name: 'speaker-id'
    static_configs:
      - targets: ['localhost:8080']
```

---

For detailed architecture, see [Solution Details](solution_details.md).
