"""Service health and status endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import cache, db
from ..backends import backend_name, build_supports
from ..worker import backend_flag_for

router = APIRouter(tags=["status"])


@router.get("/health")
def health() -> dict:
    return {"ok": True, "backends_built": build_supports()}


@router.get("/status/{token}")
def status(token: str) -> dict:
    camera = db.get_camera(token)
    if not camera:
        raise HTTPException(status_code=404, detail="Invalid token")

    status_info = cache.get_status(token)
    backend = backend_name(backend_flag_for(token))

    return {
        "token": token,
        "status": status_info["status"],
        "last_seen": status_info["last_seen"],
        "backend": backend,
        "error": status_info["error"],
    }
