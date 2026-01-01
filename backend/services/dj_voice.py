"""
AI DJ Voice Service - Generates contextual DJ commentary and voice clips.
Uses edge-tts for high-quality text-to-speech.
"""

import asyncio
import random
import os
import logging
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
import subprocess
import tempfile
import threading
import concurrent.futures

logger = logging.getLogger(__name__)

def log(msg: str):
    """Print with immediate flush for logging."""
    print(msg, flush=True)
    sys.stdout.flush()

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
    logger.info("edge-tts is available")
except ImportError:
    EDGE_TTS_AVAILABLE = False
    logger.warning("edge-tts is NOT available")


def run_async_safely(coro):
    """
    Run an async coroutine safely from sync context, 
    even when already in an async event loop (like uvicorn).
    """
    try:
        # Check if there's already a running event loop
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, safe to use asyncio.run()
        return asyncio.run(coro)
    
    # Already in an async context - run in a separate thread
    with concurrent.futures.ThreadPoolExecutor() as pool:
        future = pool.submit(asyncio.run, coro)
        return future.result()


# DJ Voice options (edge-tts voices)
DJ_VOICES = {
    "energetic_male": "en-US-GuyNeural",
    "energetic_female": "en-US-AriaNeural", 
    "deep_male": "en-US-ChristopherNeural",
    "party_female": "en-US-JennyNeural",
    "hype_male": "en-GB-RyanNeural",
}

# Language-specific greetings and shoutouts
LANGUAGE_SHOUTOUTS = {
    "english": ["Let's go!", "Here we go!", "This one's fire!"],
    "hindi": ["Arey waah!", "Bollywood vibes!", "Desi beat dropping!"],
    "malayalam": ["Kerala representing!", "Mollywood in the house!"],
    "tamil": ["Kollywood energy!", "Chennai style!", "Tamil beats!"],
    "turkish": ["Istanbul calling!", "Turkish delight coming up!"],
    "uzbek": ["Central Asia vibes!", "Uzbekistan in the mix!"],
    "arabic": ["Yalla habibi!", "Middle East heat!", "Arabic fire!"],
}

# Contextual DJ phrases
DJ_PHRASES = {
    "intro": [
        "What's up party people! Your AI DJ is in the mix!",
        "Let's get this party started! I'm your DJ for tonight!",
        "Welcome to the ultimate music experience! Let's gooo!",
        "Hey everyone! Ready to vibe? Let's do this!",
        "The energy is about to go through the roof! Here we go!",
    ],
    "hype": [
        "Let's turn it up!",
        "Make some noise!",
        "Hands up if you feel this!",
        "The vibes are immaculate!",
        "We're just getting started!",
        "Energy check! Are you with me?",
        "This is your moment!",
        "Feel the beat!",
    ],
    "transition_smooth": [
        "Smooth transition coming up...",
        "Let's keep the flow going...",
        "Blending into the next one...",
        "Keeping it smooth...",
    ],
    "transition_energy": [
        "Now let's take it up a notch!",
        "Time to raise the energy!",
        "Here comes the heat!",
        "Get ready for this one!",
        "Big tune incoming!",
    ],
    "transition_chill": [
        "Let's cool it down for a moment...",
        "Taking it easy for this one...",
        "Vibe with me on this...",
        "Smooth vibes only...",
    ],
    "language_switch": [
        "Now let's travel to {country}!",
        "Taking you to {country} with this one!",
        "Switching it up! {language} vibes incoming!",
        "{language} music hitting different!",
        "Around the world we go! Next stop: {country}!",
    ],
    "bpm_comment": [
        "Keeping the tempo at {bpm} BPM!",
        "{bpm} beats per minute of pure energy!",
        "Locking in at {bpm} BPM!",
    ],
    "peak_energy": [
        "This is the moment! Peak energy!",
        "We're at the top now! Feel it!",
        "Maximum vibes achieved!",
        "This is what we came for!",
    ],
    "outro": [
        "That's a wrap! Thanks for vibing with me!",
        "What a journey! Until next time!",
        "You've been amazing! Peace out!",
        "That's all for now! Stay groovy!",
    ],
}

