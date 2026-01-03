"""
Video DJ Playlist Exporter
Handles video export with transitions, text overlays, intro/outro, and DJ voice.
"""

import os
import subprocess
import tempfile
import logging
import shutil
import datetime
import sys
from pathlib import Path
from typing import List, Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


def get_ffmpeg_path() -> str:
    """Find FFmpeg executable path."""
    # Try common Windows locations
    candidates = [
        Path.home() / "AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.0.1-full_build/bin/ffmpeg.exe",
        Path("C:/ffmpeg/bin/ffmpeg.exe"),
        Path("C:/Program Files/ffmpeg/bin/ffmpeg.exe"),
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    # Fall back to PATH
    return "ffmpeg"


def get_ffprobe_path() -> str:
    """Find FFprobe executable path."""
    ffmpeg_path = get_ffmpeg_path()
    return ffmpeg_path.replace("ffmpeg.exe", "ffprobe.exe") if ffmpeg_path.endswith(".exe") else "ffprobe"


# Cache the paths
FFMPEG = get_ffmpeg_path()
FFPROBE = get_ffprobe_path()
logger.info(f"FFmpeg path: {FFMPEG}")


def log(msg: str):
    """Print with immediate flush for logging."""
    print(msg, flush=True)


@dataclass
class ExportSegment:
    """A segment to include in the export."""
    youtube_id: str
    youtube_url: str
    start_time: float
    end_time: float
    song_title: str
    language: str
    position: int
    artist: str = "Unknown Artist"
    bpm: float = 120.0


@dataclass
class ExportProgress:
    """Progress update for export operation."""
    status: str  # "downloading", "processing", "concatenating", "complete", "failed"
    progress: float  # 0-100
    current_step: str
    segment_index: int
    total_segments: int
    error: Optional[str] = None


@dataclass
class ExportResult:
    """Result of export operation."""
    success: bool
    output_path: Optional[str] = None
    duration_seconds: float = 0
    file_size_bytes: int = 0
    error: Optional[str] = None


def escape_ffmpeg_text(text: str) -> str:
    """Escape special characters for FFmpeg drawtext filter."""
    if not text:
        return ""
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "'\\''")
    text = text.replace(":", "\\:")
    text = text.replace("[", "\\[")
    text = text.replace("]", "\\]")
    return text


