# Deployment Guide

rtsp2jpg ships with multiple deployment options. Choose the path that best matches your environment.

## 1. Local Python environment
Best for development and quick experimentation.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[test]
uvicorn rtsp2jpg.app:app --host 0.0.0.0 --port 8000
```

Use `.env` to override defaults and `pytest` to run the test suite.

## 2. Docker
The provided `Dockerfile` bundles Python 3.11, FFmpeg, and GStreamer plugins.

```bash
docker build -t rtsp2jpg .
docker run --rm -p 8000:8000 --env-file .env.example rtsp2jpg
```

Mount persistent storage if you want the SQLite database to survive restarts:
```bash
docker run --rm -p 8000:8000 \
  -v $(pwd)/data:/data \
  -e RTSP2JPG_DB_PATH=/data/cameras.db \
  rtsp2jpg
```

## 3. Docker Compose
`docker-compose.yaml` offers a single-service stack ready to extend with dependencies (e.g., Prometheus exporters).

```bash
docker compose up --build -d
```

## 4. Kubernetes (example snippet)
Minimal Deployment + Service example:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rtsp2jpg
spec:
  replicas: 1
  selector:
    matchLabels:
      app: rtsp2jpg
  template:
    metadata:
      labels:
        app: rtsp2jpg
    spec:
      containers:
        - name: rtsp2jpg
          image: your-registry/rtsp2jpg:latest
          env:
            - name: RTSP2JPG_DB_PATH
              value: /data/cameras.db
          volumeMounts:
            - name: data
              mountPath: /data
          ports:
            - containerPort: 8000
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: rtsp2jpg-data
---
apiVersion: v1
kind: Service
metadata:
  name: rtsp2jpg
spec:
  selector:
    app: rtsp2jpg
  ports:
    - port: 8000
      targetPort: 8000
```

## 5. Reverse proxy
Place Nginx, Traefik, or Caddy in front to add TLS, authentication, or rate limiting. Example Nginx location block:
```nginx
location /rtsp2jpg/ {
    proxy_pass http://rtsp2jpg:8000/;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

## 6. Observability
- Add metrics or logs by tailing stdout (`docker logs`) or shipping JSON logs from the container.
- Expose Prometheus or OpenTelemetry metrics by integrating additional middleware (not shipped by default).

Refer to the [Operations guide](operations.md) for runtime maintenance and tuning.
