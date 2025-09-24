"""Configuration management for the rtsp2jpg service."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Service settings sourced from environment variables and optional .env file."""

    db_path: str = Field(default="cameras.db", description="SQLite database file path")
    read_throttle_sec: float = Field(default=0.08, description="Delay between frame reads")
    reconnect_delay_sec: float = Field(default=2.0, description="Delay before reconnecting after failure")
    open_test_timeout_sec: float = Field(default=4.0, description="Timeout for backend open test")
    register_test_frames: int = Field(default=3, description="Number of frames to read on registration test")
    ffmpeg_first: bool = Field(default=True, description="Prefer FFmpeg backend when available")
    jpeg_quality: int = Field(default=85, description="JPEG quality for encoded snapshots")
    log_level: str = Field(default="INFO", description="Base logging level")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="RTSP2JPG_",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()
