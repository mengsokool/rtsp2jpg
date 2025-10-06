from rtsp2jpg import config, db


def test_db_crud(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("RTSP2JPG_DB_PATH", str(db_file))
    config.get_settings.cache_clear()

    db.init_db()
    token = "tok123"
    rtsp_url = "rtsp://example/stream"

    db.add_camera(token, rtsp_url, status="active")
    camera = db.get_camera(token)
    assert camera is not None
    assert camera.rtsp_url == rtsp_url
    assert camera.status == "active"

    cameras = db.list_cameras()
    assert cameras == [camera]

    db.update_status(token, "inactive")
    camera = db.get_camera(token)
    assert camera.status == "inactive"

    db.delete_camera(token)
    assert db.get_camera(token) is None
    assert db.list_cameras() == []

    config.get_settings.cache_clear()
