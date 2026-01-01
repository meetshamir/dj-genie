#!/usr/bin/env python3
"""
FAST 30-minute New Year 2026 Party Mix - Simple concatenation with fade transitions
"""

import os
import sys
import asyncio
import json
import subprocess
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from services.song_recommender import SongRecommender

def log(msg):
    print(f"[QUICK_MIX] {msg}")

def get_video_duration(video_path: str) -> float:
    """Get video duration using ffprobe"""
    try:
        result = subprocess.run([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ], capture_output=True, text=True)
        return float(result.stdout.strip())
    except:
        return 0

def download_video(youtube_id: str, output_path: Path) -> bool:
    """Download video using yt-dlp"""
    if output_path.exists():
        return True
    
    yt_dlp_path = Path(__file__).parent / ".venv" / "Scripts" / "yt-dlp.exe"
    
    try:
        cmd = [
            str(yt_dlp_path),
            f"https://www.youtube.com/watch?v={youtube_id}",
            "-f", "best[height<=720]/best",
            "--no-playlist",
            "-o", str(output_path),
            "--quiet",
            "--no-warnings"
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=180)
        return output_path.exists()
    except Exception as e:
        log(f"  Download error: {e}")
        return False

def extract_segment(video_path: Path, output_path: Path, start: float, duration: float) -> bool:
    """Extract a segment from video"""
    try:
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", str(video_path),
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "aac",
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
            str(output_path)
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=180)
        return output_path.exists()
    except Exception as e:
        log(f"  Extract error: {e}")
        return False

def concat_videos_fast(video_paths: list, output_path: Path) -> bool:
    """Fast concatenation using concat demuxer"""
    concat_file = output_path.parent / "concat_list.txt"
    
    with open(concat_file, "w") as f:
        for vp in video_paths:
            f.write(f"file '{vp}'\n")
    
    try:
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c:v", "libx264", "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            str(output_path)
        ]
        log(f"Concatenating {len(video_paths)} segments...")
        result = subprocess.run(cmd, capture_output=True, timeout=600)
        return output_path.exists()
    except Exception as e:
        log(f"Concat error: {e}")
        return False
    finally:
        if concat_file.exists():
            concat_file.unlink()

async def main():
    log("=" * 60)
    log("🎉 FAST 30-MINUTE NEW YEAR 2026 PARTY MIX 🎉")
    log("=" * 60)
    
    # Setup directories
    cache_dir = Path(__file__).parent / "backend" / "cache" / "quick_mix"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    export_dir = Path(__file__).parent / "exports"
    export_dir.mkdir(exist_ok=True)
    
    # Get song recommendations - 30 songs for ~30 min (60 sec each)
    log("\n🎵 Getting AI song recommendations...")
    recommender = SongRecommender()
    
    prompt = """Create a 30-minute New Year 2026 party mix with:
    - 5 Hindi/Bollywood bangers (Lungi Dance, Chaiyya Chaiyya, Jhoome Jo Pathaan)
    - 4 Tamil hits (Vaathi Coming, Arabic Kuthu, Rowdy Baby)
    - 3 Malayalam songs (Jimmiki Kammal, Illuminati)
    - 4 Punjabi tracks (GOAT, Brown Munde, Proper Patola)
    - 4 Arabic songs (Youm Wara Youm, Tamally Maak, Nour El Ain)
    - 3 Turkish songs (Şımarık, Tarkan)
    - 4 English classics (Thriller, Billie Jean, Industry Baby)
    - 3 90s hits (Informer, Ice Ice Baby)
    
    Total: 30 songs for ~30 minutes of party energy!
    """
    
    playlist_plan = recommender.parse_prompt(prompt, 30)
    if not playlist_plan:
        log("ERROR: Failed to get recommendations")
        return
    
    songs = [
        {
            'title': s.title,
            'artist': s.artist,
            'youtube_id': s.youtube_id,
            'search_query': s.search_query
        }
        for s in playlist_plan.songs
    ]
    
    # Search YouTube for each song
    log(f"✓ Got {len(songs)} song recommendations, searching YouTube...")
    for i, song in enumerate(songs):
        if not song.get('youtube_id'):
            result = recommender.search_youtube(song['search_query'])
            if result:
                song['youtube_id'] = result
                log(f"  [{i+1}] {song['title']}: Found")
            else:
                log(f"  [{i+1}] {song['title']}: Not found")
    
    # Filter songs with valid YouTube IDs
    songs = [s for s in songs if s.get('youtube_id')]
    log(f"✓ Found {len(songs)} songs on YouTube")
    
    # Download and extract segments
    log("\n📥 Downloading songs and extracting segments...")
    segments = []
    target_duration = 1800  # 30 minutes
    current_duration = 0
    segment_length = 60  # 60 seconds per song
    
    for i, song in enumerate(songs):
        if current_duration >= target_duration:
            break
            
        title = song.get('title', 'Unknown')
        youtube_id = song.get('youtube_id')
        
        if not youtube_id:
            log(f"  [{i+1}] {title}: No YouTube ID, skipping")
            continue
        
        log(f"  [{i+1}/{len(songs)}] {title}...")
        
        # Download
        video_path = cache_dir / f"song_{i:03d}.mp4"
        if not download_video(youtube_id, video_path):
            log(f"    ✗ Download failed")
            continue
        
        # Get duration
        duration = get_video_duration(video_path)
        if duration < 30:
            log(f"    ✗ Too short ({duration:.0f}s)")
            continue
        
        # Extract best segment (middle of song)
        start_time = max(30, (duration - segment_length) / 2)
        segment_path = cache_dir / f"segment_{len(segments):03d}.mp4"
        
        if extract_segment(video_path, segment_path, start_time, segment_length):
            segments.append(segment_path)
            current_duration += segment_length
            log(f"    ✓ Segment extracted ({current_duration//60}:{current_duration%60:02d} total)")
        else:
            log(f"    ✗ Extract failed")
        
        # Clean up full video to save space
        if video_path.exists():
            video_path.unlink()
    
    log(f"\n✓ Created {len(segments)} segments ({current_duration//60} minutes)")
    
    if len(segments) < 5:
        log("ERROR: Not enough segments!")
        return
    
    # Concatenate
    log("\n🎬 Creating final video...")
    output_path = export_dir / "new_year_2026_30min_party.mp4"
    
    if concat_videos_fast(segments, output_path):
        final_duration = get_video_duration(output_path)
        file_size = output_path.stat().st_size / (1024 * 1024)
        
        log("\n" + "=" * 60)
        log("🎉 SUCCESS! Your party mix is ready!")
        log("=" * 60)
        log(f"📁 File: {output_path}")
        log(f"⏱️  Duration: {final_duration//60:.0f} minutes {final_duration%60:.0f} seconds")
        log(f"📦 Size: {file_size:.1f} MB")
        log("=" * 60)
    else:
        log("ERROR: Failed to create final video")
    
    # Cleanup
    for seg in segments:
        if seg.exists():
            seg.unlink()

if __name__ == "__main__":
    asyncio.run(main())
