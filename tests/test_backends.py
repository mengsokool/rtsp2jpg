from rtsp2jpg import backends, config


class DummyCap:
    def __init__(self, succeed: bool = True):
        self._succeed = succeed

    def isOpened(self):
        return self._succeed

    def read(self):
        return True, object()

    def release(self):
        pass

    def set(self, *args, **kwargs):
        pass


def test_choose_backend_with_preference(monkeypatch):
    config.get_settings.cache_clear()

    monkeypatch.setattr(backends, "_try_open", lambda *args, **kwargs: DummyCap())

    backend_flag, backend_label = backends.choose_backend("rtsp://example", prefer="ffmpeg")
    assert backend_flag == backends.cv2.CAP_FFMPEG
    assert backend_label == "ffmpeg"

    backend_flag, backend_label = backends.choose_backend("rtsp://example", prefer="gstreamer")
    assert backend_flag == backends.cv2.CAP_GSTREAMER
    assert backend_label == "gstreamer"


def test_choose_backend_auto(monkeypatch):
    config.get_settings.cache_clear()

    attempts = []

    def fake_try(rtsp_url, backend_flag, quick):
        attempts.append(backend_flag)
        if backend_flag is None:
            return DummyCap()
        return None

    monkeypatch.setattr(backends, "_try_open", fake_try)
    monkeypatch.setattr(backends, "build_supports", lambda: {"ffmpeg": False, "gstreamer": False})

    backend_flag, backend_label = backends.choose_backend("rtsp://example")
    assert backend_flag is None
    assert backend_label == "default"
    assert attempts[-1] is None
