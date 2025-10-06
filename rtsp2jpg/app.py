"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI

from . import __version__, cache, db, worker
from .api import api_router
from .backends import choose_backend
from .logging_config import configure_logging

LOGGER = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI):  # pragma: no cover - FastAPI wiring
    db.init_db()

    for camera in db.list_cameras():
        backend_flag = None
        autodetect = False
        startup_error: Optional[str] = None

        try:
            backend_flag, _ = choose_backend(camera.rtsp_url)
        except ValueError as exc:
            autodetect = True
            startup_error = str(exc)
            LOGGER.error(
                "%s: failed to select backend during startup: %s", camera.token, exc
            )

        worker.start_worker(
            camera.token,
            camera.rtsp_url,
            backend_flag,
            autodetect=autodetect,
        )

        if startup_error is not None:
            cache.set_status(camera.token, "error", startup_error)
            db.update_status(camera.token, "error")

    try:
        yield
    finally:
        worker.stop_all_workers()
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
