"""Backend detection helpers for OpenCV VideoCapture backends."""

from __future__ import annotations

import logging
import time
from typing import Dict, Optional, Tuple

import cv2

from .config import get_settings

LOGGER = logging.getLogger(__name__)

BACKEND_NAMES: Dict[Optional[int], str] = {
    None: "default",
    cv2.CAP_FFMPEG: "ffmpeg",
    cv2.CAP_GSTREAMER: "gstreamer",
}


def build_supports() -> Dict[str, bool]:
    """Return backend availability based on the OpenCV build."""

    info = cv2.getBuildInformation()
    return {
        "ffmpeg": "FFMPEG" in info,
        "gstreamer": "GStreamer" in info,
    }


def backend_name(flag: Optional[int]) -> str:
    return BACKEND_NAMES.get(flag, f"flag:{flag}")


def _try_open(rtsp_url: str, backend_flag: Optional[int], quick: bool = False) -> Optional[cv2.VideoCapture]:
    settings = get_settings()
    cap = cv2.VideoCapture(rtsp_url, backend_flag) if backend_flag is not None else cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        cap.release()
        return None

    try:
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    except Exception:  # pragma: no cover - best effort tuning
        pass

    if quick:
        t0 = time.time()
        while time.time() - t0 < settings.open_test_timeout_sec:
            ok, _ = cap.read()
            if ok:
                return cap
            time.sleep(0.01)
        cap.release()
        return None
    return cap


def choose_backend(rtsp_url: str, prefer: Optional[str] = None) -> Tuple[Optional[int], str]:
    """Determine the backend flag to use for the RTSP URL."""

    settings = get_settings()

    if prefer:
        prefer_flag = _prefer_to_flag(prefer)
        if prefer_flag is None and prefer.lower() != "default":
            raise ValueError("Invalid backend preference")
        cap = _try_open(rtsp_url, prefer_flag, quick=True)
        if not cap:
            raise ValueError("Cannot open stream with preferred backend")
        cap.release()
        return prefer_flag, backend_name(prefer_flag)

    supports = build_supports()
    if settings.ffmpeg_first:
        order = [cv2.CAP_FFMPEG, cv2.CAP_GSTREAMER, None]
    else:
        order = [cv2.CAP_GSTREAMER, cv2.CAP_FFMPEG, None]

    for flag in order:
        if flag == cv2.CAP_FFMPEG and not supports.get("ffmpeg", False):
            continue
        if flag == cv2.CAP_GSTREAMER and not supports.get("gstreamer", False):
            continue
        cap = _try_open(rtsp_url, flag, quick=True)
        if cap:
            cap.release()
            return flag, backend_name(flag)

    raise ValueError("Cannot open stream with any backend")


def open_stream(rtsp_url: str, backend_flag: Optional[int]) -> Tuple[Optional[cv2.VideoCapture], str]:
    """Open a stream using the provided backend flag."""

    cap = _try_open(rtsp_url, backend_flag, quick=False)
    if cap:
        name = backend_name(backend_flag)
        return cap, name
    return None, f"backend {backend_flag} failed"


def _prefer_to_flag(prefer: str) -> Optional[int]:
    prefer = prefer.lower().strip()
    if prefer == "ffmpeg":
        return cv2.CAP_FFMPEG
    if prefer == "gstreamer":
        return cv2.CAP_GSTREAMER
    if prefer == "default":
        return None
    return None
