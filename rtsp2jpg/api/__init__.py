"""API router composition."""

from __future__ import annotations

from fastapi import APIRouter

from . import cameras, snapshot, status

api_router = APIRouter()
api_router.include_router(cameras.router)
api_router.include_router(snapshot.router)
api_router.include_router(status.router)

__all__ = ["api_router"]
