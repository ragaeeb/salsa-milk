#!/bin/bash
set -e

# Default memory limit - increased to 8GB
MEMORY="8g"

# Parse memory option if provided
while getopts "m:" opt; do
  case $opt in
    m)
      MEMORY="$OPTARG"
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
  esac
done
shift $((OPTIND-1))

# Set up directories
OUTPUT_DIR="$(pwd)/salsa-milk-output"
CACHE_DIR="$HOME/.cache/salsa-milk"
MEDIA_DIR="$(pwd)/salsa-milk-media"

mkdir -p "$OUTPUT_DIR" "$CACHE_DIR" "$MEDIA_DIR"

# Process command line arguments
ARGS=()

# Exit if no arguments provided
if [ $# -eq 0 ]; then
  echo "Error: No input files or URLs provided."
  echo "Usage: $0 [-m MEMORY] input_file.mp4 [input_file2.mp4] [https://youtube.com/...]"
  exit 1
fi

# Handle file paths - copy local files to media dir if needed
for arg in "$@"; do
    if [[ "$arg" == http* ]]; then
        # It's a URL, pass directly
        ARGS+=("$arg")
    elif [[ -f "$arg" ]]; then
        # It's a file, copy to media dir and reference by filename
        filename=$(basename "$arg")
        cp "$arg" "$MEDIA_DIR/$filename"
        ARGS+=("/media/$filename")
    else
        # Pass other arguments as-is
        ARGS+=("$arg")
    fi
done

echo "Starting salsa-milk with memory limit: $MEMORY"

# Run the container with appropriate volume mounts
podman run --rm \
    --memory="$MEMORY" \
    -v "$MEDIA_DIR:/media" \
    -v "$OUTPUT_DIR:/output" \
    -v "$CACHE_DIR:/cache" \
    salsa-milk "${ARGS[@]}"

echo "Processing complete. Results are in $OUTPUT_DIR"