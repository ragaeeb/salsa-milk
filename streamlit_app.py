"""Streamlit interface for the Salsa Milk vocal isolation toolkit."""

from __future__ import annotations

import logging
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

from salsa_milk import __version__
from salsa_milk_core import download_from_youtube, process_files

logger = logging.getLogger("salsa-milk")


ALLOWED_EXTENSIONS = {
    "mp3",
    "wav",
    "ogg",
    "m4a",
    "aac",
    "opus",
    "flac",
    "mp4",
    "mov",
    "avi",
    "mkv",
    "webm",
}
AVAILABLE_MODELS = ["htdemucs"]


@dataclass
class DownloadableResult:
    """Represents an output artifact ready to be downloaded in Streamlit."""

    filename: str
    data: bytes
    mime: str


def _guess_mime(path: Path) -> str:
    """Return a best-effort MIME type based on the file suffix."""

    mapping = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".opus": "audio/ogg",
        ".flac": "audio/flac",
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".avi": "video/x-msvideo",
        ".mkv": "video/x-matroska",
        ".webm": "video/webm",
    }
    return mapping.get(path.suffix.lower(), "application/octet-stream")


def _save_uploaded_files(uploaded_files: Sequence[object], destination: Path) -> List[str]:
    """Persist uploaded files to disk and return their paths."""

    saved_paths: List[str] = []
    destination.mkdir(parents=True, exist_ok=True)

    for uploaded in uploaded_files:
        name = getattr(uploaded, "name", "uploaded")
        buffer = getattr(uploaded, "getbuffer", None)
        if buffer is None:
            raise AttributeError("Uploaded file does not provide getbuffer()")

        safe_name = Path(name).name
        target = destination / safe_name
        with target.open("wb") as handle:
            handle.write(bytes(buffer()))
        saved_paths.append(str(target))

    return saved_paths


def _process_submission(
    uploaded_files: Sequence[object],
    youtube_urls: str,
    model: str,
    *,
    process_func=process_files,
    download_func=download_from_youtube,
    workdir_factory=tempfile.mkdtemp,
) -> List[DownloadableResult]:
    """Coordinate downloads, processing, and packaging of results."""

    urls = youtube_urls.strip()
    if not uploaded_files and not urls:
        raise ValueError("Provide at least one uploaded file or YouTube URL.")

    work_dir = Path(workdir_factory(prefix="salsa-milk-streamlit-"))
    uploads_dir = work_dir / "uploads"
    downloads_dir = work_dir / "downloads"
    temp_dir = work_dir / "temp"
    output_dir = work_dir / "output"

    try:
        uploads_dir.mkdir(parents=True, exist_ok=True)
        downloads_dir.mkdir(parents=True, exist_ok=True)
        temp_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        local_paths = _save_uploaded_files(uploaded_files, uploads_dir)
        downloaded_paths = download_func(urls, download_dir=downloads_dir)
        all_inputs: List[str] = local_paths + downloaded_paths

        if not all_inputs:
            raise ValueError("No valid media was provided for processing.")

        results = process_func(
            all_inputs,
            model=model,
            temp_dir=temp_dir,
            output_dir=output_dir,
            enable_progress=False,
        )

        if not results:
            raise RuntimeError("Processing completed but no outputs were produced.")

        packaged: List[DownloadableResult] = []
        for result in results:
            output_path = Path(result["output"])
            data = output_path.read_bytes()
            packaged.append(
                DownloadableResult(
                    filename=output_path.name,
                    data=data,
                    mime=_guess_mime(output_path),
                )
            )

        return packaged

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def run(st_module=None) -> None:
    """Render the Streamlit user interface."""

    if st_module is None:
        import streamlit as st_module  # type: ignore[assignment]

    st = st_module

    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO)

    st.set_page_config(page_title="Salsa Milk", page_icon="🥛")
    st.title("Salsa Milk Vocal Remover")
    st.caption(f"Version {__version__}")
    st.write(
        "Upload audio/video files or provide YouTube URLs to isolate vocals using Demucs."
    )

    uploaded_files = st.file_uploader(
        "Choose media files",
        accept_multiple_files=True,
        type=sorted(ALLOWED_EXTENSIONS),
    )
    youtube_urls = st.text_area(
        "YouTube URLs (one per line)",
        placeholder="https://www.youtube.com/watch?v=...",
    )
    model = st.selectbox("Demucs model", AVAILABLE_MODELS, index=0)

    process_clicked = st.button("Process Media")

    if process_clicked:
        with st.spinner("Processing media, this may take a few minutes..."):
            try:
                results = _process_submission(uploaded_files or [], youtube_urls, model)
            except ValueError as exc:
                st.warning(str(exc))
                return
            except Exception as exc:  # pragma: no cover - surfaced through UI
                logger.exception("Streamlit processing failed: %s", exc)
                st.error("Processing failed. Please try again.")
                return

        st.success("Processing complete!")
        for index, result in enumerate(results, start=1):
            st.download_button(
                label=f"Download result {index}: {result.filename}",
                data=result.data,
                file_name=result.filename,
                mime=result.mime,
            )


if __name__ == "__main__":  # pragma: no cover - entry point for `streamlit run`
    run()
