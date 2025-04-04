#!/bin/bash
set -e

# Parse arguments
CLEAN_BUILD=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --clean)
      CLEAN_BUILD=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--clean]"
      exit 1
      ;;
  esac
done

# Clean build if requested
if [ "$CLEAN_BUILD" = true ]; then
  echo "Removing old container..."
  podman rmi -f salsa-milk 2>/dev/null || true
  BUILD_ARGS="--no-cache"
else
  BUILD_ARGS=""
fi

echo "Building salsa-milk container..."
podman build $BUILD_ARGS -t salsa-milk .

echo "Making salsa-milk.sh executable..."
chmod +x salsa-milk.sh

echo "Build complete!"
echo ""
echo "SALSA-MILK - Extract vocals from media files and YouTube videos"
echo ""
echo "USAGE:"
echo "  ./salsa-milk.sh [OPTIONS] INPUT [INPUT2 INPUT3...]"
echo ""
echo "INPUTS:"
echo "  Local media files or YouTube URLs"
echo ""
echo "OPTIONS:"
echo "  -m MEMORY      Set memory limit (default: 12g, e.g., -m 12g)"
echo "  -o DIRECTORY   Set output directory (default: current directory)"
echo ""
echo "EXAMPLES:"
echo "  ./salsa-milk.sh video.mp4"
echo "  ./salsa-milk.sh -m 12g -o ~/vocals https://youtube.com/watch?v=VIDEOID"
echo "  ./salsa-milk.sh video1.mp4 video2.mp4 https://youtube.com/watch?v=VIDEOID"