#!/usr/bin/env python3
"""Command-line interface for the Salsa Milk vocal isolation pipeline.

This module provides a command-line interface for processing audio and video files
to isolate vocals using the Demucs AI model. It supports both local files and
YouTube URLs as input.

Example:
    $ python salsa-milk.py song.mp3 https://youtube.com/watch?v=abc
    $ python salsa-milk.py --model htdemucs --output-dir ./output video.mp4
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from salsa_milk import get_version
from salsa_milk_core import download_from_youtube, process_files


def configure_logging() -> logging.Logger:
    """Configure default logging for the CLI.
    
    Sets up INFO level logging with timestamps and sends output to stdout.
    
    Returns:
        Configured logger instance for salsa-milk.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(stream=sys.stdout)],
    )
    return logging.getLogger("salsa-milk")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.
    
    Returns:
        Namespace containing parsed command-line arguments including:
            - inputs: List of input files or YouTube URLs
            - model: Demucs model name
            - temp_dir: Temporary working directory
            - output_dir: Output directory for processed files
            - download_dir: Directory for YouTube downloads
    """
    parser = argparse.ArgumentParser(
        description="Extract vocals from media files or YouTube URLs using Demucs.",
    )
    parser.add_argument("inputs", nargs="+", help="Input media files or YouTube URLs.")
    parser.add_argument("-m", "--model", default="htdemucs", help="Demucs model to use.")
    parser.add_argument(
        "--temp-dir",
        default="/tmp",
        help="Temporary working directory (default: /tmp).",
    )
    parser.add_argument(
        "--output-dir",
        default="/output",
        help="Directory for processed files (default: /output).",
    )
    parser.add_argument(
        "--download-dir",
        default="/media",
        help="Directory for downloaded YouTube media (default: /media).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {get_version()}",
        help="Show the Salsa Milk version and exit.",
    )
    return parser.parse_args()


def main() -> None:
    """Execute the CLI workflow.
    
    This function orchestrates the complete workflow:
    1. Parses command-line arguments
    2. Creates necessary directories
    3. Separates YouTube URLs from local files
    4. Downloads videos from YouTube
    5. Processes all media files
    6. Reports results
    
    Exits with code 1 if no valid inputs are provided or processing fails.
    """
    logger = configure_logging()
    args = parse_args()

    output_dir = Path(args.output_dir)
    download_dir = Path(args.download_dir)
    temp_dir = Path(args.temp_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    download_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    youtube_urls = []
    local_files = []

    for item in args.inputs:
        if item.startswith(("http://", "https://")):
            youtube_urls.append(item)
        else:
            local_path = Path(item)
            if local_path.exists():
                local_files.append(str(local_path.resolve()))
            else:
                logger.warning("Skipping missing file: %s", item)

    downloaded_files = download_from_youtube(youtube_urls, download_dir=download_dir)

    all_files = local_files + downloaded_files

    if not all_files:
        logger.error("No valid input files found. Provide local files or YouTube URLs.")
        sys.exit(1)

    logger.info("Processing %s file(s)...", len(all_files))
    results = process_files(
        all_files,
        model=args.model,
        temp_dir=temp_dir,
        output_dir=output_dir,
        enable_progress=True,
    )

    if not results:
        logger.error("No files were successfully processed.")
        sys.exit(1)

    logger.info("Successfully processed %s file(s):", len(results))
    for idx, result in enumerate(results, start=1):
        logger.info("%s. %s", idx, Path(result["output"]).name)

    logger.info("Output files saved to %s", output_dir.resolve())


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()