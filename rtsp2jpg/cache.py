"""In-memory runtime caches shared across the service."""

from __future__ import annotations

import threading
import time
from typing import Dict, Optional

import cv2
import numpy as np

FRAME_CACHE: Dict[str, np.ndarray] = {}
JPEG_CACHE: Dict[str, bytes] = {}
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
        LAST_SEEN_TS[token] = now


def get_jpeg(token: str) -> Optional[bytes]:
    with CACHE_LOCK:
        return JPEG_CACHE.get(token)


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
        LAST_SEEN_TS.pop(token, None)
    STATUS_CACHE.pop(token, None)
    ERROR_CACHE.pop(token, None)


def clear_all() -> None:
    with CACHE_LOCK:
        FRAME_CACHE.clear()
        JPEG_CACHE.clear()
        LAST_SEEN_TS.clear()
    STATUS_CACHE.clear()
    ERROR_CACHE.clear()
