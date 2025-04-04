# salsa-milk 🎵➡️🎤

<div align="center">
  <img src="https://wakatime.com/badge/user/a0b906ce-b8e7-4463-8bce-383238df6d4b/project/34209350-45ec-493e-bf98-27ecff0b4caa.svg" />
  <a href="https://colab.research.google.com/github/ragaeeb/salsa-milk/blob/main/salsa-milk.ipynb" target="_blank"><img src="https://colab.research.google.com/assets/colab-badge.svg" /></a>
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT" />
  <img src="https://img.shields.io/badge/podman-v5.4.2-purple.svg" alt="Podman: v5.4.2" />
  <img src="https://img.shields.io/badge/demucs-v4.0.1-orange.svg" alt="Demucs: v4.0.1" />
</div>

A containerized CLI tool that isolates vocals from media files and YouTube videos using [Demucs](https://github.com/facebookresearch/demucs) AI technology. Easily extract vocals from music videos or audio tracks with a single command.

## ✨ Features

- **High-Quality Vocal Isolation**: Uses Demucs, a state-of-the-art audio source separation model
- **Containerized**: Runs in a Podman/Docker container with all dependencies included
- **YouTube Support**: Process videos directly from YouTube URLs
- **Local Media Support**: Process local audio and video files
- **Preserve Video**: For video inputs, the video track is preserved with the isolated vocals
- **Customizable Output**: Choose your output directory
- **Memory Management**: Adjust memory allocation for larger files

## 🚀 Installation

### Prerequisites

- Podman (v4.0+) or Docker
- Bash-compatible shell

### macOS Installation

1. Install Podman using Homebrew:

```bash
brew install podman
```

2. Initialize and start the Podman machine:

```bash
podman machine init
podman machine start
```

3. Clone the repository:

```bash
git clone https://github.com/ragaeeb/salsa-milk.git
cd salsa-milk
```

4. Build the container:

```bash
./build.sh
```

### Linux Installation

1. Install Podman (using your package manager):

For Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install -y podman
```

For Fedora:
```bash
sudo dnf install -y podman
```

2. Clone the repository:

```bash
git clone https://github.com/ragaeeb/salsa-milk.git
cd salsa-milk
```

3. Build the container:

```bash
./build.sh
```

### Using Docker instead of Podman

The installation works the same with Docker. Simply substitute `docker` for `podman` in the commands. Edit the `salsa-milk.sh` script to use Docker instead of Podman.

## 🎮 Usage

### Basic Usage

Process a local video file:
```bash
./salsa-milk.sh video.mp4
```

Process a YouTube video:
```bash
./salsa-milk.sh https://www.youtube.com/watch?v=VIDEO_ID
```

Process multiple files:
```bash
./salsa-milk.sh video1.mp4 video2.mp4 https://www.youtube.com/watch?v=VIDEO_ID
```

### Options

- `-m MEMORY`: Set memory limit (default: 12g)
```bash
./salsa-milk.sh -m 16g video.mp4
```

- `-o DIRECTORY`: Set output directory (default: current directory)
```bash
./salsa-milk.sh -o ~/vocals video.mp4
```

Combine options:
```bash
./salsa-milk.sh -m 16g -o ~/vocals video.mp4
```

### Rebuilding the Container

If you need to rebuild the container (e.g., after updating the code):
```bash
./build.sh --clean
```

## 🔧 Technical Details

- **Container Image**: Uses Python `3.13-slim` with necessary dependencies
- **Caching**: Demucs models are cached in `~/.cache/salsa-milk` for faster processing
- **Temporary Files**: All intermediate files are stored in temporary directories and cleaned up on exit
- **Memory Usage**: Default memory allocation is `12GB`, can be adjusted with the `-m` option

## 👥 Authors

- Ragaeeb Haq - [GitHub Profile](https://github.com/ragaeeb)

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Demucs](https://github.com/facebookresearch/demucs) for the audio separation technology
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for YouTube downloading capabilities
- Inspired by [Tafrigh](https://github.com/ieasybooks/tafrigh), which was used as a template for the Google Colab notebook.
- I overheard my daughters saying "Salsa Milk" in one of their pretend-play games. They then requested I use this name for my next project.
