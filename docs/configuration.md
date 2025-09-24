# Configuration

rtsp2jpg uses [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) to map environment variables (or a `.env` file) into the `Settings` model defined in `config.py`. All variables are prefixed with `RTSP2JPG_`.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `RTSP2JPG_DB_PATH` | str | `cameras.db` | Path to the SQLite database file. |
| `RTSP2JPG_READ_THROTTLE_SEC` | float | `0.08` | Delay between frame reads to avoid excessive CPU usage. |
| `RTSP2JPG_RECONNECT_DELAY_SEC` | float | `2.0` | Sleep duration before attempting to reopen a failed stream. |
| `RTSP2JPG_OPEN_TEST_TIMEOUT_SEC` | float | `4.0` | Time spent probing a backend during registration. |
| `RTSP2JPG_REGISTER_TEST_FRAMES` | int | `3` | Frames to pull during registration validation (currently advisory). |
| `RTSP2JPG_FFMPEG_FIRST` | bool | `True` | Prefer FFmpeg backend when both FFmpeg and GStreamer are available. |
| `RTSP2JPG_JPEG_QUALITY` | int | `85` | JPEG quality used when encoding snapshots (0–100). |
| `RTSP2JPG_LOG_LEVEL` | str | `INFO` | Global logging level for the application. |

## Loading order
1. Explicit environment variables take precedence.
2. Values from a `.env` file located at the project root come next.
3. Defaults defined in `Settings` are used when nothing else is supplied.

## Example `.env`
```
RTSP2JPG_DB_PATH=/data/rtsp2jpg.db
RTSP2JPG_READ_THROTTLE_SEC=0.12
RTSP2JPG_RECONNECT_DELAY_SEC=5.0
RTSP2JPG_JPEG_QUALITY=90
RTSP2JPG_LOG_LEVEL=DEBUG
```

## Tuning guidance
- **Unstable cameras**: increase `RTSP2JPG_RECONNECT_DELAY_SEC` to reduce rapid reconnect loops, and consider increasing `RTSP2JPG_OPEN_TEST_TIMEOUT_SEC` for slow RTSP handshakes.
- **High-motion scenes**: raise `RTSP2JPG_JPEG_QUALITY` at the cost of bandwidth; lower it for lighter payloads.
- **CPU constraints**: increase `RTSP2JPG_READ_THROTTLE_SEC` to lower the frame polling rate.

After changing configuration, restart the service so the new settings take effect.
