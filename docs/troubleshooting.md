# Troubleshooting

Use this checklist when diagnosing issues with rtsp2jpg.

## Registration fails (HTTP 400)
- **Invalid backend preference**: Ensure `prefer` is one of `ffmpeg`, `gstreamer`, or `default`.
- **Backend unavailable**: Check `/health` to confirm FFmpeg/GStreamer support. Install missing codecs in your container or host.
- **RTSP URL typo**: Validate credentials and host reachability outside rtsp2jpg (e.g., `ffprobe` or `gst-launch`).

## Snapshot returns 503
- **Worker still connecting**: Give the worker time to fetch the first frame. Monitor `/status/{token}`.
- **Camera offline**: If `status` is `error`, inspect the `error` message (often contains OpenCV backend details).
- **Cache cleared**: After `/unregister`, snapshot tokens are invalidated by design.

## Frequent reconnect loops
- Increase `RTSP2JPG_RECONNECT_DELAY_SEC` to avoid hammering an unstable camera.
- Consider locking the backend preference to whichever is most stable (`prefer` during registration).
- If using WiFi cameras, reduce frame rate by increasing `RTSP2JPG_READ_THROTTLE_SEC`.

## High CPU usage
- Lower the number of concurrent cameras per instance.
- Increase `RTSP2JPG_READ_THROTTLE_SEC` or disable `uvicorn` auto-reload flags in production.
- Run headless builds (`opencv-python-headless`) as already specified in requirements.

## Database errors
- Ensure the process has write access to `RTSP2JPG_DB_PATH`.
- For disk-full situations, move the database to a larger volume or external database.

## Upgrading dependencies
- Rebuild the Docker image to pick up new FFmpeg/GStreamer versions.
- Run `pytest` to catch regressions; failing tests often point to new behaviors in OpenCV or FastAPI.

Still stuck? Open an issue with logs, environment details, and reproduction steps. Include error messages from `/status` responses when reporting worker failures.
