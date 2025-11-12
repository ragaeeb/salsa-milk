"""Streamlit interface for the Salsa Milk vocal isolation toolkit."""

from __future__ import annotations

import logging
import shutil
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from string import Template
from typing import Callable, List, Sequence

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

ASSETS_DIR = Path(__file__).resolve().parent / "templates"


@dataclass
class DownloadableResult:
    """Represents an output artifact ready to be downloaded in Streamlit."""

    filename: str
    data: bytes
    mime: str


def _guess_mime(path: Path) -> str:
    """Return a best-effort MIME type based on the file suffix.
    
    Args:
        path: File path to determine MIME type for.
        
    Returns:
        MIME type string, defaults to 'application/octet-stream' if unknown.
    """
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
    """Persist uploaded files to disk and return their paths.
    
    Args:
        uploaded_files: Sequence of Streamlit uploaded file objects.
        destination: Directory to save files to.
        
    Returns:
        List of saved file paths.
        
    Raises:
        AttributeError: If uploaded file doesn't provide getbuffer() method.
    """
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


ProgressCallback = Callable[[str, float, str], None]


@lru_cache(maxsize=None)
def _read_asset(filename: str) -> str:
    """Return the contents of a UI asset located in the templates directory."""

    asset_path = ASSETS_DIR / filename
    if not asset_path.is_file():  # pragma: no cover - defensive in case of packaging issues
        raise FileNotFoundError(f"Missing Streamlit asset: {filename}")

    return asset_path.read_text(encoding="utf-8")


def _inject_css(st_module, filename: str) -> None:
    """Add CSS styles to the Streamlit app from an external file."""

    css = _read_asset(filename)
    render = getattr(st_module, "markdown", None)
    if render is not None:
        render(f"<style>{css}</style>", unsafe_allow_html=True)
        return

    fallback = getattr(st_module, "write", None)
    if fallback is not None:  # pragma: no cover - fallback for test doubles
        fallback(css)


def _inject_html(st_module, filename: str, **context: str) -> None:
    """Render an HTML fragment using ``string.Template`` substitution."""

    template = Template(_read_asset(filename))
    html = template.safe_substitute(**context)
    render = getattr(st_module, "markdown", None)
    if render is not None:
        render(html, unsafe_allow_html=True)
        return

    fallback = getattr(st_module, "write", None)
    if fallback is not None:  # pragma: no cover - fallback for test doubles
        fallback(html)


def _process_submission(
    uploaded_files: Sequence[object],
    youtube_urls: str,
    model: str,
    *,
    process_func=process_files,
    download_func=download_from_youtube,
    workdir_factory=tempfile.mkdtemp,
    progress_callback: ProgressCallback | None = None,
) -> List[DownloadableResult]:
    """Coordinate downloads, processing, and packaging of results.
    
    Args:
        uploaded_files: Sequence of uploaded file objects.
        youtube_urls: Newline-separated YouTube URLs.
        model: Demucs model name to use.
        process_func: Function to process files (default: process_files).
        download_func: Function to download from YouTube (default: download_from_youtube).
        workdir_factory: Factory function to create working directory.
        progress_callback: Optional callback for progress updates (stage, fraction, message).
        
    Returns:
        List of downloadable result objects.
        
    Raises:
        ValueError: If no valid media was provided.
        RuntimeError: If processing completed but no outputs were produced.
    """
    urls = youtube_urls.strip()
    if not uploaded_files and not urls:
        raise ValueError("Provide at least one uploaded file or YouTube URL.")

    def notify(stage: str, fraction: float, message: str) -> None:
        if progress_callback is None:
            return

        bounded = min(max(fraction, 0.0), 1.0)
        progress_callback(stage, bounded, message)

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

        notify("prepare", 0.05, "Preparing workspace...")

        local_paths = _save_uploaded_files(uploaded_files, uploads_dir)
        notify("uploads", 0.2, f"Saved {len(local_paths)} uploaded file(s)")

        downloaded_paths = download_func(urls, download_dir=downloads_dir)
        notify("downloads", 0.35, f"Fetched {len(downloaded_paths)} YouTube item(s)")
        all_inputs: List[str] = local_paths + downloaded_paths

        if not all_inputs:
            raise ValueError("No valid media was provided for processing.")

        notify(
            "processing_start",
            0.35,
            f"Running Demucs ({model}) on {len(all_inputs)} file(s)...",
        )

        def bridge(stage: str, fraction: float, message: str | None) -> None:
            scaled = 0.35 + 0.5 * min(max(fraction, 0.0), 1.0)
            notify(stage, scaled, message or f"Processing ({stage})...")

        results = process_func(
            all_inputs,
            model=model,
            temp_dir=temp_dir,
            output_dir=output_dir,
            enable_progress=False,
            progress_callback=bridge,
        )

        if not results:
            raise RuntimeError("Processing completed but no outputs were produced.")

        notify("packaging", 0.92, "Packaging results for download...")
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

        notify("complete", 1.0, "Processing complete!")
        return packaged

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def run(st_module=None) -> None:
    """Render the Streamlit user interface.
    
    Args:
        st_module: Streamlit module (defaults to importing streamlit).
    """
    if st_module is None:
        import streamlit as st_module  # type: ignore[assignment]

    st = st_module

    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO)

    st.set_page_config(
        page_title="Salsa Milk - Music Remover",
        page_icon="🥛",
        layout="centered",
    )

    _inject_css(st, "streamlit_styles.css")
    _inject_html(st, "streamlit_header.html")

    uploaded_files = st.file_uploader(
        "📁 Choose media files",
        accept_multiple_files=True,
        type=sorted(ALLOWED_EXTENSIONS),
        help="Upload audio or video files to process"
    )
    
    youtube_urls = st.text_area(
        "🎬 YouTube URLs (one per line)",
        placeholder="https://www.youtube.com/watch?v=...",
        help="Paste YouTube video URLs to download and process"
    )
    
    model = st.selectbox(
        "🎛️ Demucs Model",
        AVAILABLE_MODELS,
        index=0,
        help="Select the AI model for audio separation"
    )

    process_clicked = st.button("🚀 Remove Music", type="primary")

    if process_clicked:
        progress_bar = st.progress(0.0, text="Preparing to process media...")

        def update_progress(_stage: str, fraction: float, message: str) -> None:
            progress_bar.progress(fraction, text=message)

        with st.spinner("Processing media, this may take a few minutes..."):
            try:
                results = _process_submission(
                    uploaded_files or [],
                    youtube_urls,
                    model,
                    progress_callback=update_progress,
                )
            except ValueError as exc:
                st.warning(str(exc))
                progress_bar.progress(0.0, text="Waiting for inputs...")
                return
            except Exception as exc:  # pragma: no cover - surfaced through UI
                logger.exception("Streamlit processing failed: %s", exc)
                st.error("Processing failed. Please try again.")
                progress_bar.progress(0.0, text="Processing failed. Please retry.")
                return

        progress_bar.progress(1.0, text="Processing complete!")
        st.success("✨ Processing complete!")
        
        for index, result in enumerate(results, start=1):
            st.download_button(
                label=f"⬇️ Download: {result.filename}",
                data=result.data,
                file_name=result.filename,
                mime=result.mime,
            )

    _inject_html(st, "streamlit_footer.html", version=__version__)


if __name__ == "__main__":  # pragma: no cover - entry point for `streamlit run`
    run()
