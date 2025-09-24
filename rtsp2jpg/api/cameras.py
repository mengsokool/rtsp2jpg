"""Camera registration endpoints."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field

from .. import cache, db, worker
from ..backends import choose_backend

router = APIRouter(tags=["cameras"])


class RegisterRequest(BaseModel):
    rtsp_url: str = Field(..., description="RTSP URL to register")
    prefer: Optional[str] = Field(
        default=None,
        description="Preferred backend (ffmpeg|gstreamer|default)",
    )


class RegisterResponse(BaseModel):
    token: str
    backend: str


class UnregisterResponse(BaseModel):
    ok: bool
    message: Optional[str] = None


@router.post("/register", response_model=RegisterResponse)
def register_camera(payload: RegisterRequest = Body(...)) -> RegisterResponse:
    try:
        backend_flag, backend_label = choose_backend(payload.rtsp_url, payload.prefer)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    token = str(uuid.uuid4())[:8]
    cache.set_status(token, "connecting")
    db.add_camera(token, payload.rtsp_url, status="connecting")
    worker.start_worker(token, payload.rtsp_url, backend_flag)

    return RegisterResponse(token=token, backend=backend_label)


@router.post("/unregister/{token}", response_model=UnregisterResponse)
def unregister_camera(token: str) -> UnregisterResponse:
    camera = db.get_camera(token)
    if not camera:
        return UnregisterResponse(ok=True, message="already removed")

    worker.stop_worker(token)
    cache.clear(token)
    db.delete_camera(token)
    return UnregisterResponse(ok=True)