def get_video_dimensions(video_path: Path) -> tuple:
    """Get video width and height using ffprobe."""
    cmd = [
        FFPROBE, '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height',
        '-of', 'csv=p=0',
        str(video_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            parts = result.stdout.strip().split(',')
            if len(parts) == 2:
                return int(parts[0]), int(parts[1])
    except Exception as e:
        logger.warning(f"Could not get video dimensions: {e}")
    return 1280, 720


def get_video_duration(video_path: Path) -> float:
    """Get video duration using ffprobe."""
    cmd = [
        FFPROBE, '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(video_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception as e:
        logger.warning(f"Could not get video duration: {e}")
    return 30.0


def download_video(youtube_id: str, output_dir: Path, quality: str = "720p") -> Optional[Path]:
    """Download a YouTube video using yt-dlp Python library."""
    import yt_dlp
    
    quality_map = {
        "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
        "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
    }
    format_str = quality_map.get(quality, quality_map["720p"])
    output_path = output_dir / f"{youtube_id}.mp4"
    
    if output_path.exists():
        logger.info(f"Video already downloaded: {youtube_id}")
        return output_path
    
    ydl_opts = {
        'format': format_str,
        'outtmpl': str(output_path),
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f'https://www.youtube.com/watch?v={youtube_id}'])
        
        if output_path.exists():
            logger.info(f"Downloaded video: {youtube_id}")
            return output_path
        else:
            logger.error(f"Download completed but file not found: {youtube_id}")
            return None
    except Exception as e:
        logger.error(f"Failed to download {youtube_id}: {e}")
        return None


def create_intro_clip(
    output_path: Path,
    playlist_name: str = "DJ MIX",
    duration: float = 4.0,
    width: int = 1280,
    height: int = 720
) -> bool:
    """Create an intro clip with animated text and fade from black."""
    date_str = datetime.datetime.now().strftime("%B %d, %Y")
    
    title_size = max(48, int(height / 10))
    date_size = max(24, int(height / 24))
    
    alpha_expr = "if(lt(t,0.5),0,if(lt(t,1.5),(t-0.5),1))"
    
    filter_complex = (
        f"[0:v]drawtext=text='{escape_ffmpeg_text(playlist_name)}':"
        f"fontsize={title_size}:fontcolor=white:"
        f"x=(w-text_w)/2:y=(h-text_h)/2-40:"
        f"alpha='{alpha_expr}',"
        f"drawtext=text='{escape_ffmpeg_text(date_str)}':"
        f"fontsize={date_size}:fontcolor=white@0.8:"
        f"x=(w-text_w)/2:y=(h/2)+30:"
        f"alpha='{alpha_expr}',"
        f"fade=t=in:st=0:d=0.5[v];"
        f"[1:a]atrim=0:{duration},afade=t=out:st={duration-1}:d=1[a]"
    )
    
    cmd = [
        FFMPEG, '-y',
        '-f', 'lavfi', '-i', f'color=c=black:s={width}x{height}:d={duration}',
        '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',
        '-filter_complex', filter_complex,
        '-map', '[v]', '-map', '[a]',
        '-c:v', 'libx264', '-c:a', 'aac',
        '-t', str(duration),
        str(output_path)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"Created intro clip: {output_path}")
            return True
        else:
            logger.error(f"Failed to create intro: {result.stderr[:200]}")
            return False
    except Exception as e:
        logger.error(f"Exception creating intro: {e}")
        return False


def create_outro_clip(
    output_path: Path,
    message: str = "Thanks for listening!",
    duration: float = 3.0,
    width: int = 1280,
    height: int = 720
) -> bool:
    """Create an outro clip with fade to black."""
    text_size = max(36, int(height / 14))
    
    filter_complex = (
        f"[0:v]drawtext=text='{escape_ffmpeg_text(message)}':"
        f"fontsize={text_size}:fontcolor=white:"
        f"x=(w-text_w)/2:y=(h-text_h)/2:"
        f"alpha='if(lt(t,{duration-1}),1,1-(t-{duration-1}))',"
        f"fade=t=out:st={duration-1}:d=1[v];"
        f"[1:a]atrim=0:{duration},afade=t=out:st={duration-1}:d=1[a]"
    )
    
    cmd = [
        FFMPEG, '-y',
        '-f', 'lavfi', '-i', f'color=c=black:s={width}x{height}:d={duration}',
        '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo',
        '-filter_complex', filter_complex,
        '-map', '[v]', '-map', '[a]',
        '-c:v', 'libx264', '-c:a', 'aac',
        '-t', str(duration),
        str(output_path)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"Created outro clip: {output_path}")
            return True
        else:
            logger.error(f"Failed to create outro: {result.stderr[:200]}")
            return False
    except Exception as e:
        logger.error(f"Exception creating outro: {e}")
        return False


def extract_and_overlay_segment(
    video_path: Path,
    output_path: Path,
    start_time: float,
    end_time: float,
    title: str,
    artist: str,
    language: str = None,
    add_overlay: bool = True,
    width: int = 1280,
    height: int = 720
) -> bool:
    """Extract a segment from video and optionally add text overlay."""
    duration = end_time - start_time
    
    # Build filter chain
    filters = [f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2']
    
    if add_overlay:
        title_size = max(28, int(height / 20))
        artist_size = max(20, int(height / 28))
        badge_size = max(16, int(height / 36))
        padding = int(height / 20)
        
        show_duration = min(6.0, duration - 1)
        alpha_expr = f"if(lt(t,1),t,if(lt(t,{show_duration-1}),1,1-(t-{show_duration-1})))"
        
        filters.append(
            f"drawtext=text='{escape_ffmpeg_text(title)}':"
            f"fontsize={title_size}:fontcolor=white:"
            f"borderw=2:bordercolor=black@0.7:"
            f"x={padding}:y=h-{padding + artist_size + title_size + 10}:"
            f"alpha='{alpha_expr}'"
        )
        
        filters.append(
            f"drawtext=text='{escape_ffmpeg_text(artist)}':"
            f"fontsize={artist_size}:fontcolor=white@0.85:"
            f"borderw=1:bordercolor=black@0.6:"
            f"x={padding}:y=h-{padding + artist_size}:"
            f"alpha='{alpha_expr}'"
        )
        
        if language:
            filters.append(
                f"drawtext=text='  {escape_ffmpeg_text(language.upper())}  ':"
                f"fontsize={badge_size}:fontcolor=white:"
                f"box=1:boxcolor=blue@0.7:boxborderw=4:"
                f"x=w-{padding}-text_w:y={padding}:"
                f"alpha='{alpha_expr}'"
            )
    
    video_filter = ",".join(filters)
    
    # Use -shortest to sync audio/video, and setpts/asetpts to reset timestamps
    cmd = [
        FFMPEG, '-y',
        '-ss', str(start_time),
        '-i', str(video_path),
        '-t', str(duration),
        '-vf', f'{video_filter},setpts=PTS-STARTPTS',
        '-af', 'asetpts=PTS-STARTPTS',
        '-c:v', 'libx264', '-preset', 'fast',
        '-c:a', 'aac', '-ar', '44100', '-ac', '2',
        '-r', '30',
        '-vsync', 'cfr',
        '-async', '1',
        '-shortest',
        str(output_path)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return True
        else:
            logger.error(f"Failed to extract segment: {result.stderr[:200]}")
            return False
    except Exception as e:
        logger.error(f"Exception extracting segment: {e}")
        return False


def simple_concat(video_files: List[Path], output_path: Path) -> bool:
    """Simple concatenation with re-encoding and A/V sync fix."""
    print(f"[CONCAT] Starting simple concat: {len(video_files)} files")
    logger.info(f"Simple concat: {len(video_files)} files")
    
    # First, normalize all input files to ensure consistent A/V sync
    temp_dir = Path(tempfile.mkdtemp())
    normalized_files = []
    
    for i, video_file in enumerate(video_files):
        print(f"[CONCAT]   - {video_file.name}")
        logger.info(f"  - {video_file.name}")
        
        # Check A/V sync
        v_dur, a_dur = get_stream_durations(video_file)
        sync_diff = abs(v_dur - a_dur) if v_dur > 0 and a_dur > 0 else 0
        
        if sync_diff > 0.1:
            # Need to fix sync
            print(f"[CONCAT]     Fixing A/V sync (v={v_dur:.2f}s, a={a_dur:.2f}s)")
            min_dur = min(v_dur, a_dur) if v_dur > 0 and a_dur > 0 else max(v_dur, a_dur)
            fixed_path = temp_dir / f"fixed_{i}.mp4"
            fix_cmd = [
                FFMPEG, '-y', '-i', str(video_file),
                '-t', str(min_dur),
                '-c:v', 'libx264', '-preset', 'fast',
                '-c:a', 'aac', '-ar', '44100', '-ac', '2',
                '-vsync', 'cfr', '-r', '30',
                str(fixed_path)
            ]
            fix_result = subprocess.run(fix_cmd, capture_output=True, text=True)
            if fix_result.returncode == 0 and fixed_path.exists():
                normalized_files.append(fixed_path)
            else:
                normalized_files.append(video_file)
        else:
            normalized_files.append(video_file)
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        for video_file in normalized_files:
            f.write(f"file '{video_file}'\n")
        concat_file = f.name
    
    # Re-encode to ensure audio sync (not just copy)
    cmd = [
        FFMPEG, '-y',
        '-f', 'concat', '-safe', '0',
        '-i', concat_file,
        '-c:v', 'libx264', '-preset', 'fast',
        '-c:a', 'aac', '-ar', '44100', '-ac', '2',
        '-vsync', 'cfr', '-r', '30',
        str(output_path)
    ]
    
    try:
        print(f"[CONCAT] Running ffmpeg...")
        logger.info(f"Running concat command...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        Path(concat_file).unlink()
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        if result.returncode != 0:
            print(f"[CONCAT] FAILED: {result.stderr[:300]}")
            logger.error(f"Concat failed: {result.stderr[:500]}")
        else:
            # Verify output sync
            out_v, out_a = get_stream_durations(output_path)
            sync_diff = abs(out_v - out_a)
            print(f"[CONCAT] SUCCESS: {output_path}")
            print(f"[CONCAT] Output: v={out_v:.2f}s, a={out_a:.2f}s, diff={sync_diff:.2f}s")
            logger.info(f"Concat successful: {output_path}")
            logger.info(f"Output sync: v={out_v:.1f}s, a={out_a:.1f}s, diff={sync_diff:.1f}s")
        return result.returncode == 0
    except Exception as e:
        print(f"[CONCAT] EXCEPTION: {e}")
        logger.error(f"Simple concat exception: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False


def get_stream_durations(video_path: Path) -> tuple:
    """Get both video and audio stream durations separately."""
    cmd = [
        FFPROBE, '-v', 'error',
        '-show_entries', 'stream=codec_type,duration',
        '-of', 'json',
        str(video_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            video_dur = 0
            audio_dur = 0
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    video_dur = float(stream.get("duration", 0))
                elif stream.get("codec_type") == "audio":
                    audio_dur = float(stream.get("duration", 0))
            return video_dur, audio_dur
    except Exception as e:
        logger.warning(f"Could not get stream durations: {e}")
    return 0, 0


def create_transition_pair(
    video1: Path,
    video2: Path,
    output_path: Path,
    transition_type: str = "fade",
    transition_duration: float = 3.5
) -> bool:
    """Create a transition between two video clips with proper A/V sync and extended audio crossfade."""
    print(f"[TRANSITION] Creating transition between {video1.name} and {video2.name}")
    
    valid_transitions = [
        'fade', 'fadeblack', 'fadewhite', 'wipeleft', 'wiperight',
        'wipeup', 'wipedown', 'slideleft', 'slideright', 'slideup',
        'slidedown', 'circlecrop', 'rectcrop', 'distance', 'smoothleft',
        'smoothright', 'smoothup', 'smoothdown', 'circleopen', 'circleclose',
        'dissolve', 'pixelize', 'radial', 'hblur'
    ]
    
    if transition_type not in valid_transitions:
        transition_type = 'fade'
    
    # Get BOTH video and audio durations to ensure sync
    v1_video, v1_audio = get_stream_durations(video1)
    v2_video, v2_audio = get_stream_durations(video2)
    
    # Use the minimum of video duration for transition timing
    # This ensures we don't have audio extending past video
    dur1 = min(v1_video, v1_audio) if v1_video > 0 and v1_audio > 0 else max(v1_video, v1_audio)
    dur2 = min(v2_video, v2_audio) if v2_video > 0 and v2_audio > 0 else max(v2_video, v2_audio)
    
    print(f"[TRANSITION] Video1: v={v1_video:.2f}s, a={v1_audio:.2f}s, using={dur1:.2f}s")
    print(f"[TRANSITION] Video2: v={v2_video:.2f}s, a={v2_audio:.2f}s, using={dur2:.2f}s")
    logger.info(f"Transition {transition_type}: video1={dur1:.1f}s, video2={dur2:.1f}s")
    
    # Allow longer transitions (up to 40% of shorter clip) for smooth blending
    # Minimum 2s, maximum capped by available content
    transition_duration = max(2.0, min(transition_duration, dur1 * 0.4, dur2 * 0.4))
    
    # Offset for xfade: when second video starts overlapping first
    offset = max(0, dur1 - transition_duration)
    
    print(f"[TRANSITION] Type: {transition_type}, Duration: {transition_duration:.2f}s, Offset: {offset:.2f}s")
    
    # Use trim filters and proper audio mixing to keep A/V in sync
    # The key is: video xfade uses an offset, but audio needs adelay to match
    # 
    # Timeline visualization:
    # Video1: [========]
    # Video2:      [========]  (starts at 'offset')
    # xfade:       [==]        (transition_duration long)
    #
    # For audio, we need the same timing:
    # Audio1: [========]       (plays until offset + transition)
    # Audio2:      [========]  (starts at offset, faded in during transition)
    
    # Calculate the exact timing
    # Audio 1 plays for (offset + transition_duration), then fades out during transition
    # Audio 2 starts at 'offset' with delay, fades in during transition
    
    filter_complex = (
        # Trim and prepare video streams
        f"[0:v]trim=0:{dur1},setpts=PTS-STARTPTS,fps=30[v0];"
        f"[1:v]trim=0:{dur2},setpts=PTS-STARTPTS,fps=30[v1];"
        # Trim and prepare audio streams
        f"[0:a]atrim=0:{dur1},asetpts=PTS-STARTPTS[a0];"
        f"[1:a]atrim=0:{dur2},asetpts=PTS-STARTPTS[a1];"
        # Apply xfade transition to video
        f"[v0][v1]xfade=transition={transition_type}:duration={transition_duration}:offset={offset}[v];"
        # For audio: delay second audio to start at offset, then mix with crossfade
        # Fade out audio1 during the transition, fade in audio2
        f"[a0]afade=t=out:st={offset}:d={transition_duration}[a0f];"
        f"[a1]adelay={int(offset * 1000)}|{int(offset * 1000)},afade=t=in:st=0:d={transition_duration}[a1f];"
        f"[a0f][a1f]amix=inputs=2:duration=longest:normalize=0[a]"
    )
    
    cmd = [
        FFMPEG, '-y',
        '-i', str(video1),
        '-i', str(video2),
        '-filter_complex', filter_complex,
        '-map', '[v]', '-map', '[a]',
        '-c:v', 'libx264', '-preset', 'fast',
        '-c:a', 'aac', '-ar', '44100', '-ac', '2',
        '-vsync', 'cfr', '-r', '30',
        str(output_path)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            # Verify output sync
            out_v, out_a = get_stream_durations(output_path)
            sync_diff = abs(out_v - out_a)
            print(f"[TRANSITION] Success! Output: v={out_v:.2f}s, a={out_a:.2f}s, diff={sync_diff:.2f}s")
            logger.info(f"Transition successful: output v={out_v:.1f}s, a={out_a:.1f}s")
            
            if sync_diff > 0.5:
                print(f"[TRANSITION] WARNING: A/V sync issue detected ({sync_diff:.2f}s diff)")
                logger.warning(f"A/V sync issue: {sync_diff:.2f}s difference")
            
            return True
        else:
            print(f"[TRANSITION] FFmpeg failed: {result.stderr[:300]}")
            logger.warning(f"Transition failed: {result.stderr[:300]}")
            logger.info("Falling back to simple concat")
            return simple_concat([video1, video2], output_path)
    except Exception as e:
        print(f"[TRANSITION] Exception: {e}")
        logger.error(f"Exception in transition: {e}")
        return simple_concat([video1, video2], output_path)


def create_transition_concat(
    video_files: List[Path],
    output_path: Path,
    transition_type: str = "random",
    transition_duration: float = 3.5
) -> bool:
    """Concatenate multiple videos with extended crossfade transitions for smooth music blending."""
    print(f"[TRANSITION_CONCAT] Starting with {len(video_files)} files, crossfade={transition_duration}s")
    
    if len(video_files) == 0:
        print("[TRANSITION_CONCAT] No files provided!")
        return False
    if len(video_files) == 1:
        print("[TRANSITION_CONCAT] Only 1 file, copying directly")
        shutil.copy(video_files[0], output_path)
        return True
    
    # Use more visually prominent transitions
    # These are the most visible and DJ-friendly transitions
    transitions = [
        'fade',          # Classic fade - always works well
        'dissolve',      # Smooth dissolve between clips
        'fadeblack',     # Fade through black - very DJ-like
        'fadewhite',     # Fade through white - energetic feel
        'circlecrop',    # Circle transition - very noticeable
        'circleopen',    # Circle opens to reveal next clip
        'radial',        # Radial wipe - dynamic
        'wipeleft',      # Horizontal wipe - professional
        'wiperight',     # Horizontal wipe other direction
        'smoothleft',    # Smooth horizontal transition
        'smoothright',   # Smooth horizontal other way
    ]
    
    temp_dir = Path(tempfile.mkdtemp())
    current_video = video_files[0]
    
    # Check initial A/V sync
    v_dur, a_dur = get_stream_durations(current_video)
    print(f"[TRANSITION_CONCAT] Initial file: {current_video.name} (v={v_dur:.2f}s, a={a_dur:.2f}s)")
    
    try:
        for i, next_video in enumerate(video_files[1:]):
            if transition_type == "random":
                trans = transitions[i % len(transitions)]
            else:
                trans = transition_type
            
            temp_output = temp_dir / f"transition_{i}.mp4"
            
            nv_dur, na_dur = get_stream_durations(next_video)
            print(f"[TRANSITION_CONCAT] Transition {i+1}/{len(video_files)-1}: {trans}")
            print(f"[TRANSITION_CONCAT]   Current: {current_video.name} (v={v_dur:.2f}s)")
            print(f"[TRANSITION_CONCAT]   Next: {next_video.name} (v={nv_dur:.2f}s, a={na_dur:.2f}s)")
            logger.info(f"Creating transition {i+1}/{len(video_files)-1}: {trans}")
            
            success = create_transition_pair(
                current_video,
                next_video,
                temp_output,
                trans,
                transition_duration
            )
            
            if not success:
                print(f"[TRANSITION_CONCAT] Transition {i+1} failed, falling back to simple concat")
                logger.error(f"Transition {i+1} failed")
                shutil.rmtree(temp_dir, ignore_errors=True)
                return simple_concat(video_files, output_path)
            
            # Update for next iteration
            current_video = temp_output
            v_dur, a_dur = get_stream_durations(current_video)
            print(f"[TRANSITION_CONCAT]   Result: {temp_output.name} (v={v_dur:.2f}s, a={a_dur:.2f}s)")
        
        # Final copy
        shutil.copy(current_video, output_path)
        
        # Check final output
        final_v, final_a = get_stream_durations(output_path)
        sync_diff = abs(final_v - final_a)
        print(f"[TRANSITION_CONCAT] Final output: v={final_v:.2f}s, a={final_a:.2f}s, diff={sync_diff:.2f}s")
        
        if sync_diff > 0.5:
            print(f"[TRANSITION_CONCAT] WARNING: A/V sync issue in final output!")
            logger.warning(f"A/V sync issue in final output: {sync_diff:.2f}s")
        
        shutil.rmtree(temp_dir, ignore_errors=True)
        return True
        
    except Exception as e:
        print(f"[TRANSITION_CONCAT] Exception: {e}")
        logger.error(f"Exception in transition concat: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return simple_concat(video_files, output_path)


def export_playlist(
    segments: List[ExportSegment],
    output_name: str = "dj_mix",
    crossfade_duration: float = 3.5,
    transition_type: str = "random",
    add_text_overlay: bool = True,
    video_quality: str = "720p",
    dj_enabled: bool = False,
    dj_voice: str = "energetic_male",
    dj_frequency: str = "moderate",
    dj_context: dict = None,  # New: DJ context with theme, mood, etc.
    progress_callback: Callable[[ExportProgress], None] = None
) -> ExportResult:
    """
    Export a playlist of video segments into a single video.
    
    Args:
        segments: List of ExportSegment objects
        output_name: Name for output file (without extension)
        crossfade_duration: Duration of transitions in seconds (default 3.5s for smooth blending)
        transition_type: "random" or specific type like "fade", "dissolve", etc.
        add_text_overlay: Whether to add song title/artist overlay
        video_quality: "480p", "720p", or "1080p"
        dj_enabled: Whether to add AI DJ voice commentary
        dj_voice: Voice style for DJ
        dj_frequency: How often DJ speaks
        dj_context: Context for DJ (theme, mood, shoutouts) - uses Azure OpenAI GPT
        progress_callback: Callback for progress updates
    
    Returns:
        ExportResult with success status and output path
    """
    if not segments:
        return ExportResult(success=False, error="No segments to export")
    
    # Setup paths
    from config import settings
    temp_dir = Path(tempfile.mkdtemp())
    download_dir = temp_dir / "downloads"
    download_dir.mkdir(parents=True, exist_ok=True)
    
    exports_dir = settings.base_dir / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    output_path = exports_dir / f"{output_name}.mp4"
    
    # Resolution settings
    resolution_map = {"480p": (854, 480), "720p": (1280, 720), "1080p": (1920, 1080)}
    width, height = resolution_map.get(video_quality, (1280, 720))
    
    segment_files = []
    total_steps = len(segments) + 3  # downloads/processing + intro + outro + concat
    
    def update_progress(status: str, progress: float, step: str, seg_idx: int = 0):
        if progress_callback:
            progress_callback(ExportProgress(
                status=status,
                progress=progress,
                current_step=step,
                segment_index=seg_idx,
                total_segments=len(segments)
            ))
        logger.info(f"[{progress:.1f}%] {step}")
    
    try:
        # Step 1: Create intro
        update_progress("processing", 5, "Creating intro...", 0)
        intro_path = temp_dir / "intro.mp4"
        if create_intro_clip(intro_path, "DJ MIX", 4.0, width, height):
            segment_files.append(intro_path)
        
        # Step 2: Download and process each segment
        for i, segment in enumerate(segments):
            progress = 10 + (i / len(segments)) * 70  # 10% to 80%
            song_name = segment.song_title[:30] if segment.song_title else f"Song {i+1}"
            update_progress("downloading", progress, f"Downloading: {song_name} ({i+1}/{len(segments)})", i)
            
            # Use source_path if available (from auto_playlist), otherwise download
            if hasattr(segment, 'source_path') and segment.source_path and Path(segment.source_path).exists():
                video_path = Path(segment.source_path)
                logger.info(f"Using local video: {video_path}")
                update_progress("processing", progress + 1, f"Found cached: {song_name}", i)
            else:
                # Download video
                video_path = download_video(segment.youtube_id, download_dir, video_quality)
            
            if not video_path:
                logger.warning(f"Skipping segment {i}: download failed")
                update_progress("processing", progress + 1, f"Skipped: {song_name} (download failed)", i)
                continue
            
            update_progress("processing", progress + 3, f"Cutting & overlaying: {song_name}", i)
            
            # Extract segment with overlay
            processed_path = temp_dir / f"segment_{i:03d}.mp4"
            success = extract_and_overlay_segment(
                video_path,
                processed_path,
                segment.start_time,
                segment.end_time,
                segment.song_title,
                segment.artist,
                segment.language,
                add_text_overlay,
                width, height
            )
            
            if success:
                segment_files.append(processed_path)
            else:
                logger.warning(f"Failed to process segment {i}")
        
        if len(segment_files) <= 1:  # Only intro or nothing
            shutil.rmtree(temp_dir, ignore_errors=True)
            return ExportResult(success=False, error="No segments were successfully processed")
        
        # Step 3: Create outro
        update_progress("processing", 82, "Creating outro clip...", len(segments))
        outro_path = temp_dir / "outro.mp4"
        if create_outro_clip(outro_path, "Thanks for listening!", 3.0, width, height):
            segment_files.append(outro_path)
        
        # Step 4: Concatenate with transitions
        update_progress("concatenating", 84, f"Joining {len(segment_files)} clips with crossfade transitions...", len(segments))
        
        if crossfade_duration > 0 and len(segment_files) > 1:
            success = create_transition_concat(
                segment_files,
                output_path,
                transition_type,
                crossfade_duration
            )
        else:
            success = simple_concat(segment_files, output_path)
        
        if not success:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return ExportResult(success=False, error="Failed to concatenate segments")
        
        # Step 5: Add DJ voice if enabled
        dj_timeline = []
        if dj_enabled:
            update_progress("processing", 88, "Preparing AI DJ voice commentary...", len(segments))
            
            # Create a progress callback for DJ voice that updates the main progress
            def dj_progress_callback(step: str, detail: str = ""):
                # Map DJ steps to progress percentages (88% to 98%)
                step_progress = {
                    "Analyzing video": 88,
                    "Generating DJ script": 89,
                    "Planning DJ moments": 90,
                }
                # Recording voice clips: 90% to 96%
                if step.startswith("Recording voice"):
                    # Extract clip number from step like "Recording voice (3/8)"
                    import re
                    match = re.search(r'\((\d+)/(\d+)\)', step)
                    if match:
                        current, total = int(match.group(1)), int(match.group(2))
                        progress = 90 + (current / total) * 6  # 90% to 96%
                    else:
                        progress = 93
                elif step == "Mixing DJ voice":
                    progress = 97
                else:
                    progress = step_progress.get(step, 92)
                
                update_progress("processing", progress, f"DJ: {step}" + (f" - {detail}" if detail else ""), len(segments))
            
            print("="*50)
            print("[DJ] STARTING DJ VOICE PROCESSING")
            print(f"[DJ] Input video: {output_path}")
            print(f"[DJ] Video exists: {output_path.exists()}")
            print(f"[DJ] DJ Context provided: {dj_context is not None}")
            if output_path.exists():
                print(f"[DJ] Video size: {output_path.stat().st_size} bytes")
            print("="*50)
            logger.info("="*50)
            logger.info("STARTING DJ VOICE PROCESSING")
            logger.info(f"Input video: {output_path}")
            logger.info(f"DJ Context: {dj_context}")
            logger.info("="*50)
            
            try:
                # Build segment info for DJ with actual timing in the final video
                # Calculate cumulative start times accounting for intro (4s) and transitions (1.5s each)
                intro_duration = 4.0
                transition_duration = crossfade_duration  # 1.5s typically
                
                segment_info = []
                cumulative_time = intro_duration  # Start after intro
                
                for i, s in enumerate(segments):
                    seg_duration = s.end_time - s.start_time  # Actual duration of this segment
                    
                    segment_info.append({
                        "song_title": s.song_title,
                        "title": s.song_title,
                        "artist": s.artist,
                        "language": s.language,
                        "start_time": s.start_time,  # Original source time
                        "video_start_time": cumulative_time,  # When this song starts in the final video
                        "segment_duration": seg_duration,  # How long this segment plays
                        "energy_score": 0.7,  # Default energy
                        "bpm": getattr(s, 'bpm', 120),
                        "position": i
                    })
                    
                    # Next segment starts after this one, minus transition overlap
                    cumulative_time += seg_duration - (transition_duration if i < len(segments) - 1 else 0)
                
                print(f"[DJ] Segment count: {len(segment_info)}")
                logger.info(f"Segment info: {segment_info}")
                
                # Map voice parameter names
                voice_map = {
                    "energetic_male": "energetic_male",
                    "energetic_female": "energetic_female",
                    "deep_male": "deep_male",
                    "party_female": "party_female",
                    "hype_male": "hype_male",
                }
                dj_voice_mapped = voice_map.get(dj_voice, "energetic_male")
                print(f"[DJ] Voice: {dj_voice_mapped}, Frequency: {dj_frequency}")
                logger.info(f"DJ Voice: {dj_voice_mapped}, Frequency: {dj_frequency}")
                
                dj_output = temp_dir / "with_dj.mp4"
                success = False
                
                # Try Azure OpenAI DJ voice first (if context provided or Azure is available)
                if dj_context:
                    print("[DJ] Using Azure OpenAI DJ voice with context...")
                    logger.info("Using Azure OpenAI DJ voice with context")
                    try:
                        from services.azure_dj_voice import (
                            add_creative_dj_commentary_to_video,
                            DJContext,
                            AZURE_OPENAI_AVAILABLE
                        )
                        
                        print(f"[DJ] Azure OpenAI available: {AZURE_OPENAI_AVAILABLE}")
                        logger.info(f"Azure OpenAI available: {AZURE_OPENAI_AVAILABLE}")
                        
                        # Build DJContext from dict - support both old and new formats
                        # New format from auto_playlist uses 'notes' and 'original_prompt'
                        mood_val = dj_context.get("mood", "energetic, celebratory, festive")
                        if isinstance(mood_val, list):
                            mood_val = ", ".join(mood_val)
                        
                        context_obj = DJContext(
                            theme=dj_context.get("theme", "New Year 2025 Party - Welcoming 2026!"),
                            mood=mood_val,
                            audience=dj_context.get("audience", "party guests ready to dance"),
                            special_notes=dj_context.get("special_notes") or dj_context.get("notes", ""),
                            custom_shoutouts=dj_context.get("custom_shoutouts", []),
                            original_prompt=dj_context.get("original_prompt", "")
                        )
                        
                        print(f"[DJ] Theme: {context_obj.theme}")
                        print(f"[DJ] Mood: {context_obj.mood}")
                        logger.info(f"DJ Theme: {context_obj.theme}")
                        
                        success, dj_timeline = add_creative_dj_commentary_to_video(
                            output_path,
                            segment_info,
                            dj_output,
                            context_obj,
                            dj_voice_mapped,
                            dj_frequency,
                            dj_progress_callback  # Pass progress callback
                        )
                        
                    except ImportError as ie:
                        print(f"[DJ] Azure DJ voice import failed: {ie}")
                        logger.warning(f"Azure DJ voice import failed: {ie}")
                    except Exception as e:
                        print(f"[DJ] Azure DJ voice failed: {e}")
                        logger.warning(f"Azure DJ voice failed: {e}")
                
                # Fallback to original DJ voice if Azure failed or no context
                if not success:
                    print("[DJ] Falling back to original DJ voice...")
                    logger.info("Falling back to original DJ voice")
                    from services.dj_voice import add_dj_commentary_to_video
                    success, dj_timeline = add_dj_commentary_to_video(
                        output_path, segment_info, dj_output, dj_voice_mapped, dj_frequency
                    )
                
                print(f"[DJ] Result: success={success}")
                print(f"[DJ] Output exists: {dj_output.exists()}")
                logger.info(f"DJ voice result: success={success}")
                logger.info(f"DJ output exists: {dj_output.exists()}")
                
                if success and dj_output.exists():
                    dj_size = dj_output.stat().st_size
                    print(f"[DJ] Output size: {dj_size} bytes")
                    logger.info(f"DJ output size: {dj_size} bytes")
                    shutil.move(str(dj_output), str(output_path))
                    print("[DJ] SUCCESS - File replaced with DJ version")
                    logger.info("DJ voice added successfully - file replaced")
                    logger.info(f"DJ Timeline: {dj_timeline}")
                else:
                    print(f"[DJ] FAILED: success={success}, exists={dj_output.exists() if success else 'N/A'}")
                    logger.warning(f"DJ voice mixing failed: success={success}")
            except Exception as e:
                print(f"[DJ] EXCEPTION: {e}")
                logger.error(f"DJ voice exception: {e}")
                import traceback
                traceback.print_exc()
            
            print("="*50)
            print("[DJ] PROCESSING COMPLETE")
            print("="*50)
            logger.info("="*50)
            logger.info("DJ VOICE PROCESSING COMPLETE")
            logger.info("="*50)
        
        # Get final file info
        update_progress("complete", 100, "Export complete!", len(segments))
        
        duration = get_video_duration(output_path)
        file_size = output_path.stat().st_size if output_path.exists() else 0
        
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        return ExportResult(
            success=True,
            output_path=str(output_path),
            duration_seconds=duration,
            file_size_bytes=file_size
        )
        
    except Exception as e:
        logger.error(f"Export failed: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return ExportResult(success=False, error=str(e))
