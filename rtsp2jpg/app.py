"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

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
        try:
            backend_flag, _ = choose_backend(camera.rtsp_url)
        except ValueError as exc:
            cache.set_status(camera.token, "error", str(exc))
            db.update_status(camera.token, "error")
            LOGGER.error("%s: failed to select backend during startup: %s", camera.token, exc)
            continue

        worker.start_worker(camera.token, camera.rtsp_url, backend_flag)

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