LANGUAGE_TO_COUNTRY = {
    "english": "the world",
    "hindi": "India",
    "malayalam": "Kerala",
    "tamil": "Tamil Nadu",
    "turkish": "Turkey",
    "uzbek": "Uzbekistan",
    "arabic": "the Middle East",
}


@dataclass
class DJComment:
    """A DJ comment to be inserted in the mix."""
    text: str
    comment_type: str  # intro, hype, transition, language_switch, outro
    position: str  # before, after, between
    segment_index: int
    audio_path: Optional[str] = None


@dataclass 
class DJSettings:
    """Settings for DJ commentary."""
    enabled: bool = True
    voice: str = "energetic_male"
    frequency: str = "moderate"  # minimal, moderate, frequent
    include_intro: bool = True
    include_outro: bool = True
    include_language_shoutouts: bool = True
    include_energy_comments: bool = True
    volume: float = 0.85  # 0-1


def get_comment_frequency(setting: str) -> float:
    """Get probability of inserting a comment based on frequency setting."""
    return {"minimal": 0.2, "moderate": 0.4, "frequent": 0.7}.get(setting, 0.4)


def generate_language_switch_comment(from_lang: str, to_lang: str) -> str:
    """Generate a comment for switching between languages."""
    template = random.choice(DJ_PHRASES["language_switch"])
    country = LANGUAGE_TO_COUNTRY.get(to_lang, to_lang.title())
    return template.format(language=to_lang.title(), country=country)


def get_energy_comment(prev_energy: float, curr_energy: float) -> str:
    """Get appropriate transition comment based on energy change."""
    energy_diff = curr_energy - prev_energy
    
    if energy_diff > 0.15:
        return random.choice(DJ_PHRASES["transition_energy"])
    elif energy_diff < -0.15:
        return random.choice(DJ_PHRASES["transition_chill"])
    else:
        return random.choice(DJ_PHRASES["transition_smooth"])


def generate_dj_script(
    segments: List[Dict],
    settings: DJSettings
) -> List[DJComment]:
    """
    Generate a complete DJ commentary script for a playlist.
    
    Args:
        segments: List of segment info dicts with keys:
            - song_title, language, bpm, energy_score, position
        settings: DJ commentary settings
    
    Returns:
        List of DJComment objects to insert during export
    """
    if not settings.enabled or not segments:
        return []
    
    comments = []
    frequency = get_comment_frequency(settings.frequency)
    
    # Intro comment
    if settings.include_intro:
        comments.append(DJComment(
            text=random.choice(DJ_PHRASES["intro"]),
            comment_type="intro",
            position="before",
            segment_index=0
        ))
    
    prev_language = None
    prev_energy = 0.5
    peak_index = max(range(len(segments)), key=lambda i: segments[i].get("energy_score", 0.5))
    
    for i, seg in enumerate(segments):
        curr_language = seg.get("language", "english")
        curr_energy = seg.get("energy_score", 0.5)
        curr_bpm = seg.get("bpm")
        
        # Skip first segment (already has intro)
        if i == 0:
            prev_language = curr_language
            prev_energy = curr_energy
            continue
        
        # Decide whether to add a comment (based on frequency)
        if random.random() > frequency:
            prev_language = curr_language
            prev_energy = curr_energy
            continue
        
        comment_text = None
        comment_type = "transition"
        
        # Language switch comment
        if settings.include_language_shoutouts and curr_language != prev_language:
            comment_text = generate_language_switch_comment(prev_language, curr_language)
            # Add language-specific shoutout
            if curr_language in LANGUAGE_SHOUTOUTS:
                shoutout = random.choice(LANGUAGE_SHOUTOUTS[curr_language])
                comment_text += f" {shoutout}"
            comment_type = "language_switch"
        
        # Peak energy comment
        elif i == peak_index and settings.include_energy_comments:
            comment_text = random.choice(DJ_PHRASES["peak_energy"])
            comment_type = "peak"
        
        # Energy-based transition comment
        elif settings.include_energy_comments:
            comment_text = get_energy_comment(prev_energy, curr_energy)
        
        # Random hype comment
        elif random.random() < 0.3:
            comment_text = random.choice(DJ_PHRASES["hype"])
            comment_type = "hype"
        
        if comment_text:
            # Occasionally add BPM comment
            if curr_bpm and random.random() < 0.2:
                bpm_comment = random.choice(DJ_PHRASES["bpm_comment"]).format(bpm=int(curr_bpm))
                comment_text += f" {bpm_comment}"
            
            comments.append(DJComment(
                text=comment_text,
                comment_type=comment_type,
                position="between",
                segment_index=i
            ))
        
        prev_language = curr_language
        prev_energy = curr_energy
    
    # Outro comment
    if settings.include_outro and len(segments) > 1:
        comments.append(DJComment(
            text=random.choice(DJ_PHRASES["outro"]),
            comment_type="outro",
            position="after",
            segment_index=len(segments) - 1
        ))
    
    return comments


