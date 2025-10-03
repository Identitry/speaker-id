# speaker-id

Speaker identification service for Home Assistant & edge setups.
- Embeddings: Resemblyzer (256) or ECAPA (192) via SpeechBrain
- Vector DB: Qdrant
- API: FastAPI
- Optional Web UI for enrollment/testing

## Quickstart (local)
```bash
docker run -p 6333:6333 qdrant/qdrant
USE_ECAPA=true SAMPLE_RATE=16000 FORCE_MONO=true ACCEPT_STEREO=true \
poetry run uvicorn app.main:APP --port 8080

# Speaker-ID

A lightweight **speaker identification service** designed for **Home Assistant** and **edge deployments**.
It provides enrollment and identification APIs powered by deep learning embeddings and a vector database.

---

## ✨ Features

- **Embeddings**
  - [Resemblyzer](https://github.com/resemble-ai/Resemblyzer) (256-dim)
  - [ECAPA-TDNN (SpeechBrain)](https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb) (192-dim)

- **Vector Database**: [Qdrant](https://qdrant.tech/) for efficient similarity search

- **API**: [FastAPI](https://fastapi.tiangolo.com/) with automatic OpenAPI/Swagger docs

- **Audio handling**
  - Configurable sample rate (e.g. 16kHz)
  - Mono/stereo handling via environment variables

- **Web UI** (optional)
  - Enroll speakers
  - Run test identifications
  - Switch between embedding backends

- **Deployment Ready**
  - Docker image
  - Example Helm chart (bjw-s App-Template) for Kubernetes
  - Designed for integration with **Home Assistant**

---

## 🏗️ Architecture

```
 ┌───────────────┐       ┌───────────────┐
 │   Audio File   │       │   Microphone   │
 └───────┬───────┘       └───────────────┘
         │
         ▼
 ┌──────────────────────┐
 │   Embeddings Engine  │  ← Resemblyzer / ECAPA
 └─────────┬────────────┘
           │  vector
           ▼
 ┌──────────────────────┐
 │   Qdrant (Vectors)   │
 └─────────┬────────────┘
           │ search
           ▼
 ┌──────────────────────┐
 │ FastAPI Endpoints    │
 │  - /api/enroll       │
 │  - /api/identify     │
 │  - /api/rebuild      │
 └──────────────────────┘
```

---

## 🚀 Quickstart (Local)

1. Start Qdrant:
```bash
docker run -p 6333:6333 qdrant/qdrant
```

2. Start API service (with ECAPA, mono, 16kHz):
```bash
USE_ECAPA=true SAMPLE_RATE=16000 FORCE_MONO=true ACCEPT_STEREO=true \
poetry run uvicorn app.main:APP --port 8080
```

3. Test API:
```bash
curl -F "file=@myvoice.wav" "http://127.0.0.1:8080/api/enroll?name=Alice"
curl -F "file=@myvoice.wav" "http://127.0.0.1:8080/api/identify?threshold=0.82"
```

---

## ⚙️ Configuration

Environment variables:

| Variable       | Default  | Description                                  |
|----------------|----------|----------------------------------------------|
| `USE_ECAPA`    | `false`  | Use ECAPA instead of Resemblyzer embeddings |
| `SAMPLE_RATE`  | `16000`  | Target sample rate in Hz                     |
| `FORCE_MONO`   | `true`   | Force downmixing to mono                     |
| `ACCEPT_STEREO`| `true`   | Allow stereo input (will resample if needed) |

---

## 📊 API Endpoints

- `GET /health` → Service health check
- `POST /api/enroll?name=NAME` → Enroll a new speaker
- `POST /api/identify?threshold=X` → Identify speaker from audio
- `POST /api/rebuild_centroids` → Rebuild master profiles
- `GET /docs` → Swagger UI
- `GET /redoc` → ReDoc UI

---

## 🧪 Testing

Unit tests are under `/tests`. Run with:

```bash
poetry run pytest
```

---

## 📦 Deployment

### Docker
Build image:
```bash
docker build -t speaker-id .
```

Run:
```bash
docker run -p 8080:8080 --env USE_ECAPA=true speaker-id
```

### Kubernetes (Helm)
Example with bjw-s app-template coming soon.

---

## 📖 Roadmap

- [ ] Unit tests (pytest)
- [ ] Prometheus metrics endpoint
- [ ] Switch embeddings backend at runtime
- [ ] Polished Web UI (AI-assisted design)
- [ ] Home Assistant integration (custom component or addon)
- [ ] Helm chart (bjw-s App-Template)
- [ ] GitHub Actions CI/CD with Docker publishing

---

## 📜 License

[MIT](LICENSE) © 2025 Henrik Nilsson
