"""Tests for the RTSP worker loop frame filtering behaviour."""

from __future__ import annotations

import threading
from typing import List, Tuple

import numpy as np

from rtsp2jpg import cache, worker


class _DummySettings:
    read_throttle_sec = 0.0
    reconnect_delay_sec = 0.0
    jpeg_quality = 75


class _FakeCapture:
    def __init__(self, frames: List[Tuple[bool, object]], stop_event: threading.Event):
        self._frames = list(frames)
        self._stop_event = stop_event

    def read(self) -> Tuple[bool, object]:  # pragma: no cover - signature match
        if not self._frames:
            self._stop_event.set()
            return False, None
        return self._frames.pop(0)

    def release(self) -> None:  # pragma: no cover - API compatibility
        return None


def test_worker_skips_invalid_frames_before_caching(monkeypatch):
    token = "cam-skip"
    cache.clear(token)

    stop_event = threading.Event()
    valid_frame = np.zeros((2, 2, 3), dtype=np.uint8)
    fake_capture = _FakeCapture([(False, None), (True, valid_frame)], stop_event)

    monkeypatch.setattr(worker, "open_stream", lambda url, flag: (fake_capture, "ok"))
    monkeypatch.setattr(worker, "get_settings", lambda: _DummySettings())
    monkeypatch.setattr(worker, "update_status", lambda *args, **kwargs: None)
    monkeypatch.setattr(worker, "MAX_CONSECUTIVE_FRAME_FAILURES", 2, raising=False)

    statuses = []
    original_set_status = worker.cache.set_status

    def tracked_set_status(token_arg, status, error=None):
        statuses.append(status)
        original_set_status(token_arg, status, error)

    monkeypatch.setattr(worker.cache, "set_status", tracked_set_status)

    stored_frames = []

    def tracked_store_frame(token_arg, frame, quality):
        stored_frames.append(frame.copy())
        stop_event.set()

    monkeypatch.setattr(worker.cache, "store_frame", tracked_store_frame)

    worker._camera_worker(token, "rtsp://example", stop_event)

    assert stored_frames and stored_frames[0].shape == valid_frame.shape
    assert "connecting" not in statuses


class _AlwaysBadCapture:
    def __init__(self, stop_event: threading.Event):
        self._stop_event = stop_event
        self._count = 0

    def read(self) -> Tuple[bool, object]:  # pragma: no cover - signature match
        self._count += 1
        if self._count >= 2:
            self._stop_event.set()
        return False, None

    def release(self) -> None:  # pragma: no cover - API compatibility
        return None


def test_worker_reconnects_after_excessive_invalid_frames(monkeypatch):
    token = "cam-reconnect"
    cache.clear(token)

    stop_event = threading.Event()
    fake_capture = _AlwaysBadCapture(stop_event)

    monkeypatch.setattr(worker, "open_stream", lambda url, flag: (fake_capture, "ok"))
    monkeypatch.setattr(worker, "get_settings", lambda: _DummySettings())
    monkeypatch.setattr(worker, "update_status", lambda *args, **kwargs: None)
    monkeypatch.setattr(worker, "MAX_CONSECUTIVE_FRAME_FAILURES", 2, raising=False)

    statuses = []
    original_set_status = worker.cache.set_status

    def tracked_set_status(token_arg, status, error=None):
        statuses.append(status)
        original_set_status(token_arg, status, error)

    monkeypatch.setattr(worker.cache, "set_status", tracked_set_status)

    stored_frames: List[object] = []
    monkeypatch.setattr(worker.cache, "store_frame", lambda *args, **kwargs: stored_frames.append(True))

    worker._camera_worker(token, "rtsp://example", stop_event)

    assert "connecting" in statuses
    assert stored_frames == []
