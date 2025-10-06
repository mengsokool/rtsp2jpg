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

## FFmpeg/H.264 decode errors in the logs
- Messages such as `co located POCs unavailable`, `cabac decode of qscale diff failed`, or
  `error while decoding MB …` originate from FFmpeg when the camera delivers a corrupted or
  incomplete H.264 frame. They are warnings that FFmpeg is attempting to conceal damaged macroblocks
  and do **not** mean the rtsp2jpg worker has crashed.
- These issues usually happen with unstable RTSP links (WiFi, congested networks, or cheap cameras).
  Reduce packet loss by improving signal quality, lowering the camera bitrate, or switching to a more
  reliable transport such as wired Ethernet or TCP RTSP mode when available.
- The worker now listens to FFmpeg/GStreamer stderr and skips frames whenever these warnings appear,
  preventing corrupted images from being cached. Tune the suppression window with
  `RTSP2JPG_DECODER_WARNING_WINDOW_SEC` or disable monitoring entirely with
  `RTSP2JPG_ENABLE_DECODER_LOG_MONITOR=false` if you run on a platform where redirecting stderr is not
  desirable.
- Ensure the camera's firmware is up to date. Some devices emit non-standard H.264 streams that trigger
  FFmpeg error spam; firmware updates often fix encoder bugs.
- If the errors flood the logs but snapshots still work, you can lower the log level to `WARNING` by
  setting `RTSP2JPG_LOG_LEVEL=warning` so that FFmpeg's diagnostic messages are suppressed.
- When the stream becomes unreadable, rtsp2jpg will reconnect according to the configured retry
  policy. Investigate persistent failures by retrieving `/status/{token}` which includes the last
  backend error text and the number of consecutive failures.

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
