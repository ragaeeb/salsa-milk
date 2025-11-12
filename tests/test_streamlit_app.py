from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

import streamlit_app


class FakeUpload:
    def __init__(self, name: str, data: bytes):
        self.name = name
        self._data = data

    def getbuffer(self):
        return memoryview(self._data)


class FakeStreamlit:
    def __init__(self):
        self.downloads = []
        self.warning_messages = []
        self.error_messages = []
        self.success_messages = []
        self.spinner_messages = []

    def set_page_config(self, **_kwargs):
        pass

    def title(self, *_args, **_kwargs):
        pass

    def caption(self, *_args, **_kwargs):
        pass

    def write(self, *_args, **_kwargs):
        pass

    def file_uploader(self, *_args, **_kwargs):
        return [FakeUpload("song.mp3", b"data")]

    def text_area(self, *_args, **_kwargs):
        return "https://www.youtube.com/watch?v=abc"

    def selectbox(self, *_args, **_kwargs):
        return "htdemucs"

    def button(self, *_args, **_kwargs):
        return True

    def spinner(self, message: str):
        self.spinner_messages.append(message)

        class Dummy:
            def __enter__(self_inner):
                return None

            def __exit__(self_inner, exc_type, exc, tb):
                return False

        return Dummy()

    def warning(self, message: str):
        self.warning_messages.append(message)

    def error(self, message: str):  # pragma: no cover - used by guarded UI paths
        self.error_messages.append(message)

    def success(self, message: str):
        self.success_messages.append(message)

    def download_button(self, label: str, data: bytes, file_name: str, mime: str):
        self.downloads.append((label, data, file_name, mime))


def test_guess_mime_defaults():
    assert streamlit_app._guess_mime(Path("track.unknown")) == "application/octet-stream"
    assert streamlit_app._guess_mime(Path("track.mp3")) == "audio/mpeg"


def test_save_uploaded_files(tmp_path):
    upload = FakeUpload("track.mp3", b"abc")
    saved = streamlit_app._save_uploaded_files([upload], tmp_path)
    assert Path(saved[0]).read_bytes() == b"abc"


def test_save_uploaded_files_requires_buffer(tmp_path):
    class InvalidUpload:
        name = "test.mp3"

    with pytest.raises(AttributeError):
        streamlit_app._save_uploaded_files([InvalidUpload()], tmp_path)


def test_process_submission_success(tmp_path):
    upload = FakeUpload("track.mp3", b"abc")

    def fake_process(paths, **kwargs):
        output = Path(kwargs["output_dir"]) / "result.wav"
        output.write_bytes(b"result")
        return [{"output": str(output)}]

    def fake_download(urls, download_dir):
        path = Path(download_dir) / "yt.mp4"
        path.write_bytes(b"yt")
        return [str(path)]

    results = streamlit_app._process_submission(
        [upload],
        "https://youtu.be/demo",
        "htdemucs",
        process_func=fake_process,
        download_func=fake_download,
        workdir_factory=lambda prefix: str(tmp_path / "workdir"),
    )

    assert len(results) == 1
    assert results[0].filename == "result.wav"
    assert results[0].data == b"result"
    assert not Path(tmp_path / "workdir").exists()


def test_process_submission_without_inputs(tmp_path):
    with pytest.raises(ValueError):
        streamlit_app._process_submission([], "", "htdemucs", workdir_factory=lambda prefix: str(tmp_path / "empty"))


def test_process_submission_without_media(tmp_path):
    with pytest.raises(ValueError):
        streamlit_app._process_submission(
            [],
            "   ",
            "htdemucs",
            download_func=lambda *_args, **_kwargs: [],
            workdir_factory=lambda prefix: str(tmp_path / "nomedia"),
        )


def test_process_submission_without_results(tmp_path):
    upload = FakeUpload("track.mp3", b"abc")

    with pytest.raises(RuntimeError):
        streamlit_app._process_submission(
            [upload],
            "",
            "htdemucs",
            process_func=lambda *_args, **_kwargs: [],
            download_func=lambda *_args, **_kwargs: [],
            workdir_factory=lambda prefix: str(tmp_path / "noresults"),
        )


def test_process_submission_requires_any_inputs(tmp_path, monkeypatch):
    upload = FakeUpload("track.mp3", b"abc")

    monkeypatch.setattr(streamlit_app, "_save_uploaded_files", lambda *_args, **_kwargs: [])

    with pytest.raises(ValueError):
        streamlit_app._process_submission(
            [upload],
            " ",
            "htdemucs",
            download_func=lambda *_args, **_kwargs: [],
            workdir_factory=lambda prefix: str(tmp_path / "novalid"),
        )


def test_run_streamlit_flow(monkeypatch):
    fake_st = FakeStreamlit()

    result = streamlit_app.DownloadableResult(
        filename="song.wav", data=b"data", mime="audio/wav"
    )

    monkeypatch.setattr(
        streamlit_app,
        "_process_submission",
        lambda *_args, **_kwargs: [result],
    )

    streamlit_app.run(fake_st)

    assert fake_st.downloads
    assert fake_st.success_messages


def test_run_streamlit_handles_value_error(monkeypatch):
    fake_st = FakeStreamlit()
    monkeypatch.setattr(
        streamlit_app,
        "_process_submission",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("no input")),
    )

    streamlit_app.run(fake_st)

    assert fake_st.warning_messages == ["no input"]
    assert not fake_st.downloads


def test_run_imports_streamlit_module(monkeypatch):
    class StubStreamlit:
        def __init__(self):
            self.configured = False

        def set_page_config(self, **_kwargs):
            self.configured = True

        def title(self, *_args, **_kwargs):
            pass

        def caption(self, *_args, **_kwargs):
            pass

        def write(self, *_args, **_kwargs):
            pass

        def file_uploader(self, *_args, **_kwargs):
            return []

        def text_area(self, *_args, **_kwargs):
            return ""

        def selectbox(self, *_args, **_kwargs):
            return "htdemucs"

        def button(self, *_args, **_kwargs):
            return False

    stub = StubStreamlit()
    monkeypatch.setitem(sys.modules, "streamlit", stub)

    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    for handler in original_handlers:
        root_logger.removeHandler(handler)

    streamlit_app.run()

    for handler in original_handlers:
        root_logger.addHandler(handler)

    assert stub.configured
