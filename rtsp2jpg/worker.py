"""Camera worker threads that pull frames from RTSP streams."""

from __future__ import annotations

import logging
import threading
import time
from typing import Dict, Optional

import cv2

from . import cache
from .backends import backend_name, open_stream
from .config import get_settings
from .db import update_status

LOGGER = logging.getLogger(__name__)

WORKERS: Dict[str, threading.Thread] = {}
STOP_EVENTS: Dict[str, threading.Event] = {}
BACKEND_CHOICE: Dict[str, Optional[int]] = {}


def start_worker(token: str, rtsp_url: str, backend_flag: Optional[int]) -> None:
    """Start a worker thread for the given camera token."""

    stop_event = threading.Event()
    STOP_EVENTS[token] = stop_event
    BACKEND_CHOICE[token] = backend_flag
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
    cache.set_status(token, "inactive")
    update_status(token, "inactive")


def stop_all_workers() -> None:
    for token in list(STOP_EVENTS.keys()):
        stop_worker(token)


def backend_flag_for(token: str) -> Optional[int]:
    return BACKEND_CHOICE.get(token)


def _camera_worker(token: str, rtsp_url: str, stop_event: threading.Event) -> None:
    settings = get_settings()
    backend_flag = BACKEND_CHOICE.get(token)

    while not stop_event.is_set():
        try:
            cap, note = open_stream(rtsp_url, backend_flag)
            if cap is None:
                cache.set_status(token, "error", note)
                update_status(token, "error")
                LOGGER.error("%s: failed to open stream (%s)", token, note)
                if stop_event.wait(settings.reconnect_delay_sec):
                    break
                continue

            cache.set_status(token, "active")
            update_status(token, "active")
            LOGGER.info("%s: connected via %s", token, backend_name(backend_flag))

            while not stop_event.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    cache.set_status(token, "connecting")
                    update_status(token, "connecting")
                    LOGGER.warning("%s: frame read failed, reconnecting", token)
                    break
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
