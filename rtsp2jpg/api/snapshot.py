"""Snapshot endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from .. import cache

router = APIRouter(tags=["snapshot"])


@router.get("/snapshot/{token}")
def snapshot(token: str) -> Response:
    jpeg = cache.get_jpeg(token)
    if not jpeg:
        raise HTTPException(status_code=503, detail="No frame available yet")
    return Response(content=jpeg, media_type="image/jpeg")
