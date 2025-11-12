"""Core processing utilities for the Salsa Milk project."""

from __future__ import annotations

import glob
import logging
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable, Iterable, List, Sequence

from tqdm import tqdm


logger = logging.getLogger("salsa-milk")


def _ensure_path(value: os.PathLike[str] | str) -> Path:
    """Return a Path instance for the provided value."""

    return value if isinstance(value, Path) else Path(value)


def process_files(
    input_files: Sequence[os.PathLike[str] | str],
    *,
    model: str = "htdemucs",
    temp_dir: os.PathLike[str] | str = "/tmp",
    output_dir: os.PathLike[str] | str = "/output",
    enable_progress: bool = False,
    progress_callback: Callable[[str, float, str | None], None] | None = None,
) -> List[dict]:
    """Process media files to isolate vocals using Demucs."""

    if not input_files:
        return []

    temp_root = _ensure_path(temp_dir)
    output_root = _ensure_path(output_dir)

    temp_audio_dir = temp_root / "audio"
    demucs_root = temp_root / "demucs"

    temp_audio_dir.mkdir(parents=True, exist_ok=True)
    demucs_root.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)

    files_iterable: Iterable[Path]
    path_inputs = [_ensure_path(path) for path in input_files]

    if enable_progress and len(path_inputs) > 1:
        files_iterable = tqdm(path_inputs, desc="Processing files")
    else:
        files_iterable = path_inputs

    results: List[dict] = []

    for index, file_path in enumerate(files_iterable):
        logger.info("Processing %s", file_path.name)
        file_id = file_path.stem
        has_video = file_path.suffix.lower() in {".mp4", ".mov", ".avi", ".mkv", ".webm"}

        wav_path = temp_audio_dir / f"{file_id}.wav"

        per_file_start = index / len(path_inputs)
        per_file_span = 1.0 / len(path_inputs)

        def emit(stage: str, fraction: float, message: str | None = None) -> None:
            if progress_callback is None:
                return
            bounded = max(0.0, min(1.0, per_file_start + per_file_span * fraction))
            progress_callback(stage, bounded, message)

        try:
            emit("prepare", 0.02, f"Preparing {file_path.name}")
            logger.info("Converting %s to WAV", file_path.name)
            ffmpeg_convert_cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(file_path),
                "-vn",
                "-acodec",
                "pcm_s16le",
                "-ar",
                "44100",
                "-ac",
                "2",
                str(wav_path),
            ]
            subprocess.run(ffmpeg_convert_cmd, check=True)
            emit("convert", 0.18, f"Converted {file_path.name} to WAV")

            logger.info("Running Demucs (%s) on %s", model, file_path.name)
            demucs_cmd = [
                "demucs",
                "--two-stems",
                "vocals",
                "-n",
                model,
                "-o",
                str(demucs_root),
                str(wav_path),
            ]
            emit("demucs", 0.22, f"Starting Demucs for {file_path.name}")

            demucs_proc = subprocess.Popen(
                demucs_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            demucs_stderr = demucs_proc.stderr
            if demucs_stderr is not None:
                for raw_line in iter(demucs_stderr.readline, ""):
                    if not raw_line:
                        break
                    line = raw_line.strip()
                    if line:
                        logger.info("demucs: %s", line)
                    match = re.search(r"(\d{1,3})%", raw_line)
                    if match:
                        percent = min(int(match.group(1)), 100)
                        demucs_fraction = 0.22 + 0.6 * (percent / 100)
                        emit(
                            "demucs",
                            demucs_fraction,
                            f"Demucs {percent}% for {file_path.name}",
                        )

            if demucs_proc.stdout is not None:
                demucs_proc.stdout.close()

            return_code = demucs_proc.wait()
            if return_code != 0:
                raise subprocess.CalledProcessError(return_code, demucs_cmd)

            emit("demucs", 0.82, f"Demucs complete for {file_path.name}")

            vocals_path = demucs_root / model / file_id / "vocals.wav"

            if not vocals_path.exists():
                potential_paths = glob.glob(str(demucs_root / "*" / file_id / "vocals.wav"))
                if potential_paths:
                    vocals_path = Path(potential_paths[0])
                    logger.info("Found vocals at alternate path: %s", vocals_path)
                else:
                    logger.warning("Could not find extracted vocals for %s", file_id)
                    continue

            if has_video:
                output_ext = "mp4"
                output_path = output_root / f"{file_id}_vocals.{output_ext}"
                ffmpeg_cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(file_path),
                    "-i",
                    str(vocals_path),
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-shortest",
                    str(output_path),
                ]
            else:
                original_ext = file_path.suffix.lower().lstrip(".")
                allowed_exts = {"mp3", "wav", "ogg", "m4a", "aac", "opus"}
                output_ext = original_ext if original_ext in allowed_exts else "wav"
                output_path = output_root / f"{file_id}_vocals.{output_ext}"

                codec = "copy"
                if output_ext == "mp3":
                    codec = "libmp3lame"
                elif output_ext in {"aac", "m4a"}:
                    codec = "aac"
                elif output_ext in {"ogg", "opus"}:
                    codec = "libopus"

                ffmpeg_cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(vocals_path),
                    "-c:a",
                    codec,
                    "-b:a",
                    "192k",
                    str(output_path),
                ]

            logger.info("Writing final output to %s", output_path)
            subprocess.run(ffmpeg_cmd, check=True)
            emit("mux", 0.95, f"Writing output for {file_path.name}")

            results.append({
                "input": str(file_path),
                "output": str(output_path),
                "id": file_id,
            })
            emit("file_complete", 1.0, f"Finished {file_path.name}")

        except subprocess.CalledProcessError as exc:
            logger.error("Processing failed for %s: %s", file_id, exc)
            emit("error", per_file_span, f"Processing failed for {file_path.name}")
        finally:
            if wav_path.exists():
                wav_path.unlink()

            demucs_candidate = demucs_root / model / file_id
            if demucs_candidate.exists():
                shutil.rmtree(demucs_candidate, ignore_errors=True)

    if progress_callback is not None:
        progress_callback("complete", 1.0, "All files processed.")

    return results


def download_from_youtube(
    urls: Sequence[str] | str,
    *,
    download_dir: os.PathLike[str] | str = "/media",
) -> List[str]:
    """Download videos from YouTube URLs and return local file paths."""

    if not urls:
        return []

    if isinstance(urls, str):
        urls = re.split(r"\s+", urls.strip())

    download_root = _ensure_path(download_dir)
    download_root.mkdir(parents=True, exist_ok=True)

    downloaded: List[str] = []

    for url in urls:
        url = url.strip()
        if not url:
            continue

        logger.info("Downloading from YouTube: %s", url)

        if "youtube.com/watch?v=" in url:
            video_id = url.split("youtube.com/watch?v=")[1].split("&")[0]
        elif "youtu.be/" in url:
            video_id = url.split("youtu.be/")[1].split("?")[0]
        else:
            video_id = f"yt_{int(time.time())}"

        output_path = download_root / f"{video_id}.mp4"
        cmd = [
            "yt-dlp",
            "-f",
            "b",
            "--output",
            str(output_path),
            "--no-check-certificate",
            "--geo-bypass",
            url,
        ]

        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as exc:
            logger.error("Failed to download %s: %s", url, exc)
            continue

        if output_path.exists():
            downloaded.append(str(output_path))
            logger.info("Downloaded %s to %s", video_id, output_path)
        else:
            logger.error("Download reported success but file missing: %s", output_path)

    return downloaded

