"""Camera worker threads that pull frames from RTSP streams."""

from __future__ import annotations

import logging
import threading
import time
from typing import Dict, Optional

import cv2

from . import cache
from .backends import backend_name, choose_backend, open_stream
from .config import get_settings
from .db import update_status

LOGGER = logging.getLogger(__name__)

WORKERS: Dict[str, threading.Thread] = {}
STOP_EVENTS: Dict[str, threading.Event] = {}
BACKEND_CHOICE: Dict[str, Optional[int]] = {}
BACKEND_AUTODETECT: Dict[str, bool] = {}

MAX_CONSECUTIVE_FRAME_FAILURES = 5


def start_worker(
    token: str,
    rtsp_url: str,
    backend_flag: Optional[int],
    *,
    autodetect: bool = False,
) -> None:
    """Start a worker thread for the given camera token.

    When ``autodetect`` is ``True`` the worker will periodically re-run backend
    detection after connection failures until it succeeds, allowing startup to
    proceed even if the camera was temporarily offline during the initial
    bootstrap.
    """

    stop_event = threading.Event()
    STOP_EVENTS[token] = stop_event
    BACKEND_CHOICE[token] = backend_flag
    BACKEND_AUTODETECT[token] = autodetect
    cache.set_status(token, "connecting")
    update_status(token, "connecting")

    thread = threading.Thread(
        target=_camera_worker,
        args=(token, rtsp_url, stop_event),
        name=f"camera-{token}",
        daemon=True,
    )
    WORKERS[token] = thread
    thread.start()


def stop_worker(token: str, join_timeout: float = 2.0) -> None:
    stop_event = STOP_EVENTS.get(token)
    thread = WORKERS.get(token)

    if stop_event:
        stop_event.set()
    if thread and thread.is_alive():
        thread.join(timeout=join_timeout)

    WORKERS.pop(token, None)
    STOP_EVENTS.pop(token, None)
    BACKEND_CHOICE.pop(token, None)
    BACKEND_AUTODETECT.pop(token, None)
    cache.set_status(token, "inactive")
    update_status(token, "inactive")


def stop_all_workers() -> None:
    for token in list(STOP_EVENTS.keys()):
        stop_worker(token)


def backend_flag_for(token: str) -> Optional[int]:
    return BACKEND_CHOICE.get(token)


def _is_frame_valid(ok: bool, frame: Optional[object]) -> bool:
    """Return True when the frame returned from VideoCapture looks usable."""

    if not ok or frame is None:
        return False
    # Some backends return empty ndarrays when the decoder hiccups.
    if getattr(frame, "size", 0) == 0:
        return False
    return True


def _camera_worker(token: str, rtsp_url: str, stop_event: threading.Event) -> None:
    settings = get_settings()

    while not stop_event.is_set():
        try:
            backend_flag = BACKEND_CHOICE.get(token)
            autodetect = BACKEND_AUTODETECT.get(token, False)

            cap, note = open_stream(rtsp_url, backend_flag)
            if cap is None:
                cache.set_status(token, "error", note)
                update_status(token, "error")
                LOGGER.error("%s: failed to open stream (%s)", token, note)
                if autodetect:
                    try:
                        new_flag, backend_label = choose_backend(rtsp_url)
                    except ValueError as detect_exc:
                        LOGGER.debug(
                            "%s: backend autodetect still failing: %s",
                            token,
                            detect_exc,
                        )
                    else:
                        BACKEND_CHOICE[token] = new_flag
                        BACKEND_AUTODETECT[token] = False
                        LOGGER.info(
                            "%s: backend autodetect succeeded with %s",
                            token,
                            backend_label,
                        )
                        continue
                if stop_event.wait(settings.reconnect_delay_sec):
                    break
                continue

            cache.set_status(token, "active")
            update_status(token, "active")
            LOGGER.info("%s: connected via %s", token, backend_name(backend_flag))

            consecutive_failures = 0
            while not stop_event.is_set():
                ok, frame = cap.read()
                if not _is_frame_valid(ok, frame):
                    consecutive_failures += 1
                    if consecutive_failures >= MAX_CONSECUTIVE_FRAME_FAILURES:
                        cache.set_status(token, "connecting")
                        update_status(token, "connecting")
                        LOGGER.warning(
                            "%s: too many invalid frames, reconnecting", token
                        )
                        break
                    LOGGER.debug(
                        "%s: skipping invalid frame (%d/%d)",
                        token,
                        consecutive_failures,
                        MAX_CONSECUTIVE_FRAME_FAILURES,
                    )
                    if stop_event.wait(settings.read_throttle_sec):
                        break
                    continue

                consecutive_failures = 0
                cache.store_frame(token, frame, settings.jpeg_quality)
                if stop_event.wait(settings.read_throttle_sec):
                    break

            cap.release()
            if stop_event.is_set():
                break
            if stop_event.wait(settings.reconnect_delay_sec):
                break
        except Exception as exc:  # pragma: no cover - defensive guard
            cache.set_status(token, "error", str(exc))
            update_status(token, "error")
            LOGGER.exception("%s: worker crashed", token, exc_info=exc)
            if stop_event.wait(settings.reconnect_delay_sec):
                break

    cache.set_status(token, "inactive")
    update_status(token, "inactive")
    LOGGER.info("%s: worker stopped", token)
