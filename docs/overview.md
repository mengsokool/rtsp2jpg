# Overview

rtsp2jpg bridges IP cameras and downstream systems that prefer HTTP and JPEG snapshots. At runtime the service:

1. Accepts RTSP URLs via a REST API and stores metadata in SQLite.
2. Spins up a worker thread per camera that reads frames with OpenCV.
3. Encodes the latest frame into JPEG and caches it in memory.
4. Serves `/snapshot/{token}` responses directly from the in-memory cache.
5. Exposes health, status, and lifecycle endpoints for integration and monitoring.

```
Camera ──RTSP──▶ rtsp2jpg ──HTTP──▶ Consumers (dashboards, model runners, archival jobs)
```

## Key features
- **Backend auto-detection**: Chooses FFmpeg, GStreamer, or the OpenCV default at registration time.
- **Per-camera workers**: Isolates unstable streams and reconnects automatically on failure.
- **Jitter-tolerant caching**: Consumers always receive the most recent frame or a clear 503 if none are available.
- **Lightweight persistence**: SQLite tracks registered cameras and their status.
- **Configurable behavior**: Pydantic Settings makes tuning reconnection windows and JPEG quality simple.
- **Deployment-ready**: Dockerfile and Compose stack bake in FFmpeg/GStreamer dependencies.

## Quick start
1. Clone the repository and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .[test]
   ```
2. Launch the service:
   ```bash
   uvicorn rtsp2jpg.app:app --host 0.0.0.0 --port 8000
   ```
3. Register a camera:
   ```bash
   curl -X POST http://localhost:8000/register \
     -H 'Content-Type: application/json' \
     -d '{"rtsp_url": "rtsp://user:pass@camera/stream"}'
   ```
4. Fetch the latest snapshot:
   ```bash
   curl http://localhost:8000/snapshot/<token> --output frame.jpg
   ```

For full deployment instructions, continue to the [Deployment guide](deployment.md).
