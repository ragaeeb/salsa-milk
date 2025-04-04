#!/bin/bash
set -e

echo "Building salsa-milk container..."
podman build -t salsa-milk .

echo "Making salsa-milk script executable..."
chmod +x salsa-milk.sh

echo "Linking salsa-milk.sh to salsa-milk for convenience..."
ln -sf salsa-milk.sh salsa-milk
chmod +x salsa-milk

echo "Build complete!"
echo ""
echo "You can now run the CLI using:"
echo "./salsa-milk path/to/video.mp4"
echo "./salsa-milk https://youtube.com/watch?v=VIDEOID"
echo ""
echo "To specify memory limit (default is 8GB):"
echo "./salsa-milk -m 12g path/to/video.mp4"