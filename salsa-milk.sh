#!/bin/bash
set -e

# Default settings
MEMORY="12g"
OUTPUT_DIR="$(pwd)"
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT  # Clean up temp dir on exit

# Parse arguments
while getopts "m:o:" opt; do
  case $opt in
    m)
      MEMORY="$OPTARG"
      ;;
    o)
      # Convert relative path to absolute path
      if [[ "$OPTARG" = /* ]]; then
        # It's already an absolute path
        OUTPUT_DIR="$OPTARG"
      else
        # Convert to absolute path
        OUTPUT_DIR="$(pwd)/$OPTARG"
      fi
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
  esac
done
shift $((OPTIND-1))

# Set up directories
CACHE_DIR="$HOME/.cache/salsa-milk"

# Create only necessary directories
mkdir -p "$OUTPUT_DIR" "$CACHE_DIR"

# Exit if no arguments provided
if [ $# -eq 0 ]; then
  echo "Error: No input files or URLs provided."
  echo "Usage: $0 [-m MEMORY] [-o OUTPUT_DIR] input_file.mp4 [input_file2.mp4] [https://youtube.com/...]"
  echo "  -m MEMORY     Set memory limit (default: 12g)"
  echo "  -o OUTPUT_DIR Set output directory (default: current directory)"
  exit 1
fi

# Process command line arguments
ARGS=()

# Handle file paths - copy local files to temp dir if needed
for arg in "$@"; do
    if [[ "$arg" == http* ]]; then
        # It's a URL, pass directly
        ARGS+=("$arg")
    elif [[ -f "$arg" ]]; then
        # It's a file, copy to temp dir and reference by filename
        filename=$(basename "$arg")
        cp "$arg" "$TEMP_DIR/$filename"
        ARGS+=("/media/$filename")
    else
        # Pass other arguments as-is
        ARGS+=("$arg")
    fi
done

echo "Starting salsa-milk with memory limit: $MEMORY"
echo "Output will be saved to: $OUTPUT_DIR"

# Debug info
echo "Using output directory: $OUTPUT_DIR (absolute path)"

# Run the container with appropriate volume mounts, using temp directory for media
podman run --rm \
    --memory="$MEMORY" \
    --memory-swap="$MEMORY" \
    -e PYTHONUNBUFFERED=1 \
    -v "$TEMP_DIR:/media:z" \
    -v "$OUTPUT_DIR:/output:z" \
    -v "$CACHE_DIR:/cache:z" \
    salsa-milk "${ARGS[@]}"

echo "Processing complete. Results are in $OUTPUT_DIR"