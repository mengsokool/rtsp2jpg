"""SQLite helpers for persisting cameras."""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator, List, Optional

from .config import get_settings

_DB_LOCK = threading.Lock()


@dataclass
class Camera:
    token: str
    rtsp_url: str
    status: str


@contextmanager
def _connection() -> Iterator[sqlite3.Connection]:
    settings = get_settings()
    conn = sqlite3.connect(settings.db_path, check_same_thread=False)
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with _DB_LOCK, _connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cameras (
                token TEXT PRIMARY KEY,
                rtsp_url TEXT NOT NULL,
                status TEXT DEFAULT 'inactive'
            )
            """
        )
        conn.commit()


def add_camera(token: str, rtsp_url: str, status: str = "inactive") -> None:
    with _DB_LOCK, _connection() as conn:
        conn.execute(
            "INSERT INTO cameras (token, rtsp_url, status) VALUES (?, ?, ?)",
            (token, rtsp_url, status),
        )
        conn.commit()


def get_camera(token: str) -> Optional[Camera]:
    with _DB_LOCK, _connection() as conn:
        row = conn.execute(
            "SELECT token, rtsp_url, status FROM cameras WHERE token = ?",
            (token,),
        ).fetchone()
    if not row:
        return None
    return Camera(*row)


def update_status(token: str, status: str) -> None:
    with _DB_LOCK, _connection() as conn:
        conn.execute("UPDATE cameras SET status = ? WHERE token = ?", (status, token))
        conn.commit()


def delete_camera(token: str) -> None:
    with _DB_LOCK, _connection() as conn:
        conn.execute("DELETE FROM cameras WHERE token = ?", (token,))
        conn.commit()


def list_cameras() -> List[Camera]:
    with _DB_LOCK, _connection() as conn:
        rows = conn.execute("SELECT token, rtsp_url, status FROM cameras").fetchall()
    return [Camera(*row) for row in rows]
