"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import __version__, cache
from .api import api_router
from .db import init_db
from .logging_config import configure_logging
from .worker import stop_all_workers


@asynccontextmanager
async def _lifespan(app: FastAPI):  # pragma: no cover - FastAPI wiring
    init_db()
    try:
        yield
    finally:
        stop_all_workers()
        cache.clear_all()


def create_app() -> FastAPI:
    """Construct and return a FastAPI application instance."""

    configure_logging()

    app = FastAPI(
        title="RTSP Snapshot Service",
        version=__version__,
        description="Expose RTSP streams as cached JPEG snapshots with backend auto-detect.",
        lifespan=_lifespan,
    )
    app.include_router(api_router)

    return app


app = create_app()
