# rtsp2jpg

Expose RTSP cameras as cached JPEG snapshots backed by FastAPI + OpenCV. The service auto-detects the best available VideoCapture backend (FFmpeg or GStreamer), keeps a live worker per registered camera, and offers a lightweight HTTP API for registration, status, and snapshot retrieval.

```
Camera ──▶ rtsp2jpg ──▶ Downstream consumers (YOLO, dashboards, storage)
```

## Features
- FastAPI application with modular architecture (`rtsp2jpg/` package)
- Backend auto-detection between FFmpeg, GStreamer, and OpenCV default
- Per-camera worker threads with JPEG caching and status tracking
- SQLite persistence for registered cameras
- Configurable via environment variables or `.env`
- Docker image and compose stack for easy deployment

## Quick start

### Python environment
```
python -m venv .venv
source .venv/bin/activate
pip install -e .[test]
uvicorn rtsp2jpg.app:app --host 0.0.0.0 --port 8000
```

### Docker
```
docker build -t rtsp2jpg .
docker run --rm -p 8000:8000 --env-file .env.example rtsp2jpg
```

For local development with FFmpeg/GStreamer dependencies pre-installed use:
```
docker compose up --build
```

The `.env` file is for service configuration knobs—database path, logging level, throttling, and similar options.
Supply RTSP URLs (with credentials) via the `/register` API or follow the [overview quick start](docs/overview.md#quick-start).

Run the automated tests at any time with:
```
pytest
```

## Documentation
Detailed documentation lives under [`docs/`](docs/index.md). Start with the overview or dive into the topic you need:

- [Overview](docs/overview.md)
- [Architecture](docs/architecture.md)
- [Configuration](docs/configuration.md)
- [API reference](docs/api.md)
- [Deployment guide](docs/deployment.md)
- [Operations & monitoring](docs/operations.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Contributing](docs/contributing.md)

## License
MIT – see [LICENSE](LICENSE).
