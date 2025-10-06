# API Reference

Base URL examples
- Local development: `http://localhost:8000`
- Docker container: `http://<container-host>:8000`

All endpoints speak JSON unless noted. Tokens returned by `/register` are short strings (first 8 characters of a UUID).

## `GET /health`
**Purpose:** Sanity check for service liveness and backend build capabilities.

**Response 200**
```json
{
  "ok": true,
  "backends_built": {
    "ffmpeg": true,
    "gstreamer": false
  }
}
```

## `POST /register`
Register a new camera and start a worker thread.

**Request body**
```json
{
  "rtsp_url": "rtsp://user:pass@camera/stream",
  "prefer": "ffmpeg"   // optional: "ffmpeg", "gstreamer", or "default"
}
```

**Success 200**
```json
{
  "token": "a1b2c3d4",
  "backend": "ffmpeg"
}
```

**Client errors**
- `400` when the preferred backend or automatic detection fails (`detail` contains the message).

## `POST /unregister/{token}`
Stop the worker and remove cached data.

**Success 200**
```json
{"ok": true}
```

If the token does not exist, the endpoint still returns `200` with message `"already removed"` for idempotency.

## `GET /status/{token}`
Retrieve runtime state for a camera.

**Success 200**
```json
{
  "token": "a1b2c3d4",
  "status": "active",       // "active", "connecting", "inactive", "error", "unknown"
  "last_seen": 1715844193.12, // Unix timestamp (float) of last successful frame
  "backend": "ffmpeg",       // chosen backend label
  "error": null
}
```

**Errors**
- `404` if the token is not registered.

## `GET /snapshot/{token}`
Return the most recent JPEG frame as binary payload.

Query parameters:

- `q` *(optional, int, default `100`)* — JPEG quality to use when encoding the
  snapshot (1–100). Lower values reduce file size at the cost of image quality.

**Success 200**
- Content-Type: `image/jpeg`
- Body: JPEG bytes

**Errors**
- `503` with JSON body `{"detail": "No frame available yet"}` if no frame has been cached (e.g., camera still connecting or offline).

## Authentication
rtsp2jpg does not include authentication/authorization by default. Wrap the service with your reverse proxy, service mesh, or API gateway if security is required.

## OpenAPI schema
While the FastAPI app exposes `/.well-known/openapi.json` and interactive docs at `/docs`, these endpoints may be disabled in production via FastAPI configuration if desired.

For usage examples, see the [Overview quick start](overview.md#quick-start) or run the included tests (`pytest`).
