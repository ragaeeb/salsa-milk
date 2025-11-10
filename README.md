# salsa-milk 🎵➡️🎤

<div align="center">
  <img src="https://wakatime.com/badge/user/a0b906ce-b8e7-4463-8bce-383238df6d4b/project/34209350-45ec-493e-bf98-27ecff0b4caa.svg" />
  <a href="https://colab.research.google.com/github/ragaeeb/salsa-milk/blob/main/salsa-milk.ipynb" target="_blank"><img src="https://colab.research.google.com/assets/colab-badge.svg" /></a>
  <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT" />
  <img src="https://img.shields.io/badge/podman-v5.4.2-purple.svg" alt="Podman: v5.4.2" />
  <img src="https://img.shields.io/badge/demucs-v4.0.1-orange.svg" alt="Demucs: v4.0.1" />
</div>

Salsa Milk isolates vocals from media files and YouTube videos using [Demucs](https://github.com/facebookresearch/demucs) AI technology. You can run it from the command line **or** through the included Flask web app that is ready to deploy on platforms such as Render.

## ✨ Features

- **High-Quality Vocal Isolation**: Uses Demucs, a state-of-the-art audio source separation model
- **Web Interface**: Upload media in the browser and download the isolated vocals (Render ready)
- **Containerized**: Runs in a Podman/Docker container with all dependencies included
- **YouTube Support**: Process videos directly from YouTube URLs
- **Local Media Support**: Process local audio and video files
- **Preserve Video**: For video inputs, the video track is preserved with the isolated vocals
- **Customizable Output**: Choose your output directory
- **Memory Management**: Adjust memory allocation for larger files

## 🌐 Deploying the Web App on Render

1. Fork or import this repository into your own GitHub account.
2. Create a new **Web Service** on [Render](https://render.com/) and connect it to your fork.
3. Use these service settings:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn -c gunicorn.conf.py webapp:app`
   - **Instance Type**: Pick at least a starter instance with enough CPU/RAM for Demucs processing.
4. (Optional) Set environment variables:
   - `MAX_CONTENT_LENGTH` &mdash; override the default 512MB upload limit (in bytes).
   - `SECRET_KEY` &mdash; customize the Flask session secret.
   - `WEB_TIMEOUT` &mdash; Gunicorn hard timeout (default `600` seconds).
   - `WEB_GRACEFUL_TIMEOUT` &mdash; graceful shutdown timeout (defaults to `WEB_TIMEOUT`).
   - `WEB_CONCURRENCY` / `WEB_THREADS` &mdash; tweak worker and thread counts (defaults: `1`).
   - `WEB_MAX_REQUESTS` &mdash; recycle workers after _n_ handled requests (disabled by default).
5. Deploy. When the service is healthy, visit the generated URL to upload audio/video, remove the music, and download the isolated vocals.

> ⚠️ Demucs is CPU intensive. Processing large videos can take several minutes depending on your Render instance size.

### Local Web Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python webapp.py
```

The web app listens on `http://127.0.0.1:8000` by default. Use `PORT` to override the port, or `MAX_CONTENT_LENGTH` to change the upload cap.

## 🚀 CLI Installation

The CLI tooling is still available for batch processing, automation, or Podman/Docker usage.

### Prerequisites

- Podman (v4.0+) or Docker
- Bash-compatible shell

### macOS Installation

```bash
brew install podman
podman machine init
podman machine start
git clone https://github.com/ragaeeb/salsa-milk.git
cd salsa-milk
./build.sh
```

### Linux Installation

```bash
sudo apt-get update
sudo apt-get install -y podman
git clone https://github.com/ragaeeb/salsa-milk.git
cd salsa-milk
./build.sh
```

### Using Docker instead of Podman

The installation works the same with Docker. Substitute `docker` for `podman` and update `salsa-milk.sh` accordingly.

## 🎮 CLI Usage

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
