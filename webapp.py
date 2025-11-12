#!/usr/bin/env python3
"""Flask web interface for Salsa Milk.

This module provides a web-based interface for processing audio and video files
to isolate vocals. It handles file uploads, asynchronous processing, progress
tracking, and download delivery.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

from flask import Flask, flash, jsonify, redirect, render_template, request, send_file, url_for
from werkzeug.exceptions import NotFound
from werkzeug.utils import secure_filename

from salsa_milk_core import process_files


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
class ProcessingTask:
    """State machine for an in-flight processing request.
    
    Tracks the complete lifecycle of a file processing job from upload
    through processing to download readiness.
    
    Attributes:
        id: Unique task identifier (UUID hex).
        work_dir: Temporary working directory for this task.
        saved_path: Path to uploaded input file.
        model: Demucs model name to use.
        temp_dir: Temporary directory for intermediate files.
        output_dir: Directory for final output files.
        status: Current task status ("queued", "running", "completed", "error").
        progress: Progress percentage (0.0 to 100.0).
        message: Human-readable status message.
        output_path: Path to final output file (set on completion).
        download_name: Suggested filename for download.
        error: Error message if processing failed.
        created_at: Timestamp when task was created.
    """
    id: str
    work_dir: Path
    saved_path: Path
    model: str
    temp_dir: Path
    output_dir: Path
    status: str = "queued"
    progress: float = 0.0
    message: str = "Queued for processing..."
    output_path: Path | None = None
    download_name: str | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)


_TASKS: Dict[str, ProcessingTask] = {}
_TASK_LOCK = threading.Lock()


def allowed_file(filename: str) -> bool:
    """Check if a filename has an allowed extension.
    
    Args:
        filename: Name of file to check.
        
    Returns:
        True if file extension is in ALLOWED_EXTENSIONS, False otherwise.
    """
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def create_app() -> Flask:
    """Create and configure the Flask application.
    
    Sets up routes, error handlers, and logging configuration.
    Configures maximum upload size from environment variable.
    
    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "salsa-milk-secret")
    app.config["MAX_CONTENT_LENGTH"] = int(
        os.environ.get("MAX_CONTENT_LENGTH", 512 * 1024 * 1024)
    )

    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO)

    logger = logging.getLogger("salsa-milk")

    @app.route("/", methods=["GET"])
    def index():
        """Render the main upload form page.
        
        Returns:
            Rendered HTML template with upload form.
        """
        return render_template(
            "index.html",
            models=AVAILABLE_MODELS,
            max_size=app.config["MAX_CONTENT_LENGTH"],
        )

    @app.post("/api/process")
    def api_process():
        """Handle file upload and initiate async processing.
        
        Validates uploaded file, creates processing task, and starts
        background thread for processing.
        
        Returns:
            JSON response with task_id and status (200 on success).
            JSON error response (400) if validation fails.
        """
        upload = request.files.get("file")
        if not upload or upload.filename == "":
            return jsonify({"error": "no_file", "message": "Please choose a media file to upload."}), 400

        filename = secure_filename(upload.filename)
        if not allowed_file(filename):
            return (
                jsonify(
                    {
                        "error": "invalid_type",
                        "message": "Unsupported file type. Please upload audio or video media.",
                    }
                ),
                400,
            )

        model = request.form.get("model", "htdemucs") or "htdemucs"

        work_dir = Path(tempfile.mkdtemp(prefix="salsa-milk-"))
        uploads_dir = work_dir / "uploads"
        temp_dir = work_dir / "temp"
        output_dir = work_dir / "output"

        uploads_dir.mkdir(parents=True, exist_ok=True)
        temp_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        saved_path = uploads_dir / filename
        upload.save(saved_path)

        task_id = uuid.uuid4().hex
        task = ProcessingTask(
            id=task_id,
            work_dir=work_dir,
            saved_path=saved_path,
            model=model,
            temp_dir=temp_dir,
            output_dir=output_dir,
            progress=5.0,
            message="Upload complete. Preparing to process...",
        )

        with _TASK_LOCK:
            _TASKS[task_id] = task

        thread = threading.Thread(target=_run_task, args=(task_id,), daemon=True)
        thread.start()

        response = jsonify({"task_id": task_id, "status": "queued"})
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/progress/<task_id>")
    def api_progress(task_id: str):
        """Get current progress for a processing task.
        
        Args:
            task_id: Unique task identifier.
            
        Returns:
            JSON response with status, progress, message, and download_ready flag.
            
        Raises:
            NotFound: If task_id does not exist.
        """
        with _TASK_LOCK:
            task = _TASKS.get(task_id)

        if task is None:
            raise NotFound()

        payload = {
            "status": task.status,
            "progress": round(task.progress, 2),
            "message": task.message,
            "error": task.error,
            "download_ready": bool(task.output_path and task.status == "completed"),
        }
        return jsonify(payload)

    @app.get("/api/download/<task_id>")
    def api_download(task_id: str):
        """Download the processed output file for a task.
        
        Automatically cleans up task data after download completion.
        
        Args:
            task_id: Unique task identifier.
            
        Returns:
            File download response with processed audio/video.
            
        Raises:
            NotFound: If task doesn't exist or output file is not available.
        """
        with _TASK_LOCK:
            task = _TASKS.get(task_id)

        if task is None or task.output_path is None or not task.output_path.exists():
            raise NotFound()

        response = send_file(
            task.output_path,
            as_attachment=True,
            download_name=task.download_name or task.output_path.name,
        )

        @response.call_on_close
        def _cleanup_task() -> None:
            """Clean up task data after download completes."""
            _finalize_task(task_id)

        return response

    @app.errorhandler(413)
    def request_entity_too_large(_error):
        """Handle file too large errors.
        
        Args:
            _error: Exception instance (unused).
            
        Returns:
            Redirect to index with error flash message.
        """
        flash("The uploaded file is too large for the server to process.", "error")
        return redirect(url_for("index"))

    return app


