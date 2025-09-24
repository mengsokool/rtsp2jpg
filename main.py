"""Compatibility wrapper exposing FastAPI app for uvicorn."""

from __future__ import annotations
from rtsp2jpg.app import app

__all__ = ["app"]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
