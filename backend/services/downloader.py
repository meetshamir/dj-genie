"""
Audio/Video Downloader Service - Downloads content from YouTube using yt-dlp.
"""

import sys
from pathlib import Path
from typing import Optional, Dict
from dataclasses import dataclass

import yt_dlp

from config import settings


@dataclass
class DownloadResult:
    """Result of a download operation."""
    success: bool
    audio_path: Optional[str] = None
    video_path: Optional[str] = None
    error: Optional[str] = None
    duration: Optional[float] = None


def get_audio_cache_path(video_id: str) -> Path:
    """Get the path for cached audio file."""
    return settings.audio_cache_dir / f"{video_id}.mp3"


def get_video_cache_path(video_id: str) -> Path:
    """Get the path for cached video file."""
    return settings.video_cache_dir / f"{video_id}.mp4"


def is_audio_cached(video_id: str) -> bool:
    """Check if audio is already downloaded."""
    return get_audio_cache_path(video_id).exists()


def is_video_cached(video_id: str) -> bool:
    """Check if video is already downloaded."""
    return get_video_cache_path(video_id).exists()


def download_audio(youtube_url: str, video_id: str, force: bool = False) -> DownloadResult:
    """
    Download audio from YouTube video for analysis.
    
    Args:
        youtube_url: Full YouTube URL
        video_id: YouTube video ID (for caching)
        force: Force re-download even if cached
    
    Returns:
        DownloadResult with path to downloaded MP3
    """
    audio_path = get_audio_cache_path(video_id)
    
    # Check cache
    if not force and audio_path.exists():
        print(f"  Using cached audio: {audio_path}")
        return DownloadResult(
            success=True,
            audio_path=str(audio_path)
        )
    
    # Ensure directory exists
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Output path template
    output_template = str(audio_path.parent / f"{video_id}.%(ext)s")
    
    # yt-dlp options for audio download
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }
    
    print(f"  Downloading audio for {video_id}...")
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
        
        # Verify file exists
        if not audio_path.exists():
            return DownloadResult(
                success=False,
                error="Download completed but file not found"
            )
        
        print(f"  Audio downloaded: {audio_path}")
        return DownloadResult(
            success=True,
            audio_path=str(audio_path)
        )
        
    except Exception as e:
        error_msg = str(e)
        print(f"  Download failed: {error_msg[:100]}")
        return DownloadResult(
            success=False,
            error=error_msg
        )


def download_video(youtube_url: str, video_id: str, force: bool = False) -> DownloadResult:
    """
    Download video from YouTube for final export.
    
    Args:
        youtube_url: Full YouTube URL
        video_id: YouTube video ID (for caching)
        force: Force re-download even if cached
    
    Returns:
        DownloadResult with path to downloaded MP4
    """
    video_path = get_video_cache_path(video_id)
    
    # Check cache
    if not force and video_path.exists():
        print(f"  Using cached video: {video_path}")
        return DownloadResult(
            success=True,
            video_path=str(video_path)
        )
    
    # Ensure directory exists
    video_path.parent.mkdir(parents=True, exist_ok=True)
    
    # yt-dlp options for video download
    ydl_opts = {
        'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'outtmpl': str(video_path),
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
    }
    
    print(f"  Downloading video for {video_id}...")
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
        
        # Verify file exists
        if not video_path.exists():
            return DownloadResult(
                success=False,
                error="Download completed but file not found"
            )
        
        print(f"  Video downloaded: {video_path}")
        return DownloadResult(
            success=True,
            video_path=str(video_path)
        )
        
    except Exception as e:
        error_msg = str(e)
        print(f"  Video download failed: {error_msg[:100]}")
        return DownloadResult(
            success=False,
            error=error_msg
        )


def get_cache_stats() -> Dict:
    """Get statistics about cached files."""
    audio_files = list(settings.audio_cache_dir.glob("*.mp3"))
    video_files = list(settings.video_cache_dir.glob("*.mp4"))
    
    audio_size = sum(f.stat().st_size for f in audio_files)
    video_size = sum(f.stat().st_size for f in video_files)
    
    return {
        "audio_files": len(audio_files),
        "video_files": len(video_files),
        "audio_size_mb": round(audio_size / (1024 * 1024), 2),
        "video_size_mb": round(video_size / (1024 * 1024), 2),
        "total_size_mb": round((audio_size + video_size) / (1024 * 1024), 2)
    }


def clear_audio_cache():
    """Delete all cached audio files."""
    for f in settings.audio_cache_dir.glob("*.mp3"):
        f.unlink()
    print("Audio cache cleared")


def clear_video_cache():
    """Delete all cached video files."""
    for f in settings.video_cache_dir.glob("*.mp4"):
        f.unlink()
    print("Video cache cleared")


# For testing
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python downloader.py <youtube_url>")
        print("\nCache stats:", get_cache_stats())
        sys.exit(0)
    
    url = sys.argv[1]
    
    # Extract video ID from URL
    import re
    match = re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', url)
    if not match:
        print("Could not extract video ID from URL")
        sys.exit(1)
    
    video_id = match.group(1)
    
    print(f"Downloading audio for: {video_id}")
    result = download_audio(url, video_id)
    
    if result.success:
        print(f"Success! File at: {result.audio_path}")
    else:
        print(f"Failed: {result.error}")
