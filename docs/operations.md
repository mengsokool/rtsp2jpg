# Operations & Monitoring

This section covers day-to-day operational tasks and health monitoring for rtsp2jpg.

## Health checks
- `GET /health`: verifies FastAPI is running and reports whether FFmpeg/GStreamer support is compiled into OpenCV.
- `GET /status/{token}`: monitor each camera; look for transitions to `error` or long periods in `connecting`.

## Recommended alerts
| Condition | Suggested alert / action |
|-----------|-------------------------|
| `status` stays `connecting` for >X minutes | Investigate network or credentials; camera likely offline. |
| `status` flips between `active` and `error` frequently | Increase `RTSP2JPG_RECONNECT_DELAY_SEC`; inspect logs for backend errors. |
| `last_seen` older than threshold | Worker is not receiving frames; check RTSP stream. |
| High CPU usage | Raise `RTSP2JPG_READ_THROTTLE_SEC` or reduce concurrent cameras per instance. |

## Logging
- Logs are emitted via Python’s `logging` module with timestamps and log level.
- Adjust verbosity with `RTSP2JPG_LOG_LEVEL` (`DEBUG`, `INFO`, `WARNING`, `ERROR`).
- Sample entries:
  ```
  2024-05-15 09:12:42 [INFO] rtsp2jpg.worker: 1a2b3c4d: connected via ffmpeg
  2024-05-15 09:13:03 [WARNING] rtsp2jpg.worker: 1a2b3c4d: frame read failed, reconnecting
  ```

## Scaling
- **Horizontal scaling**: run multiple rtsp2jpg instances with separate camera assignments. Tokens are local to each instance because SQLite is embedded.
- **Shared state**: to share tokens between instances, move persistence to a shared DB and replace the in-memory cache with an external store (Redis, Memcached). See [Architecture](architecture.md#extensibility-points).
- **Streaming density**: monitor thread count; each camera spawns one worker thread, so size your instance accordingly.

## Backups
- SQLite DB contains only RTSP URLs and status. Back it up periodically if you rely on the registry.
- Snapshots are not stored on disk; consumers must archive frames downstream if needed.

## Maintenance tasks
- Rotate logs if running under systemd or Docker (use `--log-opt max-size` with Docker).
- Rebuild the docker image when upgrading OpenCV or dependencies.
- Run `pytest` after dependency bumps to ensure regression coverage.

For troubleshooting tips, continue to [Troubleshooting](troubleshooting.md).
