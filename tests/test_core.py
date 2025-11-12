from __future__ import annotations

import io
import subprocess
import time
from pathlib import Path

import pytest

import salsa_milk_core as core


def test_process_files_empty_returns_list():
    assert core.process_files([]) == []


def test_process_files_audio_success(tmp_path, monkeypatch):
    audio_path = tmp_path / "song.mp3"
    audio_path.write_bytes(b"data")
    temp_dir = tmp_path / "temp"
    output_dir = tmp_path / "output"

    def fake_run(cmd, check):
        if cmd[0] == "ffmpeg" and cmd[-1].endswith(".wav"):
            Path(cmd[-1]).parent.mkdir(parents=True, exist_ok=True)
            Path(cmd[-1]).write_bytes(b"wav")
        elif cmd[0] == "ffmpeg":
            Path(cmd[-1]).parent.mkdir(parents=True, exist_ok=True)
            Path(cmd[-1]).write_bytes(b"final")
        else:  # pragma: no cover - guard for unexpected commands during tests
            raise AssertionError(f"Unexpected command: {cmd}")

    monkeypatch.setattr(core.subprocess, "run", fake_run)

    class FakeProc:
        def __init__(self, *_args, **_kwargs):
            vocals_path = temp_dir / "demucs" / "htdemucs" / audio_path.stem / "vocals.wav"
            vocals_path.parent.mkdir(parents=True, exist_ok=True)
            vocals_path.write_bytes(b"vocals")
            self.stderr = io.StringIO("10%\n100%\n")
            self.stdout = io.StringIO("")

        def wait(self):
            return 0

    monkeypatch.setattr(core.subprocess, "Popen", lambda *args, **kwargs: FakeProc())

    results = core.process_files(
        [audio_path],
        temp_dir=temp_dir,
        output_dir=output_dir,
        enable_progress=False,
    )

    assert len(results) == 1
    expected_output = output_dir / f"{audio_path.stem}_vocals.mp3"
    assert Path(results[0]["output"]) == expected_output
    assert expected_output.exists()


def test_process_files_video_with_alternate_vocals(tmp_path, monkeypatch):
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"video")
    temp_dir = tmp_path / "temp"
    output_dir = tmp_path / "output"
    alt_vocals = temp_dir / "demucs" / "alt" / video_path.stem / "vocals.wav"

    def fake_run(cmd, check):
        if cmd[0] == "ffmpeg" and cmd[-1].endswith(".wav"):
            Path(cmd[-1]).parent.mkdir(parents=True, exist_ok=True)
            Path(cmd[-1]).write_bytes(b"wav")
        elif cmd[0] == "ffmpeg":
            Path(cmd[-1]).parent.mkdir(parents=True, exist_ok=True)
            Path(cmd[-1]).write_bytes(b"video")
        else:  # pragma: no cover - guard for unexpected commands during tests
            raise AssertionError(f"Unexpected command: {cmd}")

    monkeypatch.setattr(core.subprocess, "run", fake_run)
    monkeypatch.setattr(core.glob, "glob", lambda pattern: [str(alt_vocals)])

    class FakeProc:
        def __init__(self, *_args, **_kwargs):
            alt_vocals.parent.mkdir(parents=True, exist_ok=True)
            alt_vocals.write_bytes(b"vocals")
            self.stderr = io.StringIO("25%\n75%\n100%\n")
            self.stdout = io.StringIO("")

        def wait(self):
            return 0

    monkeypatch.setattr(core.subprocess, "Popen", lambda *args, **kwargs: FakeProc())

    results = core.process_files([video_path], temp_dir=temp_dir, output_dir=output_dir)

    assert len(results) == 1
    assert results[0]["output"].endswith(".mp4")


def test_process_files_handles_subprocess_errors(tmp_path, monkeypatch, caplog):
    media_path = tmp_path / "broken.wav"
    media_path.write_bytes(b"broken")

    def fake_run(cmd, check):
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd)

    monkeypatch.setattr(core.subprocess, "run", fake_run)
    caplog.set_level("ERROR")

    results = core.process_files([media_path], temp_dir=tmp_path / "temp", output_dir=tmp_path / "out")

    assert results == []
    assert "Processing failed" in caplog.text


def test_process_files_missing_vocals_skips_entry(tmp_path, monkeypatch, caplog):
    audio_path = tmp_path / "song.mp3"
    audio_path.write_bytes(b"data")
    temp_dir = tmp_path / "temp"
    output_dir = tmp_path / "output"

    def fake_run(cmd, check):
        if cmd[0] == "ffmpeg" and cmd[-1].endswith(".wav"):
            Path(cmd[-1]).parent.mkdir(parents=True, exist_ok=True)
            Path(cmd[-1]).write_bytes(b"wav")
        else:  # pragma: no cover - guard for unexpected commands during tests
            raise AssertionError

    monkeypatch.setattr(core.subprocess, "run", fake_run)
    monkeypatch.setattr(core.glob, "glob", lambda pattern: [])

    class FakeProc:
        def __init__(self, *_args, **_kwargs):
            self.stderr = io.StringIO("")
            self.stdout = io.StringIO("")

        def wait(self):
            return 0

    monkeypatch.setattr(core.subprocess, "Popen", lambda *args, **kwargs: FakeProc())
    caplog.set_level("WARNING")

    results = core.process_files([audio_path], temp_dir=temp_dir, output_dir=output_dir)

    assert results == []
    assert "Could not find extracted vocals" in caplog.text


