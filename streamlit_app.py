"""Streamlit interface for the Salsa Milk vocal isolation toolkit."""

from __future__ import annotations

import logging
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
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

    # Custom CSS
    st.markdown("""
        <style>
        .main {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        
        .stApp {
            background: transparent;
        }
        
        div[data-testid="stToolbar"] {
            display: none;
        }
        
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 800px;
        }
        
        h1 {
            color: white !important;
            text-align: center;
            font-size: 3rem !important;
            font-weight: 800 !important;
            margin-bottom: 0.5rem !important;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        
        .subtitle {
            color: rgba(255, 255, 255, 0.9);
            text-align: center;
            font-size: 1.1rem;
            margin-bottom: 2rem;
        }
        
        .stFileUploader, .stTextArea, .stSelectbox {
            background: white;
            border-radius: 12px;
            padding: 1rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .stFileUploader:hover, .stTextArea:hover, .stSelectbox:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }
        
        .stButton > button {
            width: 100%;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            border: none;
            border-radius: 12px;
            padding: 0.75rem 2rem;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(245, 87, 108, 0.4);
        }
        
        .stButton > button:active {
            transform: translateY(0);
        }
        
        .stDownloadButton > button {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            border: none;
            border-radius: 12px;
            padding: 0.75rem 2rem;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            width: 100%;
        }
        
        .stDownloadButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(79, 172, 254, 0.4);
        }
        
        .footer {
            text-align: center;
            color: rgba(255, 255, 255, 0.8);
            margin-top: 3rem;
            padding: 1.5rem;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            backdrop-filter: blur(10px);
        }
        
        .footer a {
            color: white;
            text-decoration: none;
            font-weight: 600;
            transition: opacity 0.2s ease;
        }
        
        .footer a:hover {
            opacity: 0.8;
            text-decoration: underline;
        }
        
        .stProgress > div > div {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }
        
        .stAlert {
            border-radius: 12px;
            backdrop-filter: blur(10px);
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1>🥛 Salsa Milk</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Professional Music Remover - Isolate Vocals with AI</p>", unsafe_allow_html=True)

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
                key=f"download_{index}",
            )

    # Footer
    st.markdown(f"""
        <div class='footer'>
            <p>Version {__version__} • Powered by Demucs</p>
            <p>Created by <strong>Ragaeeb Haq</strong> • 
            <a href='https://github.com/ragaeeb/salsa-milk' target='_blank'>GitHub Repository</a></p>
            <p style='font-size: 0.9rem; margin-top: 0.5rem;'>
                Your audio stays private - all processing happens in this session
            </p>
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":  # pragma: no cover - entry point for `streamlit run`
    run()