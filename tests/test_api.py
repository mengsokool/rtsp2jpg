import importlib
from typing import List, Optional

import pytest
from fastapi.testclient import TestClient

from rtsp2jpg import backends, cache, config, worker
from rtsp2jpg import db as db_module
from rtsp2jpg.api import cameras, status as status_api


@pytest.fixture
def client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("RTSP2JPG_DB_PATH", str(tmp_path / "api.db"))
    config.get_settings.cache_clear()

    monkeypatch.setattr(worker, "start_worker", lambda *args, **kwargs: None)
    monkeypatch.setattr(worker, "stop_worker", lambda *args, **kwargs: None)

    app_module = importlib.import_module("rtsp2jpg.app")
    importlib.reload(app_module)
    with TestClient(app_module.app, raise_server_exceptions=False) as client:
        yield client

    cache.clear_all()
    config.get_settings.cache_clear()


def test_register_and_status_flow(client: TestClient, monkeypatch):
    monkeypatch.setattr(cameras, "choose_backend", lambda url, prefer=None: (None, "default"))
    response = client.post("/register", json={"rtsp_url": "rtsp://example"})
    assert response.status_code == 200
    token = response.json()["token"]
    assert response.json()["backend"] == "default"

    status = client.get(f"/status/{token}")
    assert status.status_code == 200
    payload = status.json()
    assert payload["status"] == "connecting"

    snapshot = client.get(f"/snapshot/{token}")
    assert snapshot.status_code == 503

    unregister = client.post(f"/unregister/{token}")
    assert unregister.status_code == 200
    assert unregister.json()["ok"] is True

    missing = client.get(f"/status/{token}")
    assert missing.status_code == 404


