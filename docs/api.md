# API Reference

Complete API documentation for the Speaker-ID service.

---

## Base URL

```
http://localhost:8080
```

Replace `localhost` with your server's IP address or hostname.

---

## Table of Contents

1. [Health & Status](#health--status)
2. [Speaker Enrollment](#speaker-enrollment)
3. [Speaker Identification](#speaker-identification)
4. [Speaker Management](#speaker-management)
5. [System Administration](#system-administration)
6. [Metrics & Monitoring](#metrics--monitoring)

---

## Health & Status

### GET /health

Check if the service is running.

**Request**:
```bash
curl http://localhost:8080/health
```

**Response** (200 OK):
```json
{
  "status": "ok"
}
```

**Use case**: Health checks in Docker, Kubernetes, load balancers.

---

## Speaker Enrollment

### POST /api/enroll

Enroll a new speaker or add samples to an existing speaker.

**Parameters**:
- `name` (query, required): Speaker name (string, 1-100 characters)
- `file` (form-data, required): Audio file (WAV, MP3, FLAC)

**Request Example**:
```bash
curl -X POST \
  "http://localhost:8080/api/enroll?name=Alice" \
  -F "file=@alice_voice.wav"
```

**Request with Python**:
```python
import requests

url = "http://localhost:8080/api/enroll"
files = {'file': open('alice_voice.wav', 'rb')}
params = {'name': 'Alice'}

response = requests.post(url, files=files, params=params)
print(response.json())
```

**Response** (200 OK):
```json
{
  "status": "enrolled",
  "name": "Alice",
  "samples": 1,
  "message": "Successfully enrolled sample for Alice"
}
```

**Error Responses**:

| Status | Reason | Solution |
|--------|--------|----------|
| 400 | Missing name parameter | Provide `?name=NAME` |
| 400 | Empty file | Upload valid audio file |
| 400 | Invalid audio format | Use WAV/MP3/FLAC |
| 500 | Embedding failed | Check audio quality |

**Best Practices**:
- Enroll 3-5 samples per speaker for best accuracy
- Use clear audio with minimal background noise
- 3-10 seconds of speech per sample
- Use natural speaking voice

**Audio Requirements**:
- **Format**: WAV (recommended), MP3, FLAC
- **Sample Rate**: Any (auto-converted to 16kHz)
- **Channels**: Mono preferred, stereo auto-converted
- **Duration**: 2-30 seconds recommended
- **File Size**: < 10 MB

---

## Speaker Identification

### POST /api/identify

Identify a speaker from an audio sample.

**Parameters**:
- `file` (form-data, required): Audio file to identify
- `threshold` (query, optional): Confidence threshold (0-1, default: 0.82)
- `topk` (query, optional): Number of candidates to return (default: 5)

**Request Example**:
```bash
curl -X POST \
  "http://localhost:8080/api/identify?threshold=0.82&topk=5" \
  -F "file=@unknown_voice.wav"
```

**Request with Python**:
```python
import requests

url = "http://localhost:8080/api/identify"
files = {'file': open('unknown_voice.wav', 'rb')}
params = {'threshold': 0.82, 'topk': 5}

response = requests.post(url, files=files, params=params)
result = response.json()

print(f"Speaker: {result['speaker']}")
print(f"Confidence: {result['confidence']:.2f}")
```

**Response** (200 OK) - Match Found:
```json
{
  "speaker": "Alice",
  "confidence": 0.91,
  "topN": [
    {"name": "Alice", "score": 0.91},
    {"name": "Bob", "score": 0.65},
    {"name": "Charlie", "score": 0.52}
  ]
}
```

**Response** (200 OK) - No Match:
```json
{
  "speaker": "unknown",
  "confidence": 0.0,
  "topN": []
}
```

**Response** (200 OK) - Below Threshold:
```json
{
  "speaker": "unknown",
  "confidence": 0.75,
  "topN": [
    {"name": "Alice", "score": 0.75}
  ]
}
```

**Response Fields**:
- `speaker`: Identified name or "unknown"
- `confidence`: Similarity score (0-1) of best match
- `topN`: List of top candidates with scores

**Threshold Guidelines**:

| Threshold | False Positives | False Negatives | Use Case |
|-----------|-----------------|-----------------|----------|
| 0.95 | Very Low | High | Security/authentication |
| 0.85 | Low | Moderate | Balanced (recommended) |
| 0.75 | Moderate | Low | Convenience/automation |
| 0.65 | High | Very Low | Maximum recall |

**Interpreting Confidence Scores**:
- **0.90+**: Very confident - almost certainly correct
- **0.80-0.89**: Confident - likely correct
- **0.70-0.79**: Moderate - possibly correct
- **< 0.70**: Low confidence - probably wrong

**Home Assistant Example**:
```yaml
rest_command:
  identify_speaker:
    url: "http://localhost:8080/api/identify?threshold=0.82"
    method: POST
    content_type: "multipart/form-data"
    payload: "{{ {'file': states('input_text.audio_path')} }}"

automation:
  - alias: "Voice Identification"
    trigger:
      platform: state
      entity_id: binary_sensor.microphone_active
      to: "on"
    action:
      - service: rest_command.identify_speaker
      - service: notify.mobile_app
        data:
          message: "Detected {{ speaker }} (confidence: {{ confidence }})"
```

---

## Speaker Management

### GET /api/profiles

List all enrolled speakers.

**Request**:
```bash
curl http://localhost:8080/api/profiles
```

**Response** (200 OK):
```json
{
  "profiles": ["Alice", "Bob", "Charlie"]
}
```

**Use case**: Display enrolled speakers in UI, check enrollment status.

### POST /api/reset

Delete all speakers and start fresh.

**Parameters**:
- `name` (query, optional): Delete specific speaker only
- `drop_all` (query, optional): Delete everything (default: false)

**Request - Delete Specific Speaker**:
```bash
curl -X POST "http://localhost:8080/api/reset?name=Alice"
```

**Request - Delete All**:
```bash
curl -X POST "http://localhost:8080/api/reset?drop_all=true"
```

**Response** (200 OK):
```json
{
  "status": "reset",
  "message": "Database reset successfully"
}
```

**⚠️ Warning**: This operation is irreversible! All voice data for the deleted speaker(s) will be permanently removed.

---

## System Administration

### POST /api/rebuild_centroids

Rebuild master profiles from raw enrollment data.

**When to use**:
- After enrolling many samples at once
- Periodic maintenance (weekly/monthly)
- If identification accuracy seems degraded

**Request**:
```bash
curl -X POST http://localhost:8080/api/rebuild_centroids
```

**Response** (200 OK):
```json
{
  "status": "rebuilt",
  "speakers_updated": 3,
  "message": "Successfully rebuilt centroids for 3 speakers"
}
```

**What it does**:
1. Fetches all raw enrollment samples for each speaker
2. Computes average (centroid) of all samples
3. Updates master collection with new centroids

**Performance**: Takes 1-2 seconds for 100 speakers.

### GET /api/config

Get current service configuration.

**Request**:
```bash
curl http://localhost:8080/api/config
```

**Response** (200 OK):
```json
{
  "model": "resemblyzer",
  "embedding_dim": 256,
  "sample_rate": 16000,
  "default_threshold": 0.82,
  "version": "1.0.0"
}
```

---

## Metrics & Monitoring

### GET /metrics

Prometheus metrics endpoint.

**Request**:
```bash
curl http://localhost:8080/metrics
```

**Response** (200 OK, text/plain):
```
# HELP speakerid_requests_total Total HTTP requests
# TYPE speakerid_requests_total counter
speakerid_requests_total{path="/api/identify",method="POST",status="200"} 1523.0

# HELP speakerid_identify_match_total Successful identifications
# TYPE speakerid_identify_match_total counter
speakerid_identify_match_total 892.0

# HELP speakerid_identify_match_by_speaker_total Per-speaker matches
# TYPE speakerid_identify_match_by_speaker_total counter
speakerid_identify_match_by_speaker_total{speaker="Alice"} 421.0
speakerid_identify_match_by_speaker_total{speaker="Bob"} 356.0

# HELP speakerid_request_latency_seconds Request latency
# TYPE speakerid_request_latency_seconds histogram
speakerid_request_latency_seconds_bucket{path="/api/identify",method="POST",le="0.1"} 892.0
speakerid_request_latency_seconds_bucket{path="/api/identify",method="POST",le="0.5"} 1503.0
```

**Metrics Provided**:
- `speakerid_requests_total`: Total HTTP requests by path/method/status
- `speakerid_identify_match_total`: Total successful identifications
- `speakerid_identify_match_by_speaker_total`: Per-speaker identification counts
- `speakerid_request_latency_seconds`: Request latency histogram
- `http_*`: Standard HTTP metrics from FastAPI instrumentator

**Grafana Dashboard Example**:
```
Rate of identification requests:
  rate(speakerid_identify_match_total[5m])

99th percentile latency:
  histogram_quantile(0.99,
    rate(speakerid_request_latency_seconds_bucket[5m]))

Most identified speaker:
  topk(5, speakerid_identify_match_by_speaker_total)
```

---

## Interactive Documentation

### Swagger UI

**URL**: http://localhost:8080/docs

Features:
- Interactive API testing
- Request/response examples
- Schema definitions
- Try-it-out functionality

### ReDoc

**URL**: http://localhost:8080/redoc

Features:
- Clean, readable documentation
- Searchable
- Code samples in multiple languages
- Download OpenAPI spec

---

## Error Handling

All errors follow the same format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common HTTP Status Codes**:

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Request completed successfully |
| 400 | Bad Request | Missing parameter, invalid audio |
| 404 | Not Found | Endpoint doesn't exist |
| 500 | Server Error | Internal error (check logs) |

**Error Examples**:

```json
// Missing required parameter
{
  "detail": "Missing required parameter: name"
}

// Invalid audio format
{
  "detail": "Unsupported or corrupt audio format"
}

// Empty audio file
{
  "detail": "Empty file upload"
}

// Embedding failed
{
  "detail": "Failed to compute embedding for audio"
}
```

---

## Rate Limiting

**Currently**: No rate limiting

**Recommendations** for production:
- Use reverse proxy (nginx, Traefik) with rate limiting
- Typical limits: 100 requests/minute per IP
- Monitor via Prometheus metrics

---

## CORS (Cross-Origin Requests)

**Currently**: CORS not enabled

**To enable** for web applications:
```python
# Add to app/main.py
from fastapi.middleware.cors import CORSMiddleware

APP.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Your frontend URL
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

---

## Code Examples

### Python (requests)

```python
import requests

# Enroll
def enroll_speaker(name, audio_file):
    url = "http://localhost:8080/api/enroll"
    files = {'file': open(audio_file, 'rb')}
    params = {'name': name}
    response = requests.post(url, files=files, params=params)
    return response.json()

# Identify
def identify_speaker(audio_file, threshold=0.82):
    url = "http://localhost:8080/api/identify"
    files = {'file': open(audio_file, 'rb')}
    params = {'threshold': threshold}
    response = requests.post(url, files=files, params=params)
    return response.json()

# Usage
result = enroll_speaker("Alice", "alice_sample1.wav")
print(result)

result = identify_speaker("unknown.wav")
print(f"Speaker: {result['speaker']}, Confidence: {result['confidence']}")
```

### JavaScript (fetch)

```javascript
// Enroll
async function enrollSpeaker(name, audioFile) {
  const formData = new FormData();
  formData.append('file', audioFile);

  const response = await fetch(`http://localhost:8080/api/enroll?name=${name}`, {
    method: 'POST',
    body: formData
  });

  return await response.json();
}

// Identify
async function identifySpeaker(audioFile, threshold = 0.82) {
  const formData = new FormData();
  formData.append('file', audioFile);

  const response = await fetch(`http://localhost:8080/api/identify?threshold=${threshold}`, {
    method: 'POST',
    body: formData
  });

  return await response.json();
}

// Usage
const file = document.getElementById('audioInput').files[0];
const result = await identifySpeaker(file);
console.log(`Speaker: ${result.speaker}, Confidence: ${result.confidence}`);
```

### cURL

```bash
# Enroll
curl -X POST \
  "http://localhost:8080/api/enroll?name=Alice" \
  -F "file=@alice_voice.wav"

# Identify
curl -X POST \
  "http://localhost:8080/api/identify?threshold=0.82" \
  -F "file=@unknown_voice.wav"

# List speakers
curl http://localhost:8080/api/profiles

# Get metrics
curl http://localhost:8080/metrics
```

---

## Troubleshooting API Issues

### "Empty file upload"
- Check file exists and has content
- Verify file path is correct
- Ensure proper permissions

### "Unsupported or corrupt audio format"
- Use WAV, MP3, or FLAC
- Try converting with `ffmpeg -i input.mp3 output.wav`
- Check file isn't corrupted

### "Failed to compute embedding"
- Audio might be too short (< 1 second)
- Audio might be silent or too quiet
- Check audio quality

### Slow response times
- Check server CPU usage
- Consider using Resemblyzer instead of ECAPA
- Monitor via `/metrics` endpoint

### Getting "unknown" for enrolled speaker
- Lower threshold (try 0.75)
- Enroll more samples (3-5 recommended)
- Rebuild centroids: `POST /api/rebuild_centroids`
- Check audio quality matches enrollment

---

For integration examples, see [Home Assistant Integration](ha-integration.md).
