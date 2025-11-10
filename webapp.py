#!/usr/bin/env python3
"""Flask web interface for Salsa Milk."""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path

from flask import (
    Flask,
    after_this_request,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
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


def allowed_file(filename: str) -> bool:
    """Check if a filename has an allowed extension."""

    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def create_app() -> Flask:
    """Create and configure the Flask application."""

    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "salsa-milk-secret")
    app.config["MAX_CONTENT_LENGTH"] = int(
        os.environ.get("MAX_CONTENT_LENGTH", 512 * 1024 * 1024)
    )

    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO)

    logger = logging.getLogger("salsa-milk")

    @app.route("/", methods=["GET", "POST"])
    def index():
        if request.method == "POST":
            upload = request.files.get("file")
            if not upload or upload.filename == "":
                flash("Please choose a media file to upload.", "error")
                return redirect(request.url)

            filename = secure_filename(upload.filename)
            if not allowed_file(filename):
                flash("Unsupported file type. Please upload audio or video media.", "error")
                return redirect(request.url)

            work_dir = Path(tempfile.mkdtemp(prefix="salsa-milk-"))
            uploads_dir = work_dir / "uploads"
            temp_dir = work_dir / "temp"
            output_dir = work_dir / "output"

            uploads_dir.mkdir(parents=True, exist_ok=True)
            temp_dir.mkdir(parents=True, exist_ok=True)
            output_dir.mkdir(parents=True, exist_ok=True)

            saved_path = uploads_dir / filename
            upload.save(saved_path)

            model = request.form.get("model", "htdemucs") or "htdemucs"

            try:
                results = process_files(
                    [saved_path],
                    model=model,
                    temp_dir=temp_dir,
                    output_dir=output_dir,
                    enable_progress=False,
                )
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.exception("Processing failed: %s", exc)
                shutil.rmtree(work_dir, ignore_errors=True)
                flash("Processing failed. Please try again.", "error")
                return redirect(request.url)

            if not results:
                shutil.rmtree(work_dir, ignore_errors=True)
                flash("No output was produced. Please try a different file.", "error")
                return redirect(request.url)

            output_path = Path(results[0]["output"])
            download_name = f"{saved_path.stem}_vocals{output_path.suffix}"

            response = send_file(output_path, as_attachment=True, download_name=download_name)

            @after_this_request
            def cleanup(response):  # type: ignore[override]
                shutil.rmtree(work_dir, ignore_errors=True)
                return response

            return response

        return render_template(
            "index.html",
            models=AVAILABLE_MODELS,
            max_size=app.config["MAX_CONTENT_LENGTH"],
        )

    @app.errorhandler(413)
    def request_entity_too_large(_error):
        flash("The uploaded file is too large for the server to process.", "error")
        return redirect(url_for("index"))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), debug=False)
