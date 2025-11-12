from __future__ import annotations

import io
import logging
from pathlib import Path

from werkzeug.exceptions import RequestEntityTooLarge

import webapp


def test_allowed_file_extension_checks():
    assert webapp.allowed_file("track.mp3")
    assert not webapp.allowed_file("track.txt")


def build_app():
    app = webapp.create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return app


def test_get_request_serves_form(monkeypatch):
    app = build_app()
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"Upload" in response.data


def test_post_without_file(monkeypatch):
    app = build_app()
    client = app.test_client()
    response = client.post("/", data={}, content_type="multipart/form-data", follow_redirects=True)
    assert response.status_code == 200
    assert b"Please choose a media file" in response.data


def test_post_with_invalid_extension(monkeypatch):
    app = build_app()
    client = app.test_client()
    data = {"file": (io.BytesIO(b"abc"), "payload.txt")}
    response = client.post("/", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert response.status_code == 200
    assert b"Unsupported file type" in response.data


def test_successful_processing(monkeypatch, tmp_path):
    app = build_app()
    client = app.test_client()

    output_file = tmp_path / "result.wav"
    output_file.write_bytes(b"audio")

    def fake_process(paths, **kwargs):
        return [{"output": str(output_file)}]

    monkeypatch.setattr(webapp, "process_files", fake_process)

    data = {"file": (io.BytesIO(b"abc"), "payload.mp3")}
    response = client.post("/", data=data, content_type="multipart/form-data")

    assert response.status_code == 200
    assert response.headers.get("Content-Disposition") is not None
    assert response.data == b"audio"


def test_processing_failure(monkeypatch, tmp_path):
    app = build_app()
    client = app.test_client()

    def fake_process(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(webapp, "process_files", fake_process)

    data = {"file": (io.BytesIO(b"abc"), "payload.mp3")}
    response = client.post("/", data=data, content_type="multipart/form-data", follow_redirects=True)

    assert response.status_code == 200
    assert b"Processing failed" in response.data


def test_post_without_results(monkeypatch):
    app = build_app()
    client = app.test_client()

    monkeypatch.setattr(webapp, "process_files", lambda *_args, **_kwargs: [])

    data = {"file": (io.BytesIO(b"abc"), "payload.mp3")}
    response = client.post("/", data=data, content_type="multipart/form-data", follow_redirects=True)

    assert response.status_code == 200
    assert b"No output was produced" in response.data


def test_error_handler_redirects():
    app = build_app()
    with app.test_request_context("/"):
        response = app.handle_user_exception(RequestEntityTooLarge())
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_create_app_configures_logging(monkeypatch):
    recorded = {}

    def fake_basic_config(**kwargs):
        recorded["called"] = kwargs

    monkeypatch.setattr(logging, "basicConfig", fake_basic_config)

    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    for handler in original_handlers:
        root_logger.removeHandler(handler)

    try:
        webapp.create_app()
    finally:
        for handler in original_handlers:
            root_logger.addHandler(handler)

    assert recorded["called"] == {"level": logging.INFO}
