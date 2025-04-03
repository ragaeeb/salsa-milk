# salsa-milk

<div align="center">
  <img src="https://wakatime.com/badge/user/a0b906ce-b8e7-4463-8bce-383238df6d4b/project/34209350-45ec-493e-bf98-27ecff0b4caa.svg" />
  <a href="https://colab.research.google.com/github/ragaeeb/salsa-milk/blob/main/salsa-milk.ipynb" target="_blank"><img src="https://colab.research.google.com/assets/colab-badge.svg" /></a>
</div>

salsa-milk is an open-source tool that isolates vocals from music and video files using [Demucs](https://github.com/facebookresearch/demucs) AI technology. It's designed to be easy to use, with a focus on providing high-quality vocal isolation without requiring technical expertise.

## Features

- **High-Quality Vocal Isolation**: Uses Demucs, a state-of-the-art audio source separation model
- **Batch Processing**: Process multiple files at once
- **Video Support**: Can handle both audio and video files, preserving video tracks
- **Multiple Output Formats**: Get results as audio-only `WAV` files or video MP4 files
- **Google Colab Integration**: Run without installing anything on your computer

## Getting Started

### Using the Google Colab Notebook

The easiest way to use salsa-milk is through our Google Colab notebook:

1. Open the [salsa-milk Colab Notebook](https://colab.research.google.com/github/ragaeeb/salsa-milk/blob/main/salsa-milk.ipynb)
2. Upload your audio/video files or provide YouTube URLs
3. Run the processing cell
4. Download your extracted vocals

### Processing YouTube Videos

Due to YouTube's restrictions on direct downloads from Google Colab, the most reliable approach is:

1. Install yt-dlp: `pip install yt-dlp`
2. Download videos locally: `yt-dlp -x --audio-format wav "YOUR_YOUTUBE_URL"`
3. Upload the downloaded files to the Colab notebook

## Advanced Usage

### Demucs Models

You can choose between different Demucs models:

- `htdemucs`: General-purpose model (default)

### GPU Acceleration

If you're using the Colab notebook, you can enable GPU acceleration for faster processing:

1. Go to Runtime → Change runtime type
2. Select `GPU` from the Hardware accelerator dropdown
3. Click "Save"

## Contributing

Contributions are welcome! Please feel free to submit a pull request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Demucs](https://github.com/facebookresearch/demucs) for the audio separation technology
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for YouTube downloading capabilities
- Inspired by [Tafrigh](https://github.com/ieasybooks/tafrigh), which was used as a template for the Google Colab notebook.
- I overheard my daughters saying `Salsa Milk` in one of their pretend-play games. They then requested I use this name for my next project.
