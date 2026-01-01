"""
Debug script for video export with detailed logging.
Tests each step of the export process and validates audio/video sync.
"""

import subprocess
import tempfile
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

def check_av_sync(video_path: Path, label: str = "") -> dict:
    """Check video and audio durations, return dict with info."""
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'stream=codec_type,duration',
        '-of', 'json',
        str(video_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {"error": result.stderr}
    
    import json
    data = json.loads(result.stdout)
    
    info = {"path": str(video_path), "label": label}
    for stream in data.get("streams", []):
        ctype = stream.get("codec_type")
        dur = float(stream.get("duration", 0))
        info[ctype] = dur
    
    if "video" in info and "audio" in info:
        info["diff"] = abs(info["video"] - info["audio"])
        info["sync_ok"] = info["diff"] < 0.5  # Allow 0.5s tolerance
    
    return info


def print_sync(info: dict):
    """Print sync info nicely."""
    label = info.get("label", "")
    video = info.get("video", 0)
    audio = info.get("audio", 0)
    diff = info.get("diff", 0)
    sync_ok = info.get("sync_ok", False)
    
    status = "✓ SYNC OK" if sync_ok else f"✗ OUT OF SYNC ({diff:.2f}s diff)"
    print(f"  {label:20} | Video: {video:7.2f}s | Audio: {audio:7.2f}s | {status}")


def get_video_info(video_path: Path) -> dict:
    """Get comprehensive video info."""
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration,size:stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels,duration',
        '-of', 'json',
        str(video_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {"error": result.stderr}
    
    import json
    return json.loads(result.stdout)


def run_test():
    """Run comprehensive export test with debugging."""
    print("="*70)
    print("VIDEO DJ EXPORT DEBUG TEST")
    print("="*70)
    
    # Import required modules
    from config import settings
    from services.exporter import (
        download_video, extract_and_overlay_segment, 
        create_intro_clip, create_outro_clip,
        simple_concat, create_transition_concat,
        get_video_duration
    )
    from services.dj_voice import add_dj_commentary_to_video
    
    temp_dir = Path(tempfile.mkdtemp())
    download_dir = temp_dir / "downloads"
    download_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nTemp directory: {temp_dir}")
    print(f"Exports directory: {settings.base_dir / 'exports'}")
    
    # Get test segments from database
    import sqlite3
    db_path = settings.base_dir / "database.sqlite"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute("""
        SELECT seg.id, seg.song_id, seg.start_time, seg.end_time, seg.energy_score,
               s.youtube_id, s.title, s.language, s.bpm
        FROM segments seg
        JOIN songs s ON seg.song_id = s.id
        ORDER BY seg.energy_score DESC
        LIMIT 3
    """)
    rows = cursor.fetchall()
    conn.close()
    
    if len(rows) < 3:
        print("ERROR: Need at least 3 segments in database")
        return
    
    print(f"\n--- TEST SEGMENTS ({len(rows)}) ---")
    test_segments = []
    for row in rows:
        seg_id, song_id, start, end, energy, yt_id, title, lang, bpm = row
        duration = end - start
        print(f"  [{lang:10}] {title[:40]:42} | {start:.1f}-{end:.1f}s ({duration:.1f}s)")
        test_segments.append({
            "youtube_id": yt_id,
            "start_time": start,
            "end_time": end,
            "title": title,
            "artist": "Unknown",
            "language": lang,
            "bpm": bpm or 120,
            "energy_score": energy
        })
    
    # Step 1: Download videos
    print("\n--- STEP 1: DOWNLOAD VIDEOS ---")
    downloaded = []
    for i, seg in enumerate(test_segments):
        print(f"  Downloading {seg['youtube_id']}...")
        path = download_video(seg["youtube_id"], download_dir, "720p")
        if path:
            info = check_av_sync(path, f"download_{i}")
            print_sync(info)
            downloaded.append({"path": path, "segment": seg, "sync": info})
        else:
            print(f"  ERROR: Failed to download {seg['youtube_id']}")
    
    if len(downloaded) < 3:
        print("ERROR: Failed to download enough videos")
        return
    
    # Step 2: Extract segments with overlay
    print("\n--- STEP 2: EXTRACT SEGMENTS ---")
    extracted = []
    for i, dl in enumerate(downloaded):
        seg = dl["segment"]
        out_path = temp_dir / f"segment_{i:03d}.mp4"
        print(f"  Extracting segment {i+1}: {seg['start_time']:.1f}-{seg['end_time']:.1f}s...")
        
        success = extract_and_overlay_segment(
            dl["path"],
            out_path,
            seg["start_time"],
            seg["end_time"],
            seg["title"],
            seg["artist"],
            seg["language"],
            add_overlay=True,
            width=1280, height=720
        )
        
        if success and out_path.exists():
            info = check_av_sync(out_path, f"segment_{i}")
            print_sync(info)
            extracted.append({"path": out_path, "segment": seg, "sync": info})
        else:
            print(f"  ERROR: Failed to extract segment {i}")
    
    # Step 3: Create intro/outro
    print("\n--- STEP 3: CREATE INTRO/OUTRO ---")
    intro_path = temp_dir / "intro.mp4"
    outro_path = temp_dir / "outro.mp4"
    
    create_intro_clip(intro_path, "DEBUG TEST MIX", 4.0, 1280, 720)
    if intro_path.exists():
        info = check_av_sync(intro_path, "intro")
        print_sync(info)
    
    create_outro_clip(outro_path, "Thanks for testing!", 3.0, 1280, 720)
    if outro_path.exists():
        info = check_av_sync(outro_path, "outro")
        print_sync(info)
    
    # Step 4: Test simple concat (no transitions)
    print("\n--- STEP 4a: SIMPLE CONCAT (no transitions) ---")
    simple_output = temp_dir / "simple_concat.mp4"
    all_files = [intro_path] + [e["path"] for e in extracted] + [outro_path]
    
    print(f"  Concatenating {len(all_files)} files...")
    for f in all_files:
        print(f"    - {f.name}")
    
    success = simple_concat(all_files, simple_output)
    if success and simple_output.exists():
        info = check_av_sync(simple_output, "simple_concat")
        print_sync(info)
        print(f"  File size: {simple_output.stat().st_size / 1024 / 1024:.2f} MB")
    else:
        print("  ERROR: Simple concat failed!")
    
    # Step 4b: Test transition concat
    print("\n--- STEP 4b: TRANSITION CONCAT ---")
    trans_output = temp_dir / "transition_concat.mp4"
    
    print(f"  Creating transitions between {len(all_files)} files...")
    success = create_transition_concat(all_files, trans_output, "random", 1.0)
    if success and trans_output.exists():
        info = check_av_sync(trans_output, "transition_concat")
        print_sync(info)
        print(f"  File size: {trans_output.stat().st_size / 1024 / 1024:.2f} MB")
        
        # Save without DJ for comparison
        import shutil
        no_dj_path = settings.base_dir / "exports" / "debug_no_dj.mp4"
        shutil.copy(trans_output, no_dj_path)
        print(f"  Saved to: {no_dj_path}")
    else:
        print("  ERROR: Transition concat failed!")
        trans_output = simple_output  # Fall back
    
    # Step 5: Add DJ voice
    print("\n--- STEP 5: ADD DJ VOICE ---")
    dj_output = temp_dir / "with_dj.mp4"
    
    segment_info = [
        {
            "title": e["segment"]["title"],
            "artist": e["segment"]["artist"],
            "language": e["segment"]["language"],
            "energy_score": e["segment"]["energy_score"],
            "bpm": e["segment"]["bpm"],
        }
        for e in extracted
    ]
    
    source_video = trans_output if trans_output.exists() else simple_output
    print(f"  Source video: {source_video}")
    print(f"  Adding DJ commentary...")
    
    success, timeline = add_dj_commentary_to_video(
        source_video, segment_info, dj_output, 
        "energetic_male", "frequent"
    )
    
    if success and dj_output.exists():
        info = check_av_sync(dj_output, "with_dj")
        print_sync(info)
        print(f"  File size: {dj_output.stat().st_size / 1024 / 1024:.2f} MB")
        
        # Save final output
        import shutil
        final_path = settings.base_dir / "exports" / "debug_with_dj.mp4"
        shutil.copy(dj_output, final_path)
        print(f"  Saved to: {final_path}")
        
        print("\n  DJ Timeline:")
        for t in timeline:
            print(f"    - {t['type'].upper():8} @ {t['start_time']:.1f}s - {t['end_time']:.1f}s")
    else:
        print("  ERROR: DJ voice failed!")
    
    # Cleanup
    print("\n--- CLEANUP ---")
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    print("  Temp files cleaned up")
    
    # Summary
    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)
    print("\nCheck exported files:")
    print(f"  - debug_no_dj.mp4 (without DJ voice)")
    print(f"  - debug_with_dj.mp4 (with DJ voice)")
    print("\nPlay both and verify:")
    print("  1. Audio plays for the full duration")
    print("  2. Video transitions are visible between segments")
    print("  3. DJ voice is audible at start, middle, and end")


if __name__ == "__main__":
    run_test()