app = create_app()


def _default_message(stage: str, file_name: str) -> str:
    """Generate default progress message for a processing stage.
    
    Args:
        stage: Processing stage identifier.
        file_name: Name of file being processed.
        
    Returns:
        Human-readable progress message.
    """
    stage_messages = {
        "prepare": f"Preparing {file_name}...",
        "convert": f"Converting {file_name}...",
        "demucs": f"Running Demucs on {file_name}...",
        "mux": f"Writing {file_name}...",
        "file_complete": f"Completed {file_name}.",
    }
    return stage_messages.get(stage, "Processing...")


def _run_task(task_id: str) -> None:
    """Execute processing for a task in background thread.
    
    Updates task progress through callbacks and handles errors.
    Sets final status to "completed" on success or "error" on failure.
    
    Args:
        task_id: Unique task identifier.
    """
    with _TASK_LOCK:
        task = _TASKS.get(task_id)

    if task is None:
        return

    logger = logging.getLogger("salsa-milk")

    def update(stage: str, fraction: float, message: str | None) -> None:
        """Update task progress.
        
        Args:
            stage: Processing stage identifier.
            fraction: Progress fraction (0.0 to 1.0).
            message: Optional progress message.
        """
        with _TASK_LOCK:
            current = _TASKS.get(task_id)
            if current is None:
                return
            current.status = "running"
            current.progress = max(current.progress, fraction * 100)
            current.message = message or _default_message(stage, current.saved_path.name)

    try:
        results = process_files(
            [task.saved_path],
            model=task.model,
            temp_dir=task.temp_dir,
            output_dir=task.output_dir,
            enable_progress=False,
            progress_callback=update,
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Processing failed: %s", exc)
        with _TASK_LOCK:
            current = _TASKS.get(task_id)
            if current is not None:
                current.status = "error"
                current.message = "Processing failed. Please try again."
                current.error = str(exc)
        return

    if not results:
        with _TASK_LOCK:
            current = _TASKS.get(task_id)
            if current is not None:
                current.status = "error"
                current.message = "No output was produced. Please try a different file."
                current.error = "no_output"
        return

    output_path = Path(results[0]["output"])
    download_name = f"{task.saved_path.stem}_vocals{output_path.suffix}"

    with _TASK_LOCK:
        current = _TASKS.get(task_id)
        if current is None:
            return
        current.status = "completed"
        current.progress = 100.0
        current.message = "Demucs separation complete! Preparing download..."
        current.output_path = output_path
        current.download_name = download_name


def _finalize_task(task_id: str) -> None:
    """Clean up task resources and remove from tracking.
    
    Deletes temporary working directory and removes task from registry.
    
    Args:
        task_id: Unique task identifier.
    """
    with _TASK_LOCK:
        task = _TASKS.pop(task_id, None)

    if task is None:
        return

    shutil.rmtree(task.work_dir, ignore_errors=True)


if __name__ == "__main__":  # pragma: no cover - Flask entry point
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), debug=False)