def test_register_failure(client: TestClient, monkeypatch):
    def _raise(*_args, **_kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(cameras, "choose_backend", _raise)

    response = client.post("/register", json={"rtsp_url": "rtsp://bad"})
    assert response.status_code == 400
    assert response.json()["detail"] == "boom"


def test_register_invalid_preference(client: TestClient):
    response = client.post("/register", json={"rtsp_url": "rtsp://example", "prefer": "wtf"})
    assert response.status_code == 400


def test_register_db_failure_returns_500(client: TestClient, monkeypatch):
    monkeypatch.setattr(cameras, "choose_backend", lambda url, prefer=None: (None, "default"))

    def explode(*_args, **_kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(db_module, "add_camera", explode)

    response = client.post("/register", json={"rtsp_url": "rtsp://example"})
    assert response.status_code == 500


def test_snapshot_success(client: TestClient, monkeypatch):
    monkeypatch.setattr(cameras, "choose_backend", lambda url, prefer=None: (None, "default"))
    response = client.post("/register", json={"rtsp_url": "rtsp://example"})
    token = response.json()["token"]

    qualities: List[Optional[int]] = []

    def fake_get_jpeg(_token: str, quality: Optional[int] = None) -> Optional[bytes]:
        qualities.append(quality)
        return b"jpeg" if _token == token else None

    monkeypatch.setattr(cache, "get_jpeg", fake_get_jpeg)

    snapshot = client.get(f"/snapshot/{token}")
    assert snapshot.status_code == 200
    assert snapshot.content == b"jpeg"
    assert snapshot.headers["content-type"] == "image/jpeg"
    assert qualities == [100]


def test_snapshot_allows_quality_override(client: TestClient, monkeypatch):
    monkeypatch.setattr(cameras, "choose_backend", lambda url, prefer=None: (None, "default"))
    response = client.post("/register", json={"rtsp_url": "rtsp://example"})
    token = response.json()["token"]

    qualities: List[Optional[int]] = []

    def fake_get_jpeg(_token: str, quality: Optional[int] = None) -> Optional[bytes]:
        qualities.append(quality)
        return b"jpeg" if _token == token else None

    monkeypatch.setattr(cache, "get_jpeg", fake_get_jpeg)

    snapshot = client.get(f"/snapshot/{token}?q=25")
    assert snapshot.status_code == 200
    assert snapshot.content == b"jpeg"
    assert snapshot.headers["content-type"] == "image/jpeg"
    assert qualities == [25]


def test_snapshot_allows_requesting_full_quality(client: TestClient, monkeypatch):
    monkeypatch.setattr(cameras, "choose_backend", lambda url, prefer=None: (None, "default"))
    response = client.post("/register", json={"rtsp_url": "rtsp://example"})
    token = response.json()["token"]

    qualities: List[Optional[int]] = []

    def fake_get_jpeg(_token: str, quality: Optional[int] = None) -> Optional[bytes]:
        qualities.append(quality)
        return b"jpeg" if _token == token else None

    monkeypatch.setattr(cache, "get_jpeg", fake_get_jpeg)

    snapshot = client.get(f"/snapshot/{token}?q=100")
    assert snapshot.status_code == 200
    assert snapshot.content == b"jpeg"
    assert snapshot.headers["content-type"] == "image/jpeg"
    assert qualities == [100]


def test_status_reflects_cache_error(client: TestClient, monkeypatch):
    monkeypatch.setattr(cameras, "choose_backend", lambda url, prefer=None: (None, "default"))
    response = client.post("/register", json={"rtsp_url": "rtsp://example"})
    token = response.json()["token"]

    cache.set_status(token, "error", "fail")
    status = client.get(f"/status/{token}")
    assert status.status_code == 200
    payload = status.json()
    assert payload["status"] == "error"
    assert payload["error"] == "fail"


def test_status_defaults_to_unknown_when_cache_empty(client: TestClient, monkeypatch):
    monkeypatch.setattr(cameras, "choose_backend", lambda url, prefer=None: (None, "default"))
    response = client.post("/register", json={"rtsp_url": "rtsp://example"})
    token = response.json()["token"]

    cache.clear(token)

    monkeypatch.setattr(status_api, "backend_flag_for", lambda _token: 42 if _token == token else None)

    status = client.get(f"/status/{token}")
    assert status.status_code == 200
    payload = status.json()
    assert payload["status"] == "unknown"
    assert payload["backend"] == "flag:42"
    assert payload["last_seen"] is None


def test_unregister_missing_token(client: TestClient):
    response = client.post("/unregister/missing")
    assert response.status_code == 200
    payload = response.json()
    assert payload == {"ok": True, "message": "already removed"}


def test_health_endpoint(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert "backends_built" in payload


def test_register_with_preference_invokes_worker(client: TestClient, monkeypatch):
    start_calls: List[tuple] = []

    def fake_start(token: str, url: str, backend_flag, *, autodetect: bool = False):
        start_calls.append((token, url, backend_flag, autodetect))

    monkeypatch.setattr(worker, "start_worker", fake_start)
    monkeypatch.setattr(worker, "stop_worker", lambda *_, **__: None)
    monkeypatch.setattr(
        cameras,
        "choose_backend",
        lambda url, prefer=None: (backends.cv2.CAP_FFMPEG, "ffmpeg"),
    )

    response = client.post(
        "/register",
        json={"rtsp_url": "rtsp://example", "prefer": "ffmpeg"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["backend"] == "ffmpeg"
    assert len(start_calls) == 1
    token, url, backend_flag, autodetect = start_calls[0]
    assert token == payload["token"]
    assert url == "rtsp://example"
    assert backend_flag == backends.cv2.CAP_FFMPEG
    assert autodetect is False


def test_snapshot_unregistered_token_returns_503(client: TestClient, monkeypatch):
    monkeypatch.setattr(cameras, "choose_backend", lambda url, prefer=None: (None, "default"))
    response = client.post("/register", json={"rtsp_url": "rtsp://example"})
    token = response.json()["token"]

    with cache.CACHE_LOCK:
        cache.JPEG_CACHE[token] = b"jpeg"

    client.post(f"/unregister/{token}")

    assert cache.get_jpeg(token) is None
    snapshot = client.get(f"/snapshot/{token}")
    assert snapshot.status_code == 503


def test_unregister_stops_worker_and_clears_cache(client: TestClient, monkeypatch):
    monkeypatch.setattr(cameras, "choose_backend", lambda url, prefer=None: (None, "default"))
    start_calls: List[str] = []
    stop_calls: List[str] = []

    monkeypatch.setattr(worker, "start_worker", lambda token, *_: start_calls.append(token))
    monkeypatch.setattr(worker, "stop_worker", lambda token: stop_calls.append(token))

    response = client.post("/register", json={"rtsp_url": "rtsp://example"})
    token = response.json()["token"]

    cache.set_status(token, "active")
    with cache.CACHE_LOCK:
        cache.JPEG_CACHE[token] = b"jpeg"

    result = client.post(f"/unregister/{token}")
    assert result.status_code == 200
    assert stop_calls == [token]
    assert cache.get_jpeg(token) is None
    assert cache.get_status(token)["status"] == "unknown"


def test_snapshot_unknown_token_returns_503(client: TestClient):
    response = client.get("/snapshot/does-not-exist")
    assert response.status_code == 503


def test_status_includes_backend_and_last_seen(client: TestClient, monkeypatch):
    monkeypatch.setattr(cameras, "choose_backend", lambda url, prefer=None: (None, "default"))
    response = client.post("/register", json={"rtsp_url": "rtsp://example"})
    token = response.json()["token"]

    with cache.CACHE_LOCK:
        cache.LAST_SEEN_TS[token] = 123.0
    cache.set_status(token, "active")

    monkeypatch.setattr(
        status_api,
        "backend_flag_for",
        lambda _token: backends.cv2.CAP_GSTREAMER if _token == token else None,
    )

    status = client.get(f"/status/{token}")
    assert status.status_code == 200
    payload = status.json()
    assert payload["backend"] == "gstreamer"
    assert payload["last_seen"] == 123.0
    assert payload["status"] == "active"


def test_app_lifespan_triggers_cleanup(tmp_path, monkeypatch):
    monkeypatch.setenv("RTSP2JPG_DB_PATH", str(tmp_path / "life.db"))
    config.get_settings.cache_clear()

    app_module = importlib.import_module("rtsp2jpg.app")
    importlib.reload(app_module)

    stop_called = []
    clear_called = []
    init_called = []

    monkeypatch.setattr(app_module.worker, "stop_all_workers", lambda: stop_called.append(True))
    monkeypatch.setattr(app_module.cache, "clear_all", lambda: clear_called.append(True))

    original_init_db = app_module.db.init_db

    def _init_wrapper():
        init_called.append(True)
        original_init_db()

    monkeypatch.setattr(app_module.db, "init_db", _init_wrapper)

    app = app_module.create_app()

    with TestClient(app) as client:
        client.get("/health")

    assert stop_called
    assert clear_called
    assert init_called

    config.get_settings.cache_clear()
