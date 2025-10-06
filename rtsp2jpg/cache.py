"""In-memory runtime caches shared across the service."""

from __future__ import annotations

import threading
import time
from typing import Dict, Optional

import cv2
import numpy as np

FRAME_CACHE: Dict[str, np.ndarray] = {}
JPEG_CACHE: Dict[str, bytes] = {}
JPEG_CACHE_QUALITY: Dict[str, int] = {}
STATUS_CACHE: Dict[str, str] = {}
ERROR_CACHE: Dict[str, Optional[str]] = {}
LAST_SEEN_TS: Dict[str, float] = {}

CACHE_LOCK = threading.Lock()


def store_frame(token: str, frame: np.ndarray, jpeg_quality: int) -> None:
    """Encode and store the latest frame + JPEG payload for the token."""

    ok, jpeg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)])
    if not ok:
        return
    now = time.time()
    with CACHE_LOCK:
        FRAME_CACHE[token] = frame
        JPEG_CACHE[token] = jpeg.tobytes()
        JPEG_CACHE_QUALITY[token] = int(jpeg_quality)
        LAST_SEEN_TS[token] = now


def get_jpeg(token: str, quality: Optional[int] = None) -> Optional[bytes]:
    """Return cached JPEG bytes, optionally re-encoding at a new quality."""

    with CACHE_LOCK:
        cached_jpeg = JPEG_CACHE.get(token)
        cached_quality = JPEG_CACHE_QUALITY.get(token)
        frame = FRAME_CACHE.get(token)

    if quality is None or quality == cached_quality:
        return cached_jpeg

    if frame is None:
        return cached_jpeg

    ok, jpeg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)])
    if not ok:
        return None
    return jpeg.tobytes()


def set_status(token: str, status: str, error: Optional[str] = None) -> None:
    STATUS_CACHE[token] = status
    ERROR_CACHE[token] = error


def get_status(token: str) -> Dict[str, Optional[str]]:
    return {
        "status": STATUS_CACHE.get(token, "unknown"),
        "error": ERROR_CACHE.get(token),
        "last_seen": LAST_SEEN_TS.get(token),
    }


def clear(token: str) -> None:
    with CACHE_LOCK:
        FRAME_CACHE.pop(token, None)
        JPEG_CACHE.pop(token, None)
        JPEG_CACHE_QUALITY.pop(token, None)
        LAST_SEEN_TS.pop(token, None)
    STATUS_CACHE.pop(token, None)
    ERROR_CACHE.pop(token, None)


def clear_all() -> None:
    with CACHE_LOCK:
        FRAME_CACHE.clear()
        JPEG_CACHE.clear()
        JPEG_CACHE_QUALITY.clear()
        LAST_SEEN_TS.clear()
    STATUS_CACHE.clear()
    ERROR_CACHE.clear()
