"""Snapshot endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from .. import cache

router = APIRouter(tags=["snapshot"])


@router.get("/snapshot/{token}")
def snapshot(token: str, q: int = Query(default=100, ge=1, le=100)) -> Response:
    quality = None if q == 100 else q
    jpeg = cache.get_jpeg(token, quality=quality)
    if not jpeg:
        raise HTTPException(status_code=503, detail="No frame available yet")
    return Response(content=jpeg, media_type="image/jpeg")
