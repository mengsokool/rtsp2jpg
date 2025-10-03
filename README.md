# rtsp2jpg

Expose RTSP cameras as cached JPEG snapshots backed by FastAPI + OpenCV. rtsp2jpg keeps a worker per camera, caches frames, and exposes a lightweight HTTP API for registration, status, and snapshot retrieval.

## Why rtsp2jpg?
- Auto-detects the best available VideoCapture backend (FFmpeg or GStreamer)
- Ships with a modular FastAPI application (`rtsp2jpg/` package)
- Maintains per-camera workers with SQLite persistence and health tracking
- Configurable through environment variables or `.env`
- Includes Docker, Docker Compose, and PM2 deployment recipes

## Quickstart
Launch the stack with a single command:

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

The published image starts a plain `uvicorn` process without `--reload`. To
develop with live reload you can mount your source tree as a volume and add the
flag, for example:

```
docker run --rm -p 8000:8000 \
  -v "$(pwd)":/app \
  --env-file .env.example \
  rtsp2jpg \
  uvicorn rtsp2jpg.app:app --host 0.0.0.0 --port 8000 --reload
```

The `.env` file is for service configuration knobs—database path, logging level, throttling, and similar options.
Supply RTSP URLs (with credentials) via the `/register` API or follow the [overview quick start](docs/overview.md#quick-start).

Run the automated tests at any time with:
```
docker compose up --build
```

You will get a FastAPI server on `http://localhost:8000` with hot reload-friendly defaults. Use an `.env` file to provide camera credentials or overrides.

## Deployment options
- [Local Python environment](docs/deployment.md#python-env)
- [Docker](docs/deployment.md#docker)
- [Docker Compose](docs/deployment.md#docker-compose)
- [PM2](docs/deployment.md#pm2)
- [Testing](docs/deployment.md#testing)

## Learn more
Comprehensive documentation lives in [`docs/`](docs/index.md):

- [Overview](docs/overview.md)
- [Architecture](docs/architecture.md)
- [Configuration](docs/configuration.md)
- [API reference](docs/api.md)
- [Operations & monitoring](docs/operations.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Contributing](docs/contributing.md)

## License
MIT – see [LICENSE](LICENSE).
