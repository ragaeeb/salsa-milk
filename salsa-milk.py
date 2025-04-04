#!/usr/bin/env python3
import os
import sys
import subprocess
import glob
import re
import argparse
import logging
import time
from pathlib import Path
from tqdm import tqdm

# Configure logging with immediate output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(stream=sys.stdout)]
)
logger = logging.getLogger('salsa-milk')

def download_from_youtube(urls):
    """Download videos from YouTube URLs"""
    video_files = []
    
    if not urls:
        return video_files
    
    # Split multiple URLs if provided as a single string
    if isinstance(urls, str):
        urls = re.split(r'\s+', urls.strip())
    
    for url in urls:
        if not url.strip():
            continue
            
        logger.info(f"Downloading from YouTube: {url}")
        
        # Extract video ID for naming
        if "youtube.com/watch?v=" in url:
            video_id = url.split("youtube.com/watch?v=")[1].split("&")[0]
        elif "youtu.be/" in url:
            video_id = url.split("youtu.be/")[1].split("?")[0]
        else:
            # Generate a timestamp-based ID if we can't extract one
            video_id = f"yt_{int(time.time())}"
        
        # Download video
        try:
            video_output = f"/media/{video_id}.mp4"
            video_cmd = [
                "yt-dlp",
                "-f", "best",  # Get best format that includes video
                "--output", video_output,
                "--no-check-certificate",
                "--geo-bypass",
                url
            ]
            
            logger.info(f"Downloading video from: {url}")
            # Use real-time output instead of capturing
            subprocess.run(video_cmd, check=True, stdout=sys.stdout, stderr=sys.stderr)
            
            if os.path.exists(video_output):
                logger.info(f"✅ Successfully downloaded {video_id}")
                video_files.append(video_output)
            else:
                logger.error(f"❌ Failed to download {url}")
        except Exception as e:
            logger.error(f"❌ Error downloading {url}: {str(e)}")
    
    return video_files

def process_files(input_files, model="htdemucs"):
    """Process media files to isolate vocals"""
    results = []
    
    # Determine device 
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Using device: {device}")
    
    # Create temporary directory
    os.makedirs("/tmp/demucs", exist_ok=True)
    
    for file_path in tqdm(input_files, desc="Processing files"):
        logger.info(f"Processing {os.path.basename(file_path)}...")
        
        # Extract ID from filename
        file_id = os.path.splitext(os.path.basename(file_path))[0]
        
        # Check if it's a video file
        has_video = file_path.lower().endswith((".mp4", ".mov", ".avi", ".mkv", ".webm"))
        
        # Run Demucs to extract vocals - with real-time output
        demucs_cmd = [
            "demucs",
            "--two-stems", "vocals",
            "-n", model,
            "--device", device,
            "-o", "/tmp/demucs",
            file_path
        ]
        
        try:
            # Point to cache location for models
            env = os.environ.copy()
            env["TORCH_HOME"] = "/cache"
            
            logger.info(f"Running Demucs on {file_id}...")
            # Use real-time output
            subprocess.run(demucs_cmd, env=env, check=True, stdout=sys.stdout, stderr=sys.stderr)
            
            # Get path to extracted vocals
            vocals_path = f"/tmp/demucs/{model}/{file_id}/vocals.wav"
            
            # Check alternate paths if default not found
            if not os.path.exists(vocals_path):
                potential_paths = glob.glob(f"/tmp/demucs/*/{file_id}/vocals.wav")
                if potential_paths:
                    vocals_path = potential_paths[0]
                    logger.info(f"Found vocals at alternate path: {vocals_path}")
                else:
                    logger.warning(f"⚠️ Could not find extracted vocals for {file_id}, skipping...")
                    continue
            
            # Get file extension for output
            if has_video:
                # Video files always output as MP4
                output_ext = "mp4"
                output_path = f"/output/{file_id}_vocals.{output_ext}"
                
                # Replace audio in original video
                logger.info(f"Creating video with isolated vocals...")
                ffmpeg_cmd = [
                    "ffmpeg", "-y",
                    "-i", file_path,
                    "-i", vocals_path,
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    "-shortest",
                    output_path
                ]
            else:
                # For audio files, keep the original extension
                original_ext = os.path.splitext(file_path)[1][1:].lower()
                output_ext = original_ext if original_ext else "wav"
                output_path = f"/output/{file_id}_vocals.{output_ext}"
                
                logger.info(f"Creating audio file with isolated vocals...")
                
                # Choose codec based on output format
                codec = "copy"
                if output_ext in ["mp3"]:
                    codec = "libmp3lame"
                elif output_ext in ["aac", "m4a"]:
                    codec = "aac"
                elif output_ext in ["ogg", "opus"]:
                    codec = "libopus"
                
                ffmpeg_cmd = [
                    "ffmpeg", "-y",
                    "-i", vocals_path,
                    "-c:a", codec,
                    "-b:a", "192k",
                    output_path
                ]
            
            logger.info(f"Running FFmpeg...")
            # Use real-time output
            subprocess.run(ffmpeg_cmd, check=True, stdout=sys.stdout, stderr=sys.stderr)
            
            # Add to results
            results.append({
                "input": file_path,
                "output": output_path,
                "id": file_id
            })
            
            logger.info(f"✅ Successfully processed {file_id}")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error processing {file_id}: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Error processing {file_id}: {str(e)}")
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Extract vocals from media files using Demucs')
    parser.add_argument('inputs', nargs='+', help='Input media files or YouTube URLs')
    parser.add_argument('-m', '--model', default='htdemucs', help='Demucs model to use')
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    os.makedirs("/output", exist_ok=True)
    os.makedirs("/media", exist_ok=True)
    
    # Separate YouTube URLs from local file paths
    youtube_urls = []
    local_files = []
    
    for input_item in args.inputs:
        if input_item.startswith(('http://', 'https://')):
            youtube_urls.append(input_item)
        else:
            # Handle potential local path
            local_files.append(input_item)
    
    # Download YouTube videos if provided
    yt_files = download_from_youtube(youtube_urls) if youtube_urls else []
    
    # Combine all input files
    all_files = local_files + yt_files
    
    if not all_files:
        logger.error("No valid input files found. Please provide valid files or YouTube URLs.")
        sys.exit(1)
    
    # Process all files
    logger.info(f"Processing {len(all_files)} files...")
    results = process_files(all_files, model=args.model)
    
    # Display results
    if results:
        logger.info(f"Successfully processed {len(results)} files:")
        for i, result in enumerate(results):
            logger.info(f"{i+1}. {os.path.basename(result['output'])}")
    else:
        logger.error("No files were successfully processed.")
        sys.exit(1)
    
    logger.info("Output files saved to the output directory.")

if __name__ == "__main__":
    main()