def test_process_files_uses_progress_bar_and_codecs(tmp_path, monkeypatch):
    aac_path = tmp_path / "clip.aac"
    ogg_path = tmp_path / "clip.ogg"
    for media in (aac_path, ogg_path):
        media.write_bytes(b"data")

    temp_dir = tmp_path / "temp"
    output_dir = tmp_path / "output"

    codecs_seen = []

    def fake_run(cmd, check):
        target = Path(cmd[-1])
        if cmd[0] == "ffmpeg" and target.suffix == ".wav":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"wav")
        elif cmd[0] == "ffmpeg":
            codec_index = cmd.index("-c:a") + 1
            codecs_seen.append(cmd[codec_index])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"output")
        else:  # pragma: no cover - guard for unexpected commands during tests
            raise AssertionError

    def fake_tqdm(iterable, desc):
        assert desc == "Processing files"
        fake_tqdm.called = True
        return list(iterable)

    fake_tqdm.called = False

    monkeypatch.setattr(core.subprocess, "run", fake_run)
    monkeypatch.setattr(core, "tqdm", fake_tqdm)

    class FakeProc:
        def __init__(self, args, **_kwargs):
            track_name = Path(args[-1]).stem
            vocals_path = temp_dir / "demucs" / "htdemucs" / track_name / "vocals.wav"
            vocals_path.parent.mkdir(parents=True, exist_ok=True)
            vocals_path.write_bytes(b"vocals")
            self.stderr = io.StringIO("50%\n100%\n")
            self.stdout = io.StringIO("")

        def wait(self):
            return 0

    monkeypatch.setattr(core.subprocess, "Popen", lambda *args, **kwargs: FakeProc(args[0]))

    results = core.process_files(
        [aac_path, ogg_path],
        temp_dir=temp_dir,
        output_dir=output_dir,
        enable_progress=True,
    )

    assert fake_tqdm.called
    assert len(results) == 2
    assert set(codecs_seen) == {"aac", "libopus"}


def test_process_files_emits_progress_updates(tmp_path, monkeypatch):
    audio_path = tmp_path / "song.mp3"
    audio_path.write_bytes(b"data")
    temp_dir = tmp_path / "temp"
    output_dir = tmp_path / "output"

    def fake_run(cmd, check):
        if cmd[0] == "ffmpeg" and cmd[-1].endswith(".wav"):
            Path(cmd[-1]).parent.mkdir(parents=True, exist_ok=True)
            Path(cmd[-1]).write_bytes(b"wav")
        elif cmd[0] == "ffmpeg":
            Path(cmd[-1]).parent.mkdir(parents=True, exist_ok=True)
            Path(cmd[-1]).write_bytes(b"final")

    class FakeProc:
        def __init__(self, *_args, **_kwargs):
            vocals_path = temp_dir / "demucs" / "htdemucs" / audio_path.stem / "vocals.wav"
            vocals_path.parent.mkdir(parents=True, exist_ok=True)
            vocals_path.write_bytes(b"vocals")
            self.stderr = io.StringIO("20%\n60%\n100%\n")
            self.stdout = io.StringIO("")

        def wait(self):
            return 0

    monkeypatch.setattr(core.subprocess, "run", fake_run)
    monkeypatch.setattr(core.subprocess, "Popen", lambda *args, **kwargs: FakeProc())

    events = []

    core.process_files(
        [audio_path],
        temp_dir=temp_dir,
        output_dir=output_dir,
        progress_callback=lambda stage, fraction, message: events.append((stage, fraction, message)),
    )

    assert any(stage == "demucs" for stage, _, _ in events)
    assert events[-1][0] == "complete"
    assert events[-1][1] == pytest.approx(1.0)


def test_download_from_youtube_handles_various_urls(tmp_path, monkeypatch):
    urls = " https://www.youtube.com/watch?v=abc123  https://youtu.be/xyz789 \nhttps://example.com/video "
    monkeypatch.setattr(time, "time", lambda: 42)

    def fake_run(cmd, check):
        output_index = cmd.index("--output") + 1
        Path(cmd[output_index]).parent.mkdir(parents=True, exist_ok=True)
        Path(cmd[output_index]).write_bytes(b"video")

    monkeypatch.setattr(core.subprocess, "run", fake_run)

    results = core.download_from_youtube(urls, download_dir=tmp_path)

    expected_files = {
        tmp_path / "abc123.mp4",
        tmp_path / "xyz789.mp4",
        tmp_path / "yt_42.mp4",
    }
    assert set(map(Path, results)) == expected_files


def test_download_from_youtube_handles_failures(tmp_path, monkeypatch, caplog):
    caplog.set_level("ERROR")
    calls = 0

    def fake_run(cmd, check):
        nonlocal calls
        calls += 1
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd)

    monkeypatch.setattr(core.subprocess, "run", fake_run)

    results = core.download_from_youtube(["https://youtu.be/fail", ""], download_dir=tmp_path)

    assert results == []
    assert "Failed to download" in caplog.text
    assert calls == 1


def test_download_from_youtube_empty_input():
    assert core.download_from_youtube([]) == []


def test_download_from_youtube_reports_missing_file(tmp_path, monkeypatch, caplog):
    caplog.set_level("ERROR")

    def fake_run(cmd, check):
        Path(cmd[cmd.index("--output") + 1]).parent.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(core.subprocess, "run", fake_run)

    results = core.download_from_youtube(["https://youtu.be/missing"], download_dir=tmp_path)

    assert results == []
    assert "Download reported success" in caplog.text
