from __future__ import annotations

import io
import logging

import pytest

werkzeug_exceptions = pytest.importorskip("werkzeug.exceptions")
RequestEntityTooLarge = werkzeug_exceptions.RequestEntityTooLarge

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


class ImmediateThread:
    def __init__(self, target=None, args=None, kwargs=None, daemon=None):
        self._target = target
        self._args = args or ()
        self._kwargs = kwargs or {}

    def start(self):
        if self._target:
            self._target(*self._args, **self._kwargs)


def clear_tasks():
    with webapp._TASK_LOCK:  # type: ignore[attr-defined]
        task_ids = list(webapp._TASKS.keys())  # type: ignore[attr-defined]

    for task_id in task_ids:
        webapp._finalize_task(task_id)  # type: ignore[attr-defined]


def test_post_without_file(monkeypatch):
    app = build_app()
    client = app.test_client()
    response = client.post("/api/process", data={}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert response.get_json()["error"] == "no_file"


def test_post_with_invalid_extension(monkeypatch):
    app = build_app()
    client = app.test_client()
    data = {"file": (io.BytesIO(b"abc"), "payload.txt")}
    response = client.post("/api/process", data=data, content_type="multipart/form-data")
    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_type"


def test_successful_processing(monkeypatch, tmp_path):
    app = build_app()
    client = app.test_client()

    output_file = tmp_path / "result.wav"
    output_file.write_bytes(b"audio")

    def fake_process(paths, **kwargs):
        progress = kwargs.get("progress_callback")
        if progress:
            progress("prepare", 0.1, "Preparing file")
            progress("demucs", 0.5, "Demucs 50%")
        return [{"output": str(output_file)}]

    monkeypatch.setattr(webapp, "process_files", fake_process)
    monkeypatch.setattr(webapp.threading, "Thread", ImmediateThread)

    data = {"file": (io.BytesIO(b"abc"), "payload.mp3")}
    response = client.post("/api/process", data=data, content_type="multipart/form-data")
    payload = response.get_json()
    assert response.status_code == 200
    task_id = payload["task_id"]

    progress = client.get(f"/api/progress/{task_id}").get_json()
    assert progress["status"] == "completed"
    assert progress["download_ready"]
    assert "Demucs" in progress["message"]

    download = client.get(f"/api/download/{task_id}")
    assert download.status_code == 200
    assert download.data == b"audio"

    clear_tasks()


def test_processing_failure(monkeypatch, tmp_path):
    app = build_app()
    client = app.test_client()

    def fake_process(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(webapp, "process_files", fake_process)
    monkeypatch.setattr(webapp.threading, "Thread", ImmediateThread)

    data = {"file": (io.BytesIO(b"abc"), "payload.mp3")}
    response = client.post("/api/process", data=data, content_type="multipart/form-data")
    task_id = response.get_json()["task_id"]

    progress = client.get(f"/api/progress/{task_id}").get_json()
    assert progress["status"] == "error"
    assert "failed" in progress["message"].lower()

    clear_tasks()


def test_post_without_results(monkeypatch):
    app = build_app()
    client = app.test_client()

    monkeypatch.setattr(webapp, "process_files", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(webapp.threading, "Thread", ImmediateThread)

    data = {"file": (io.BytesIO(b"abc"), "payload.mp3")}
    response = client.post("/api/process", data=data, content_type="multipart/form-data")
    task_id = response.get_json()["task_id"]

    progress = client.get(f"/api/progress/{task_id}").get_json()
    assert progress["status"] == "error"
    assert "No output" in progress["message"]

    clear_tasks()


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
