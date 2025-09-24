# Architecture

rtsp2jpg is a modular FastAPI service composed of the following layers:

```
rtsp2jpg/
├── app.py           # FastAPI app factory + lifespan hooks
├── api/             # Route groupings (cameras, snapshot, status)
├── backends.py      # OpenCV backend detection + stream opening
├── cache.py         # In-memory frame/JPEG/status caches
├── config.py        # Pydantic Settings wrapper
├── db.py            # SQLite helpers & models
├── worker.py        # Per-camera worker lifecycle
└── logging_config.py# Structured logging bootstrap
```

## Request lifecycle
1. **Registration (`POST /register`)**
   - Validate payload, optional backend preference.
   - Choose a backend (FFmpeg, GStreamer, default) using `backends.choose_backend`.
   - Persist camera metadata via `db.add_camera`.
   - Start a worker thread with `worker.start_worker`.
   - Return a short token for subsequent calls.

2. **Worker loop**
   - Attempt to open the RTSP stream with the chosen backend.
   - On success: read frames, encode JPEG, push to cache, update status.
   - On read failure: downgrade status to `connecting`, break loop, sleep, retry.
   - On exception: mark status `error`, log, sleep, retry.

3. **Snapshot retrieval (`GET /snapshot/{token}`)**
   - Lookup cached JPEG; if absent return 503 with a clear message.
   - Serve bytes with `image/jpeg` content type.

4. **Status queries**
   - Merge database metadata with cache runtime information (`status`, `last_seen`, `backend`, `error`).

5. **Unregistration**
   - Stop worker, clear caches, delete DB entry.

## Lifespan management
- Startup: `init_db()` ensures the SQLite schema exists.
- Shutdown: `stop_all_workers()` joins active threads and `cache.clear_all()` flushes caches.

## Threading model
- A global dictionary of worker threads keyed by token ensures one worker per camera.
- `threading.Event` objects provide responsive shutdown signaling.
- Shared caches are protected by a single `CACHE_LOCK` to keep updates atomic.

## Persistence
- SQLite stores minimal camera metadata: token, RTSP URL, status string.
- Actual frame data remains in memory; persisting snapshots is deliberately out of scope.

## Extensibility points
- **Backends**: add new capture backends by extending `BACKEND_NAMES` and `_prefer_to_flag`.
- **Cache**: swap to Redis/Memcached by re-implementing the cache module (ensure thread safety).
- **Database**: replace SQLite with Postgres or others by implementing the same CRUD surface.
- **Workers**: alternative scheduling (e.g., asyncio, multiprocessing) can plug in by matching the start/stop API.

Refer to the [Operations guide](operations.md) for runtime considerations and monitoring.