async def generate_voice_clip_async(
    text: str,
    output_path: Path,
    voice: str = "energetic_male"
) -> bool:
    """Generate a voice clip using edge-tts."""
    if not EDGE_TTS_AVAILABLE:
        print("edge-tts not available, skipping voice generation")
        return False
    
    voice_id = DJ_VOICES.get(voice, DJ_VOICES["energetic_male"])
    
    try:
        communicate = edge_tts.Communicate(text, voice_id)
        await communicate.save(str(output_path))
        return True
    except Exception as e:
        print(f"TTS error: {e}")
        return False


def generate_voice_clip(
    text: str,
    output_path: Path,
    voice: str = "energetic_male"
) -> bool:
    """Synchronous wrapper for voice generation."""
    return run_async_safely(generate_voice_clip_async(text, output_path, voice))


def add_reverb_effect(input_path: Path, output_path: Path) -> bool:
    """Add slight reverb and EQ to make DJ voice sound professional."""
    try:
        # Add slight reverb, bass boost, and normalize
        cmd = [
            'ffmpeg', '-y',
            '-i', str(input_path),
            '-af', 'aecho=0.8:0.7:40:0.3,equalizer=f=100:width_type=o:width=2:g=3,loudnorm',
            '-ar', '44100',
            str(output_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"Audio effect error: {e}")
        return False


def create_dj_audio_with_beat(
    voice_path: Path,
    output_path: Path,
    duration: float = None
) -> bool:
    """
    Create DJ audio clip with slight background beat/swoosh effect.
    """
    try:
        # Add a subtle swoosh/riser effect before the voice
        # Using FFmpeg's sine wave generator for a quick riser
        cmd = [
            'ffmpeg', '-y',
            '-i', str(voice_path),
            '-af', (
                'afade=t=in:st=0:d=0.1,'  # Fade in
                'afade=t=out:st=-0.1:d=0.1,'  # Fade out at end
                'volume=1.2'  # Slight volume boost
            ),
            str(output_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"DJ audio creation error: {e}")
        return False


async def generate_all_dj_clips(
    comments: List[DJComment],
    output_dir: Path,
    voice: str = "energetic_male"
) -> List[DJComment]:
    """Generate all DJ voice clips for a list of comments."""
    if not EDGE_TTS_AVAILABLE:
        print("edge-tts not installed. Install with: pip install edge-tts")
        return comments
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for i, comment in enumerate(comments):
        raw_path = output_dir / f"dj_raw_{i}.mp3"
        final_path = output_dir / f"dj_clip_{i}.mp3"
        
        # Generate voice
        success = await generate_voice_clip_async(comment.text, raw_path, voice)
        
        if success:
            # Add effects
            if add_reverb_effect(raw_path, final_path):
                comment.audio_path = str(final_path)
            else:
                comment.audio_path = str(raw_path)
            
            # Clean up raw file if we have processed version
            if final_path.exists() and raw_path.exists():
                raw_path.unlink()
    
    return comments


def generate_all_dj_clips_sync(
    comments: List[DJComment],
    output_dir: Path,
    voice: str = "energetic_male"
) -> List[DJComment]:
    """Synchronous wrapper for generating all DJ clips."""
    return run_async_safely(generate_all_dj_clips(comments, output_dir, voice))


def get_dj_clip_duration(audio_path: str) -> float:
    """Get duration of a DJ audio clip."""
    try:
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return float(result.stdout.strip())
    except:
        pass
    return 2.0  # Default estimate


def get_stream_durations(video_path) -> tuple:
    """Get both video and audio stream durations separately."""
    cmd = [
        'ffprobe', '-v', 'error',
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
        print(f"[DJ_VOICE] Could not get stream durations: {e}")
    return 0, 0


def mix_dj_audio_with_video(
    video_path: Path,
    dj_audio_path: Path,
    output_path: Path,
    dj_start_time: float = 0,
    dj_volume: float = 1.0,
    duck_music: bool = True
) -> bool:
    """
    Mix DJ audio clip with video, optionally ducking the music.
    
    Args:
        video_path: Input video
        dj_audio_path: DJ voice clip
        output_path: Output video
        dj_start_time: When to start DJ audio (seconds from video start)
        dj_volume: DJ voice volume (0-1)
        duck_music: Whether to lower music volume during DJ speech
    """
    try:
        dj_duration = get_dj_clip_duration(str(dj_audio_path))
        
        # Clamp start time to valid range
        video_duration = get_dj_clip_duration(str(video_path))
        if dj_start_time < 0:
            dj_start_time = 0
        if dj_start_time >= video_duration - 1:
            dj_start_time = max(0, video_duration - dj_duration - 1)
        
        delay_ms = int(dj_start_time * 1000)
        end_time = dj_start_time + dj_duration
        
        if duck_music:
            # Duck the music volume during DJ speech, boost DJ voice significantly
            # Using sidechaincompress alternative: manually lower music, overlay DJ
            filter_complex = (
                f"[1:a]adelay={delay_ms}|{delay_ms},volume={dj_volume * 2.0}[dj];"
                f"[0:a]volume='if(between(t,{dj_start_time},{end_time}),0.25,1)':eval=frame[music];"
                f"[music][dj]amix=inputs=2:duration=longest:dropout_transition=0:weights='1 2'[aout]"
            )
        else:
            filter_complex = (
                f"[1:a]adelay={delay_ms}|{delay_ms},volume={dj_volume * 1.5}[dj];"
                f"[0:a][dj]amix=inputs=2:duration=longest:dropout_transition=0:weights='1 1.5'[aout]"
            )
        
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-i', str(dj_audio_path),
            '-filter_complex', filter_complex,
            '-map', '0:v',
            '-map', '[aout]',
            '-c:v', 'copy',
            '-c:a', 'aac', '-b:a', '192k',
            '-shortest',
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"FFmpeg error: {result.stderr[:500]}")
        return result.returncode == 0
    except Exception as e:
        print(f"DJ audio mix error: {e}")
        return False

def add_dj_commentary_to_video(
    video_path: Path,
    segments: list,
    output_path: Path,
    voice: str = "energetic_male",
    frequency: str = "moderate"
) -> Tuple[bool, list]:
    """
    Complete DJ voice integration - generates commentary and mixes with video.
    Uses a SEPARATE audio track approach for reliability.
    Handles A/V sync to ensure audio doesn't extend past video.
    
    Returns:
        Tuple of (success: bool, timeline: list of dicts with timing info)
    """
    timeline = []
    
    print("="*60)
    print("[DJ_VOICE] ADD_DJ_COMMENTARY_TO_VIDEO STARTED")
    print(f"[DJ_VOICE] Input video: {video_path}")
    print(f"[DJ_VOICE] Output path: {output_path}")
    print(f"[DJ_VOICE] Voice: {voice}, Frequency: {frequency}")
    print(f"[DJ_VOICE] Segments: {len(segments)}")
    print(f"[DJ_VOICE] EDGE_TTS_AVAILABLE: {EDGE_TTS_AVAILABLE}")
    print("="*60)
    
    logger.info("="*60)
    logger.info("ADD_DJ_COMMENTARY_TO_VIDEO STARTED")
    logger.info(f"Input video: {video_path}")
    logger.info(f"Output path: {output_path}")
    logger.info(f"Voice: {voice}, Frequency: {frequency}")
    logger.info(f"Segments: {len(segments)}")
    logger.info(f"EDGE_TTS_AVAILABLE: {EDGE_TTS_AVAILABLE}")
    logger.info("="*60)
    
    if not EDGE_TTS_AVAILABLE:
        print("[DJ_VOICE] edge-tts not available, skipping DJ voice")
        logger.error("edge-tts not available, skipping DJ voice")
        return False, timeline
    
    temp_dir = Path(tempfile.mkdtemp())
    logger.info(f"Temp dir: {temp_dir}")
    
    try:
        # Get BOTH video and audio stream durations
        video_dur, audio_dur = get_stream_durations(video_path)
        print(f"[DJ_VOICE] Input streams: video={video_dur:.2f}s, audio={audio_dur:.2f}s")
        logger.info(f"Input streams: video={video_dur:.2f}s, audio={audio_dur:.2f}s")
        
        # Use the SHORTER of the two to avoid audio extending past video
        video_duration = min(video_dur, audio_dur) if video_dur > 0 and audio_dur > 0 else max(video_dur, audio_dur)
        
        if video_duration <= 0:
            # Fallback to format duration
            video_duration = get_dj_clip_duration(str(video_path))
        
        print(f"[DJ_VOICE] Using duration: {video_duration:.2f}s for DJ timing")
        logger.info(f"Using duration: {video_duration:.2f}s for DJ timing")
        
        if video_duration <= 0:
            logger.error(f"Invalid video duration: {video_duration}")
            return False, timeline
        
        num_segments = len(segments)
        
        # Create exactly 3 DJ comments: intro, middle, outro
        comments_to_make = []
        
        # 1. INTRO - plays at 2 seconds (during intro card fade-in)
        intro_text = "What's up party people! Your AI DJ is in the mix! Let's get this party started!"
        comments_to_make.append({
            "text": intro_text,
            "type": "intro",
            "start_time": 2.0,
        })
        
        # 2. MIDDLE - plays at the midpoint of the video
        midpoint = video_duration / 2
        if num_segments >= 2:
            langs = [s.get("language", "english") for s in segments]
            mid_lang = langs[len(langs)//2] if len(langs) > 1 else "english"
            mid_text = f"Now we're switching it up! {mid_lang.title()} vibes coming in hot! Keep that energy going!"
        else:
            mid_text = "We're just getting warmed up! The vibes are immaculate! Keep that energy going!"
        comments_to_make.append({
            "text": mid_text,
            "type": "middle",
            "start_time": midpoint,
        })
        
        # 3. OUTRO - plays 8 seconds before the end
        outro_start = max(video_duration - 8.0, video_duration * 0.85)
        outro_text = "That's a wrap! Thanks for vibing with me! Until next time, stay groovy!"
        comments_to_make.append({
            "text": outro_text,
            "type": "outro", 
            "start_time": outro_start,
        })
        
        print(f"[DJ_VOICE] Creating {len(comments_to_make)} DJ comments for {video_duration:.1f}s video")
        logger.info(f"Creating {len(comments_to_make)} DJ comments for {video_duration:.1f}s video")
        for c in comments_to_make:
            print(f"[DJ_VOICE]   - [{c['type']}] at {c['start_time']:.1f}s")
            logger.info(f"  - [{c['type']}] at {c['start_time']:.1f}s: {c['text'][:40]}...")
        
        # Generate voice clips
        dj_clips = []
        for i, comment in enumerate(comments_to_make):
            clip_path = temp_dir / f"dj_{i}.mp3"
            
            print(f"[DJ_VOICE] Generating voice clip {i+1}/{len(comments_to_make)}...")
            logger.info(f"Generating voice clip {i+1}/{len(comments_to_make)}...")
            success = generate_voice_clip(comment["text"], clip_path, voice)
            print(f"[DJ_VOICE]   Success: {success}, Exists: {clip_path.exists()}")
            logger.info(f"  Voice generation success: {success}")
            logger.info(f"  Clip exists: {clip_path.exists()}")
            
            if success and clip_path.exists():
                clip_size = clip_path.stat().st_size
                clip_duration = get_dj_clip_duration(str(clip_path))
                print(f"[DJ_VOICE]   Size: {clip_size} bytes, Duration: {clip_duration:.1f}s")
                logger.info(f"  Clip size: {clip_size} bytes, duration: {clip_duration:.1f}s")
                
                dj_clips.append({
                    "path": str(clip_path),
                    "start_time": comment["start_time"],
                    "duration": clip_duration,
                    "type": comment["type"],
                    "text": comment["text"],
                })
                timeline.append({
                    "type": comment["type"],
                    "start_time": comment["start_time"],
                    "end_time": comment["start_time"] + clip_duration,
                    "text": comment["text"][:50] + "..."
                })
            else:
                print(f"[DJ_VOICE]   FAILED to generate clip {i+1}")
                logger.error(f"  Failed to generate clip {i+1}")
        
        print(f"[DJ_VOICE] Generated {len(dj_clips)} DJ clips successfully")
        logger.info(f"Generated {len(dj_clips)} DJ clips successfully")
        
        if not dj_clips:
            print("[DJ_VOICE] No DJ clips generated! Returning False")
            logger.error("No DJ clips generated!")
            return False, timeline
        
        # First, fix the input video's A/V sync if needed
        sync_diff = abs(video_dur - audio_dur)
        input_video = video_path
        
        if sync_diff > 0.5:
            print(f"[DJ_VOICE] Input has A/V sync issue ({sync_diff:.2f}s), fixing first...")
            logger.info(f"Input has A/V sync issue ({sync_diff:.2f}s), fixing first...")
            
            fixed_input = temp_dir / "fixed_input.mp4"
            min_dur = min(video_dur, audio_dur)
            
            fix_cmd = [
                'ffmpeg', '-y',
                '-i', str(video_path),
                '-t', str(min_dur),
                '-c:v', 'libx264', '-preset', 'fast',
                '-c:a', 'aac', '-ar', '44100', '-ac', '2',
                '-vsync', 'cfr', '-r', '30',
                str(fixed_input)
            ]
            
            fix_result = subprocess.run(fix_cmd, capture_output=True, text=True)
            if fix_result.returncode == 0 and fixed_input.exists():
                input_video = fixed_input
                print(f"[DJ_VOICE] Fixed input A/V sync, using {fixed_input}")
                logger.info(f"Fixed input A/V sync, using {fixed_input}")
            else:
                print(f"[DJ_VOICE] Could not fix input sync, proceeding anyway")
                logger.warning("Could not fix input sync, proceeding anyway")
        
        # Build FFmpeg command with all clips at once
        input_args = ['-i', str(input_video)]
        filter_parts = []
        
        # Build duck ranges
        duck_expr_parts = []
        for clip in dj_clips:
            start = clip["start_time"]
            end = start + clip["duration"]
            duck_expr_parts.append(f"between(t,{start},{end})")
        
        # Music: duck to 15% during DJ, otherwise full
        if duck_expr_parts:
            duck_cond = '+'.join(duck_expr_parts)
            filter_parts.append(f"[0:a]volume='if({duck_cond},0.15,1.0)':eval=frame[music]")
        else:
            filter_parts.append("[0:a]anull[music]")
        
        # Add each DJ clip
        mix_labels = ['[music]']
        for i, clip in enumerate(dj_clips):
            input_args.extend(['-i', clip["path"]])
            input_idx = i + 1
            delay_ms = int(clip["start_time"] * 1000)
            
            # Boost DJ voice significantly: 3.0x volume
            filter_parts.append(
                f"[{input_idx}:a]adelay={delay_ms}|{delay_ms},volume=3.0[dj{i}]"
            )
            mix_labels.append(f'[dj{i}]')
        
        # Final mix - music gets weight 1, each DJ gets weight 3
        # IMPORTANT: Use duration=first to match the first input (video) duration
        num_inputs = len(mix_labels)
        weights = '1 ' + ' '.join(['3'] * (num_inputs - 1))
        filter_parts.append(
            f"{''.join(mix_labels)}amix=inputs={num_inputs}:duration=first:dropout_transition=0:normalize=0:weights='{weights}'[aout]"
        )
        
        filter_complex = ';'.join(filter_parts)
        
        # Re-encode video to ensure A/V sync in output (don't use -c:v copy)
        cmd = [
            'ffmpeg', '-y',
            *input_args,
            '-filter_complex', filter_complex,
            '-map', '0:v',
            '-map', '[aout]',
            '-c:v', 'libx264', '-preset', 'fast',  # Re-encode video for sync
            '-c:a', 'aac', '-b:a', '192k',
            '-vsync', 'cfr', '-r', '30',
            '-shortest',  # Stop when shortest stream ends
            str(output_path)
        ]
        
        print(f"[DJ_VOICE] Running FFmpeg with {len(input_args)//2} inputs...")
        logger.info(f"FFmpeg command inputs: {len(input_args)//2} files")
        logger.info(f"Filter complex length: {len(filter_complex)} chars")
        logger.info("Running FFmpeg...")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"[DJ_VOICE] FFmpeg FAILED with code {result.returncode}")
            print(f"[DJ_VOICE] stderr: {result.stderr[:500]}")
            logger.error(f"FFmpeg failed with code {result.returncode}")
            logger.error(f"FFmpeg stderr: {result.stderr[:1000]}")
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False, timeline
        
        # Verify output A/V sync
        out_v, out_a = get_stream_durations(output_path)
        out_sync_diff = abs(out_v - out_a)
        
        print(f"[DJ_VOICE] FFmpeg SUCCESS!")
        print(f"[DJ_VOICE] Output: video={out_v:.2f}s, audio={out_a:.2f}s, diff={out_sync_diff:.2f}s")
        print(f"[DJ_VOICE] Output exists: {output_path.exists()}")
        if output_path.exists():
            print(f"[DJ_VOICE] Output size: {output_path.stat().st_size} bytes")
        
        logger.info("FFmpeg completed successfully!")
        logger.info(f"Output: video={out_v:.1f}s, audio={out_a:.1f}s, diff={out_sync_diff:.2f}s")
        logger.info(f"Output file exists: {output_path.exists()}")
        if output_path.exists():
            logger.info(f"Output file size: {output_path.stat().st_size} bytes")
        
        if out_sync_diff > 0.5:
            print(f"[DJ_VOICE] WARNING: Output has A/V sync issue!")
            logger.warning(f"Output has A/V sync issue: {out_sync_diff:.2f}s")
        
        print("[DJ_VOICE] === DJ VOICE TIMELINE ===")
        logger.info("")
        logger.info("=== DJ VOICE TIMELINE ===")
        for t in timeline:
            print(f"[DJ_VOICE]   {t['type'].upper():8} @ {t['start_time']:.1f}s - {t['end_time']:.1f}s")
            logger.info(f"  {t['type'].upper():8} @ {t['start_time']:.1f}s - {t['end_time']:.1f}s")
        print("[DJ_VOICE] =========================")
        logger.info("=========================")
        
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        return True, timeline
        
    except Exception as e:
        print(f"[DJ_VOICE] EXCEPTION: {e}")
        logger.error(f"DJ commentary error: {e}")
        import traceback
        traceback.print_exc()
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False, timeline
