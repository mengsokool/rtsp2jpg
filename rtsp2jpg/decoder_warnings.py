"""Helpers for detecting decoder corruption warnings from FFmpeg/GStreamer."""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from typing import Dict, Optional, Set
from urllib.parse import urlparse

from .config import get_settings

LOGGER = logging.getLogger(__name__)

_WARNING_PATTERNS = (
    "error while decoding",
    "cabac decode",
    "co located pocs unavailable",
    "concealing",
    "corrupt input",
    "corrupt macroblock",
    "error received from element",
)


class _DecoderWarningMonitor:
    """Capture stderr output and mark when decoder corruption is reported."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_warning_global: float = 0.0
        self._last_warning_by_token: Dict[str, float] = {}
        self._pointer_by_token: Dict[str, Set[str]] = {}
        self._token_by_pointer: Dict[str, str] = {}
        self._keywords_by_token: Dict[str, Set[str]] = {}
        self._enabled = False
        self._reader_thread: Optional[threading.Thread] = None
        self._pipe_r: Optional[int] = None
        self._orig_stderr_fd: Optional[int] = None

    @staticmethod
    def _extract_pointer(line: str) -> Optional[str]:
        match = re.search(r"\[[^\[]*?@\s*(0x[0-9a-fA-F]+)\]", line)
        if match:
            return match.group(1).casefold()
        return None

    def start(self) -> None:
        if self._enabled:
            return

        if os.name != "posix":
            LOGGER.debug("Decoder warning monitor not supported on %s", os.name)
            return

        try:
            pipe_r, pipe_w = os.pipe()
            orig_stderr_fd = os.dup(2)
            os.dup2(pipe_w, 2)
            os.close(pipe_w)
        except OSError as exc:
            LOGGER.warning("Decoder warning monitor disabled: %s", exc)
            return

        self._pipe_r = pipe_r
        self._orig_stderr_fd = orig_stderr_fd
        self._enabled = True
        self._reader_thread = threading.Thread(target=self._pump_stderr, name="decoder-log", daemon=True)
        self._reader_thread.start()
        LOGGER.debug("Decoder warning monitor started")

    def _pump_stderr(self) -> None:
        assert self._pipe_r is not None
        assert self._orig_stderr_fd is not None

        buffer = b""
        while True:
            try:
                chunk = os.read(self._pipe_r, 4096)
            except OSError as exc:  # pragma: no cover - defensive
                LOGGER.debug("Decoder warning monitor read failed: %s", exc)
                break
            if not chunk:
                break
            try:
                os.write(self._orig_stderr_fd, chunk)
            except OSError:  # pragma: no cover - write best effort
                pass
            buffer += chunk
            buffer = self._process_buffer(buffer)

        if buffer:
            try:
                os.write(self._orig_stderr_fd, buffer)
            except OSError:  # pragma: no cover - best effort
                pass

        try:
            os.close(self._pipe_r)
        except OSError:  # pragma: no cover - best effort cleanup
            pass
        try:
            os.close(self._orig_stderr_fd)
        except OSError:  # pragma: no cover - best effort cleanup
            pass

    def _process_buffer(self, buffer: bytes) -> bytes:
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            self._handle_line(line.decode("utf-8", "replace"))
        return buffer

    def _handle_line(self, raw_line: str) -> None:
        line = raw_line.strip()
        if not line:
            return
        folded = line.casefold()

        pointer = self._extract_pointer(line)
        token = None
        with self._lock:
            if pointer and pointer in self._token_by_pointer:
                token = self._token_by_pointer[pointer]
            else:
                token = self._detect_token_for_line(folded)
                if token and pointer:
                    self._token_by_pointer[pointer] = token
                    self._pointer_by_token.setdefault(token, set()).add(pointer)

            if token is None and any(pattern in folded for pattern in _WARNING_PATTERNS):
                # Track a global warning fallback so callers can still consult it.
                self._last_warning_global = time.monotonic()
                LOGGER.debug("Decoder reported warning (unattributed): %s", line)
                return

            if token and any(pattern in folded for pattern in _WARNING_PATTERNS):
                now = time.monotonic()
                self._last_warning_by_token[token] = now
                self._last_warning_global = now
                LOGGER.debug("Decoder reported warning for %s: %s", token, line)

    def record_manual_warning(self) -> None:
        with self._lock:
            self._last_warning_global = time.monotonic()

    def had_recent_warning(self, window_sec: float) -> bool:
        if not self._enabled and os.name == "posix":
            # Monitoring might be disabled by configuration; treat as no warning.
            pass
        with self._lock:
            if not self._last_warning_global:
                return False
            return (time.monotonic() - self._last_warning_global) <= window_sec

    def register_stream(self, token: str, url: str) -> None:
        keywords = _keywords_for_url(url)
        with self._lock:
            self._keywords_by_token[token] = keywords
            # Clear any existing warning state/pointer mapping for reused tokens.
            for pointer in self._pointer_by_token.pop(token, set()):
                self._token_by_pointer.pop(pointer, None)
            self._last_warning_by_token.pop(token, None)

    def unregister_stream(self, token: str) -> None:
        with self._lock:
            self._keywords_by_token.pop(token, None)
            for pointer in self._pointer_by_token.pop(token, set()):
                self._token_by_pointer.pop(pointer, None)
            self._last_warning_by_token.pop(token, None)

    def had_recent_warning_for_token(self, token: str, window_sec: float) -> bool:
        if not self._enabled and os.name == "posix":
            pass
        with self._lock:
            timestamp = self._last_warning_by_token.get(token)
            if not timestamp:
                return False
            return (time.monotonic() - timestamp) <= window_sec

    def record_manual_warning_for_token(self, token: str) -> None:
        with self._lock:
            now = time.monotonic()
            self._last_warning_by_token[token] = now
            self._last_warning_global = max(self._last_warning_global, now)

    def _detect_token_for_line(self, folded_line: str) -> Optional[str]:
        for token, keywords in self._keywords_by_token.items():
            if any(keyword and keyword in folded_line for keyword in keywords):
                return token
        return None


_MONITOR: Optional[_DecoderWarningMonitor] = None
_MONITOR_LOCK = threading.Lock()


def _get_monitor() -> _DecoderWarningMonitor:
    global _MONITOR
    if _MONITOR is None:
        with _MONITOR_LOCK:
            if _MONITOR is None:
                _MONITOR = _DecoderWarningMonitor()
    return _MONITOR


def ensure_started() -> None:
    settings = get_settings()
    if not settings.enable_decoder_log_monitor:
        return
    monitor = _get_monitor()
    monitor.start()


def had_recent_warning(window_sec: float) -> bool:
    settings = get_settings()
    if not settings.enable_decoder_log_monitor:
        return False
    monitor = _get_monitor()
    return monitor.had_recent_warning(window_sec)


def record_manual_warning() -> None:
    monitor = _get_monitor()
    monitor.record_manual_warning()


def register_stream(token: str, url: str) -> None:
    settings = get_settings()
    if not settings.enable_decoder_log_monitor:
        return
    monitor = _get_monitor()
    monitor.register_stream(token, url)


def unregister_stream(token: str) -> None:
    settings = get_settings()
    if not settings.enable_decoder_log_monitor:
        return
    monitor = _get_monitor()
    monitor.unregister_stream(token)


def had_recent_warning_for_token(token: str, window_sec: float) -> bool:
    settings = get_settings()
    if not settings.enable_decoder_log_monitor:
        return False
    monitor = _get_monitor()
    return monitor.had_recent_warning_for_token(token, window_sec)


def record_manual_warning_for_token(token: str) -> None:
    settings = get_settings()
    if not settings.enable_decoder_log_monitor:
        return
    monitor = _get_monitor()
    monitor.record_manual_warning_for_token(token)


def _keywords_for_url(url: str) -> Set[str]:
    parsed = urlparse(url)
    keywords: Set[str] = set()
    if parsed.hostname:
        keywords.add(parsed.hostname.casefold())
    if parsed.port:
        keywords.add(str(parsed.port))
    if parsed.path and parsed.path != "/":
        keywords.add(parsed.path.casefold())
        keywords.add(parsed.path.strip("/").casefold())
    return {word for word in keywords if word}
