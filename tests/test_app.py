import importlib

from fastapi.testclient import TestClient

from rtsp2jpg import cache, config, db, worker


def _reload_app():
    return importlib.reload(importlib.import_module("rtsp2jpg.app"))


def test_lifespan_restores_registered_cameras(tmp_path, monkeypatch):
    db_file = tmp_path / "restore.db"
    monkeypatch.setenv("RTSP2JPG_DB_PATH", str(db_file))
    config.get_settings.cache_clear()
    cache.clear_all()

    db.init_db()
    token = "tok123"
    rtsp_url = "rtsp://example/stream"
    db.add_camera(token, rtsp_url, status="inactive")

    start_calls = []

    def fake_start(token_arg, url_arg, backend_flag, *, autodetect=False):
        start_calls.append((token_arg, url_arg, backend_flag, autodetect))

    monkeypatch.setattr(worker, "start_worker", fake_start)
    monkeypatch.setattr(worker, "stop_all_workers", lambda: None)
    original_clear_all = cache.clear_all
    monkeypatch.setattr(cache, "clear_all", lambda: None)

    app_module = _reload_app()
    monkeypatch.setattr(app_module, "choose_backend", lambda url, prefer=None: (42, "ffmpeg"))

    with TestClient(app_module.app, raise_server_exceptions=False):
        pass

    assert start_calls == [(token, rtsp_url, 42, False)]

    original_clear_all()
    config.get_settings.cache_clear()


def test_lifespan_marks_error_when_backend_unavailable(tmp_path, monkeypatch):
    db_file = tmp_path / "error.db"
    monkeypatch.setenv("RTSP2JPG_DB_PATH", str(db_file))
    config.get_settings.cache_clear()
    cache.clear_all()

    db.init_db()
    token = "tok456"
    rtsp_url = "rtsp://example/error"
    db.add_camera(token, rtsp_url, status="inactive")

    start_calls = []

    def fake_start(token_arg, url_arg, backend_flag, *, autodetect=False):
        start_calls.append((token_arg, url_arg, backend_flag, autodetect))

    monkeypatch.setattr(worker, "start_worker", fake_start)
    monkeypatch.setattr(worker, "stop_all_workers", lambda: None)
    original_clear_all = cache.clear_all
    monkeypatch.setattr(cache, "clear_all", lambda: None)

    app_module = _reload_app()

    def _raise(*_args, **_kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(app_module, "choose_backend", _raise)

    with TestClient(app_module.app, raise_server_exceptions=False):
        pass

    status = cache.get_status(token)
    assert status["status"] == "error"
    assert status["error"] == "boom"

    camera = db.get_camera(token)
    assert camera is not None
    assert camera.status == "error"

    assert start_calls == [(token, rtsp_url, None, True)]

    original_clear_all()
    cache.clear(token)
    config.get_settings.cache_clear()
