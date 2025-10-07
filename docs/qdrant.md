# Qdrant Database Guide

Understanding and managing the Qdrant vector database used by Speaker-ID.

---

## What is Qdrant?

Qdrant is a vector similarity search engine that stores and searches voice embeddings efficiently.

---

## Collections

Speaker-ID uses two collections:

### speakers_raw
- Stores every enrollment sample
- UUID-based IDs
- Used for auditing and rebuilding

### speakers_master
- Stores one centroid per speaker
- Deterministic IDs (hash of name)
- Used for fast identification

---

## Backup & Restore

**Backup**:
```bash
docker compose stop qdrant
tar -czf qdrant-backup-$(date +%Y%m%d).tar.gz ./qdrant_data
docker compose start qdrant
```

**Restore**:
```bash
docker compose stop qdrant
tar -xzf qdrant-backup-20250107.tar.gz
docker compose start qdrant
```

---

## Web UI

Access Qdrant dashboard at: http://localhost:6333/dashboard

Features:
- Browse collections
- View vectors
- Manual queries
- Collection statistics

---

## Maintenance

**Rebuild all centroids**:
```bash
curl -X POST http://localhost:8080/api/rebuild_centroids
```

**Check collection stats**:
```bash
curl http://localhost:6333/collections/speakers_master
```

---

For more details, see [Solution Details](solution_details.md#two-tier-storage-pattern).
