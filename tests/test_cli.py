from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


CLI_SPEC = importlib.util.spec_from_file_location("salsa_milk_cli", Path("salsa-milk.py"))
CLI_MODULE = importlib.util.module_from_spec(CLI_SPEC)
assert CLI_SPEC.loader is not None
CLI_SPEC.loader.exec_module(CLI_MODULE)  # type: ignore[assignment]


def test_cli_handles_missing_files(tmp_path, monkeypatch, caplog):
    missing = tmp_path / "missing.mp3"
    output_dir = tmp_path / "output"
    download_dir = tmp_path / "downloads"
    temp_dir = tmp_path / "temp"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "salsa-milk.py",
            str(missing),
            "--output-dir",
            str(output_dir),
            "--download-dir",
            str(download_dir),
            "--temp-dir",
            str(temp_dir),
        ],
    )

    monkeypatch.setattr(CLI_MODULE, "download_from_youtube", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        CLI_MODULE,
        "process_files",
        lambda *_args, **_kwargs: [],
    )

    caplog.set_level("INFO")

    with pytest.raises(SystemExit) as exc:
        CLI_MODULE.main()

    assert exc.value.code == 1
    assert "No valid input files" in caplog.text


def test_cli_success_flow(tmp_path, monkeypatch, caplog):
    local_file = tmp_path / "local.wav"
    local_file.write_bytes(b"data")

    output_dir = tmp_path / "output"
    download_dir = tmp_path / "downloads"
    temp_dir = tmp_path / "temp"
    output_file = output_dir / "local_vocals.wav"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_bytes(b"vocals")

    monkeypatch.setattr(
        CLI_MODULE,
        "download_from_youtube",
        lambda urls, download_dir: [str(download_dir / "yt.mp4")],
    )

    def fake_process(paths, **kwargs):
        return [{"output": str(output_file)}]

    monkeypatch.setattr(CLI_MODULE, "process_files", fake_process)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "salsa-milk.py",
            str(local_file),
            "https://youtu.be/demo",
            "--output-dir",
            str(output_dir),
            "--download-dir",
            str(download_dir),
            "--temp-dir",
            str(temp_dir),
        ],
    )

    caplog.set_level("INFO")
    CLI_MODULE.main()

    assert "Successfully processed" in caplog.text


def test_cli_exits_when_processing_returns_empty(tmp_path, monkeypatch, caplog):
    local_file = tmp_path / "local.wav"
    local_file.write_bytes(b"data")

    output_dir = tmp_path / "output"
    download_dir = tmp_path / "downloads"
    temp_dir = tmp_path / "temp"

    monkeypatch.setattr(
        CLI_MODULE,
        "download_from_youtube",
        lambda urls, download_dir: [],
    )

    monkeypatch.setattr(CLI_MODULE, "process_files", lambda *_args, **_kwargs: [])

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "salsa-milk.py",
            str(local_file),
            "--output-dir",
            str(output_dir),
            "--download-dir",
            str(download_dir),
            "--temp-dir",
            str(temp_dir),
        ],
    )

    caplog.set_level("INFO")

    with pytest.raises(SystemExit) as exc:
        CLI_MODULE.main()

    assert exc.value.code == 1
    assert "No files were successfully processed" in caplog.text


def test_cli_version_flag(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["salsa-milk.py", "--version"])
    with pytest.raises(SystemExit) as exc:
        CLI_MODULE.main()
    assert exc.value.code == 0
