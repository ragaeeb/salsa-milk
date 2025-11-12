"""Integration tests for end-to-end processing."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import salsa_milk_core as core


@pytest.mark.integration
def test_process_sample_video_end_to_end(tmp_path):
    """Test complete processing pipeline with actual sample video.
    
    This test requires ffmpeg and demucs to be installed and a sample.mp4
    file to exist in the tests directory. It verifies the entire pipeline
    from video input to isolated vocals output.
    
    Args:
        tmp_path: Pytest fixture providing temporary directory.
    """
    sample_video = Path(__file__).parent / "sample.mp4"
    
    if not sample_video.exists():
        pytest.skip("sample.mp4 not found in tests directory")
    
    # Verify ffmpeg is available
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("ffmpeg not available")
    
    # Verify demucs is available
    try:
        subprocess.run(
            ["demucs", "--help"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("demucs not available")
    
    temp_dir = tmp_path / "temp"
    output_dir = tmp_path / "output"
    
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process the sample video
    results = core.process_files(
        [sample_video],
        model="htdemucs",
        temp_dir=temp_dir,
        output_dir=output_dir,
        enable_progress=True,
    )
    
    # Verify results
    assert len(results) == 1, "Expected exactly one result"
    
    result = results[0]
    assert result["input"] == str(sample_video)
    assert "output" in result
    
    output_path = Path(result["output"])
    assert output_path.exists(), f"Output file not created: {output_path}"
    assert output_path.suffix == ".mp4", "Expected MP4 output for video input"
    assert output_path.stat().st_size > 0, "Output file is empty"
    
    # Verify output filename contains "vocals"
    assert "vocals" in output_path.name.lower()
    
    # Verify no temporary files left behind
    audio_dir = temp_dir / "audio"
    if audio_dir.exists():
        assert len(list(audio_dir.glob("*.wav"))) == 0, "Temporary WAV files not cleaned up"