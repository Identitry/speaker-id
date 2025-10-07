# Deployment Guide

Production deployment options for Speaker-ID.

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
    image: ghcr.io/YOUR-REPO/speaker-id:latest
    ports:
      - "8080:8080"
    environment:
      - QDRANT_URL=http://qdrant:6333
      - USE_ECAPA=false
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
  repository: ghcr.io/YOUR-REPO/speaker-id
  tag: latest

env:
  QDRANT_URL: "http://qdrant:6333"
  USE_ECAPA: "false"

resources:
  limits:
    cpu: "1000m"
    memory: "512Mi"
  requests:
    cpu: "500m"
    memory: "256Mi"
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
