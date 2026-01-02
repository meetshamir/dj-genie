"""
Auto Playlist Generator

Takes a PlaylistPlan from the recommender, downloads songs, analyzes them,
and creates an optimized mix with AI DJ commentary.
"""

import os
import sys
import json
import asyncio
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.song_recommender import PlaylistPlan, SongRecommendation, create_playlist_from_prompt

# For audio analysis
try:
    import librosa
    import numpy as np
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

# For downloading
try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False


@dataclass
class DownloadedSong:
    """A downloaded song with analysis"""
    original: SongRecommendation
    video_path: str
    audio_path: Optional[str] = None
    duration: float = 0.0
    bpm: float = 120.0
    energy: float = 0.7
    best_segment_start: float = 0.0
    best_segment_end: float = 30.0
    # YouTube "Most Replayed" heatmap data - list of {start_time, end_time, value}
    youtube_heatmap: Optional[List[Dict[str, float]]] = None


@dataclass
class AutoPlaylistResult:
    """Result of auto playlist generation"""
    success: bool
    playlist_id: Optional[str] = None
    export_path: Optional[str] = None
    songs_downloaded: int = 0
    total_duration: float = 0.0
    theme: str = ""
    error: Optional[str] = None


class AutoPlaylistGenerator:
    """Generates complete DJ playlists from natural language prompts"""
    
    def __init__(
        self,
        downloads_dir: str = "downloads",
        exports_dir: str = "exports",
        progress_callback: Optional[Callable[[str, float], None]] = None
    ):
        self.downloads_dir = Path(downloads_dir)
        self.exports_dir = Path(exports_dir)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.progress_callback = progress_callback or (lambda msg, pct: print(f"[{pct:.0%}] {msg}"))
    
    def log(self, message: str, progress: float = 0.0):
        """Log progress"""
        print(f"[AUTO_PLAYLIST] {message}")
        if self.progress_callback:
            self.progress_callback(message, progress)
    
    def download_song(self, song: SongRecommendation, index: int, total: int) -> Optional[DownloadedSong]:
        """Download a single song from YouTube"""
        if not song.youtube_url:
            self.log(f"  [FAIL] No YouTube URL for {song.title}")
            return None
        
        if not YT_DLP_AVAILABLE:
            self.log("  [FAIL] yt-dlp not available")
            return None
        
        # Create safe filename
        safe_name = f"{song.artist}_{song.title}".replace(" ", "_")
        safe_name = "".join(c for c in safe_name if c.isalnum() or c in "_-")[:50]
        output_template = str(self.downloads_dir / f"{safe_name}_%(id)s.%(ext)s")
        
        ydl_opts_base = {
            'format': 'best[height<=720]/bestvideo[height<=720]+bestaudio',  # 720p, prefer single file format
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'extract_audio': False,
            'merge_output_format': 'mp4',  # Ensure mp4 output
            'postprocessor_args': {'ffmpeg': ['-c', 'copy']},  # Fast copy without re-encode
        }
        
        # Check if cookies file exists - try multiple locations
        cookies_candidates = [
            self.downloads_dir.parent / "youtube_cookies.txt",  # cache/youtube_cookies.txt
            self.downloads_dir.parent.parent / "cache" / "youtube_cookies.txt",  # project/cache/youtube_cookies.txt
            Path.home() / "video-dj-playlist" / "cache" / "youtube_cookies.txt",  # home dir
        ]
        cookies_file = None
        for candidate in cookies_candidates:
            if candidate.exists():
                cookies_file = candidate
                break
        
        if cookies_file:
            ydl_opts_base['cookiefile'] = str(cookies_file)
            self.log(f"    [INFO] Using cookies from {cookies_file}")
        
        try:
            self.log(f"  [{index}/{total}] Downloading: {song.artist} - {song.title}...")
            
            # Try different configurations to bypass bot detection
            configs = [
                ydl_opts_base,  # Try base config first (with cookies file if exists)
                {**ydl_opts_base, 'extractor_args': {'youtube': {'player_client': ['tv_embedded', 'web']}}},  # Try tv_embedded
                {**ydl_opts_base, 'extractor_args': {'youtube': {'player_client': ['web_music']}}},  # Try web_music
            ]
            
            last_error = None
            for opts in configs:
                try:
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(song.youtube_url, download=True)
                        
                        # Find the downloaded file
                        video_path = None
                        for ext in ['mp4', 'webm', 'mkv']:
                            potential = self.downloads_dir / f"{safe_name}_{info['id']}.{ext}"
                            if potential.exists():
                                video_path = str(potential)
                                break
                        
                        if not video_path:
                            # Try to find by pattern
                            for f in self.downloads_dir.glob(f"{safe_name}*"):
                                if f.suffix in ['.mp4', '.webm', '.mkv']:
                                    video_path = str(f)
                                    break
                        
                        if not video_path:
                            self.log(f"    [FAIL] Downloaded file not found")
                            return None
                        
                        # Extract YouTube "Most Replayed" heatmap data if available
                        # This shows which parts viewers replay most - great for finding catchy segments!
                        heatmap_data = info.get('heatmap')
                        if heatmap_data:
                            self.log(f"    [HEATMAP] Found YouTube 'Most Replayed' data ({len(heatmap_data)} points)")
                        
                        downloaded = DownloadedSong(
                            original=song,
                            video_path=video_path,
                            duration=info.get('duration', 180),
                            youtube_heatmap=heatmap_data
                        )
                        
                        self.log(f"    [OK] Downloaded ({downloaded.duration:.0f}s)")
                        return downloaded
                except Exception as e:
                    last_error = e
                    self.log(f"    [RETRY] Download attempt failed, trying alternative...")
                    continue
            
            # All attempts failed
            if last_error:
                raise last_error
                
        except Exception as e:
            self.log(f"    [FAIL] Download failed: {e}")
            return None
    
    def _calculate_segment_duration(self, energy: float, song_duration: float) -> float:
        """
        Calculate segment duration based on energy level.
        High energy songs get shorter segments (45s) - keep it punchy!
        Lower energy songs can have longer segments (up to 90s) to build atmosphere.
        """
        # Base: 45s minimum, 90s maximum
        MIN_DURATION = 45.0
        MAX_DURATION = 90.0
        
        # High energy (>0.8) = 45-55s (short and punchy)
        # Medium energy (0.5-0.8) = 55-70s 
        # Lower energy (<0.5) = 70-90s (more atmospheric)
        if energy >= 0.8:
            target = MIN_DURATION + (1.0 - energy) * 50  # 45-55s
        elif energy >= 0.5:
            target = 55 + (0.8 - energy) * 50  # 55-70s
        else:
            target = 70 + (0.5 - energy) * 40  # 70-90s
        
        # Clamp to bounds and song duration
        target = max(MIN_DURATION, min(MAX_DURATION, target))
        target = min(target, song_duration - 5)  # Leave 5s buffer at end
        
        return target
    
    def _find_best_segment_from_heatmap(
        self, 
        heatmap: List[Dict[str, float]], 
        target_duration: float,
        max_start_time: float = 180.0
    ) -> Optional[tuple]:
        """
        Find the best segment using YouTube's "Most Replayed" heatmap data.
        
        The heatmap contains [{start_time, end_time, value}] where value (0-1) 
        represents replay intensity - higher values mean more viewers replayed that part.
        
        Args:
            heatmap: YouTube heatmap data from yt-dlp
            target_duration: Desired segment length in seconds
            max_start_time: Only consider segments starting before this time (default: first 3 mins)
            
        Returns:
            (best_start, best_end, peak_value) or None if no valid segment found
        """
        if not heatmap:
            return None
        
        # Filter heatmap to first 3 minutes (user requested optimization)
        filtered_heatmap = [
            h for h in heatmap 
            if h.get('start_time', 0) < max_start_time
        ]
        
        if not filtered_heatmap:
            return None
        
        # Find the segment with highest average replay intensity
        best_start = 0
        best_score = 0
        
        # Sort by start_time for sliding window approach
        sorted_heatmap = sorted(filtered_heatmap, key=lambda h: h.get('start_time', 0))
        
        for i, point in enumerate(sorted_heatmap):
            start_time = point.get('start_time', 0)
            
            # Skip if segment would start too late
            if start_time > max_start_time - target_duration:
                break
            
            # Calculate average replay value for this potential segment
            segment_end = start_time + target_duration
            segment_values = []
            
            for h in sorted_heatmap:
                h_start = h.get('start_time', 0)
                h_end = h.get('end_time', h_start + 1)
                h_value = h.get('value', 0)
                
                # Check if this heatmap point overlaps with our segment
                if h_start < segment_end and h_end > start_time:
                    segment_values.append(h_value)
            
            if segment_values:
                avg_score = sum(segment_values) / len(segment_values)
                if avg_score > best_score:
                    best_score = avg_score
                    best_start = start_time
        
        if best_score > 0:
            return (best_start, best_start + target_duration, best_score)
        
        return None
    
    def _find_nearest_beat_boundary(self, target_time: float, beat_times: np.ndarray, prefer_direction: str = "before") -> float:
        """
        Find the nearest beat/phrase boundary to ensure we don't cut mid-lyric.
        
        Args:
            target_time: The target time we want to cut at
            beat_times: Array of detected beat times
            prefer_direction: "before" to prefer earlier beat, "after" to prefer later
        
        Returns:
            The nearest beat time to the target
        """
        if len(beat_times) == 0:
            return target_time
        
        # Find beats within a reasonable range (±5 seconds)
        nearby_beats = beat_times[np.abs(beat_times - target_time) <= 5.0]
        
        if len(nearby_beats) == 0:
            # No beats nearby, use original time
            return target_time
        
        if prefer_direction == "before":
            # Prefer beats BEFORE the target (don't cut too early into next phrase)
            before_beats = nearby_beats[nearby_beats <= target_time]
            if len(before_beats) > 0:
                return float(before_beats[-1])  # Last beat before target
        else:  # prefer "after"
            # Prefer beats AFTER the target (give the current phrase time to finish)
            after_beats = nearby_beats[nearby_beats >= target_time]
            if len(after_beats) > 0:
                return float(after_beats[0])  # First beat after target
        
        # Fallback: just use the closest beat
        closest_idx = np.argmin(np.abs(nearby_beats - target_time))
        return float(nearby_beats[closest_idx])
    
    def _find_phrase_boundary(self, y: np.ndarray, sr: int, target_time: float, search_range: float = 3.0) -> float:
        """
        Find a natural phrase boundary near the target time.
        
        Uses onset detection and spectral flux to find moments of low activity
        (silences or transitions between phrases) where cuts sound natural.
        
        Args:
            y: Audio signal
            sr: Sample rate
            target_time: Where we want to cut
            search_range: How many seconds to search around target
        
        Returns:
            Best phrase boundary time near target
        """
        # Convert time range to samples
        start_sample = max(0, int((target_time - search_range) * sr))
        end_sample = min(len(y), int((target_time + search_range) * sr))
        
        if end_sample <= start_sample:
            return target_time
        
        # Extract the search region
        region = y[start_sample:end_sample]
        
        # Calculate short-time energy (RMS in small windows)
        hop_length = 512
        frame_length = 2048
        
        try:
            # Get RMS energy
            rms = librosa.feature.rms(y=region, frame_length=frame_length, hop_length=hop_length)[0]
            
            # Find local minima in energy (potential phrase boundaries)
            # These are moments where the music gets quieter
            from scipy.signal import find_peaks
            
            # Invert RMS to find minima as peaks
            inv_rms = 1.0 - (rms / (rms.max() + 1e-8))
            
            # Find peaks in inverted RMS (= energy dips)
            peaks, properties = find_peaks(inv_rms, height=0.3, distance=sr // hop_length // 2)  # At least 0.5s apart
            
            if len(peaks) == 0:
                return target_time
            
            # Convert peak frames to times
            peak_times = (peaks * hop_length / sr) + (target_time - search_range)
            
            # Find the peak closest to our target
            closest_idx = np.argmin(np.abs(peak_times - target_time))
            boundary_time = peak_times[closest_idx]
            
            print(f"[AUTO_PLAYLIST]     [PHRASE] Found phrase boundary at {boundary_time:.2f}s (target was {target_time:.2f}s)")
            
            return float(boundary_time)
            
        except Exception as e:
            print(f"[AUTO_PLAYLIST]     [PHRASE] Phrase detection failed: {e}")
            return target_time

    def analyze_song(self, song: DownloadedSong) -> DownloadedSong:
        """
        Analyze a song for BPM, energy, and find best HIGH-ENERGY segment.
        
        Uses a hybrid approach:
        1. YouTube "Most Replayed" heatmap (if available) - shows what viewers replay most
        2. Librosa audio energy analysis - finds loudest/most energetic parts
        3. Beat tracking to ensure segment boundaries align with musical phrases
        4. Combines all signals for best segment selection with natural cuts
        """
        duration = song.duration
        
        # First, try to get segment from YouTube heatmap (what people actually replay)
        heatmap_segment = None
        if song.youtube_heatmap:
            # We'll get seg_duration after estimating energy, but use a default first
            estimated_seg_duration = 60.0  # Initial estimate
            heatmap_segment = self._find_best_segment_from_heatmap(
                song.youtube_heatmap, 
                estimated_seg_duration,
                max_start_time=180.0  # Focus on first 3 minutes
            )
            if heatmap_segment:
                print(f"[AUTO_PLAYLIST]   [HEATMAP] YouTube suggests segment at {heatmap_segment[0]:.1f}s (popularity: {heatmap_segment[2]:.2f})")
        
        if not LIBROSA_AVAILABLE:
            # Use defaults with some variation based on title hash
            song.bpm = 120 + (hash(song.original.title) % 40 - 20)
            song.energy = 0.6 + (hash(song.original.artist) % 40) / 100
            
            # Calculate dynamic segment duration based on energy
            seg_duration = self._calculate_segment_duration(song.energy, duration)
            
            # If we have heatmap data, use it!
            if heatmap_segment:
                song.best_segment_start = heatmap_segment[0]
                song.best_segment_end = heatmap_segment[0] + seg_duration
            elif duration > 180:
                # Long songs (>3 min): start at 30-35% (after verse, into first chorus)
                song.best_segment_start = duration * 0.32
            elif duration > 120:
                # Medium-long songs (2-3 min): start at 28%
                song.best_segment_start = duration * 0.28
            elif duration > 60:
                # Medium songs (1-2 min): start at 20-25%
                song.best_segment_start = duration * 0.22
            else:
                # Short songs: start from beginning
                song.best_segment_start = 0
            
            # Ensure we don't overflow
            if song.best_segment_start + seg_duration > duration:
                song.best_segment_start = max(0, duration - seg_duration)
            
            song.best_segment_end = song.best_segment_start + seg_duration
            
            return song
        
        try:
            # Extract audio for analysis - analyze first 3 minutes for speed
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                audio_path = tmp.name
            
            # Analyze up to 3 minutes (user-requested optimization)
            analyze_duration = min(180, song.duration)
            cmd = [
                'ffmpeg', '-y', '-i', song.video_path,
                '-vn', '-acodec', 'pcm_s16le', '-ar', '22050', '-ac', '1',
                '-t', str(analyze_duration),
                audio_path
            ]
            subprocess.run(cmd, capture_output=True, timeout=60)
            
            if Path(audio_path).exists():
                # Load and analyze
                y, sr = librosa.load(audio_path, sr=22050, duration=analyze_duration)
                
                # Detect BPM and beat times for phrase-aligned cuts
                tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
                if hasattr(tempo, '__iter__'):
                    tempo = float(tempo[0])
                song.bpm = float(tempo)
                
                # Convert beat frames to times
                beat_times = librosa.frames_to_time(beat_frames, sr=sr)
                print(f"[AUTO_PLAYLIST]   [BEATS] Detected {len(beat_times)} beats, tempo: {song.bpm:.0f} BPM")
                
                # Calculate energy (RMS)
                rms = librosa.feature.rms(y=y)[0]
                song.energy = float(np.mean(rms) * 10)  # Scale to 0-1 range roughly
                song.energy = min(1.0, max(0.0, song.energy))
                
                # Calculate dynamic segment duration based on energy
                seg_duration = self._calculate_segment_duration(song.energy, song.duration)
                
                # Find best segment using HYBRID approach
                hop_length = 512
                window_seconds = seg_duration
                window_size = int(window_seconds * sr / hop_length)
                
                # Calculate audio energy scores for each position
                audio_best_start = 0
                audio_max_energy = 0
                
                if len(rms) > window_size:
                    for i in range(len(rms) - window_size):
                        window_energy = np.sum(rms[i:i+window_size])
                        if window_energy > audio_max_energy:
                            audio_max_energy = window_energy
                            audio_best_start = i * hop_length / sr
                
                # HYBRID DECISION: Combine YouTube heatmap with audio energy
                if heatmap_segment and audio_max_energy > 0:
                    # Both signals available - use weighted combination
                    heatmap_start = heatmap_segment[0]
                    heatmap_score = heatmap_segment[2]
                    
                    # Calculate audio energy at heatmap's suggested position
                    heatmap_frame = int(heatmap_start * sr / hop_length)
                    if heatmap_frame + window_size < len(rms):
                        heatmap_audio_energy = np.sum(rms[heatmap_frame:heatmap_frame + window_size])
                        heatmap_audio_ratio = heatmap_audio_energy / audio_max_energy
                    else:
                        heatmap_audio_ratio = 0.5
                    
                    # If heatmap spot has decent energy (>50% of max), prefer it
                    # because viewer engagement is a strong signal
                    if heatmap_audio_ratio > 0.5 or heatmap_score > 0.7:
                        raw_start = heatmap_start
                        print(f"[AUTO_PLAYLIST]   -> Using YouTube heatmap position (audio energy: {heatmap_audio_ratio:.0%} of peak)")
                    else:
                        raw_start = audio_best_start
                        print(f"[AUTO_PLAYLIST]   -> Using audio energy peak (heatmap spot had low energy)")
                        
                elif heatmap_segment:
                    # Only heatmap available
                    raw_start = heatmap_segment[0]
                    print(f"[AUTO_PLAYLIST]   -> Using YouTube heatmap position")
                else:
                    # Only audio analysis available
                    raw_start = audio_best_start
                
                raw_end = raw_start + seg_duration
                
                # BEAT-ALIGN the segment boundaries to avoid cutting mid-phrase/lyric!
                # Start: snap to nearest beat AFTER the raw start (give intro time)
                aligned_start = self._find_nearest_beat_boundary(raw_start, beat_times, prefer_direction="after")
                
                # Try to find a phrase boundary for the end (a moment of lower energy)
                try:
                    aligned_end = self._find_phrase_boundary(y, sr, raw_end, search_range=3.0)
                except:
                    # Fallback: snap to nearest beat BEFORE the raw end (let current phrase finish)
                    aligned_end = self._find_nearest_beat_boundary(raw_end, beat_times, prefer_direction="before")
                
                # Ensure minimum segment duration after alignment
                if aligned_end - aligned_start < 40:
                    # Alignment made segment too short, use beat alignment only
                    aligned_start = self._find_nearest_beat_boundary(raw_start, beat_times, prefer_direction="after")
                    aligned_end = aligned_start + seg_duration
                    aligned_end = self._find_nearest_beat_boundary(aligned_end, beat_times, prefer_direction="before")
                
                song.best_segment_start = aligned_start
                song.best_segment_end = aligned_end
                
                print(f"[AUTO_PLAYLIST]   [ALIGNED] {raw_start:.1f}s-{raw_end:.1f}s -> {aligned_start:.1f}s-{aligned_end:.1f}s (beat/phrase aligned)")
                
                # Ensure we don't overflow the song duration
                if song.best_segment_end > song.duration:
                    song.best_segment_start = max(0, song.duration - seg_duration)
                    song.best_segment_end = song.best_segment_start + seg_duration
                
                # Clean up
                Path(audio_path).unlink(missing_ok=True)
                
        except Exception as e:
            print(f"[AUTO_PLAYLIST] Analysis error for {song.original.title}: {e}")
            # Use defaults, but still try heatmap if available
            song.bpm = 120
            song.energy = 0.7
            seg_duration = 60.0
            
            if heatmap_segment:
                song.best_segment_start = heatmap_segment[0]
            else:
                song.best_segment_start = song.duration * 0.25
            
            song.best_segment_end = min(song.best_segment_start + seg_duration, song.duration)
        
        return song
    
    def create_mix_order(self, songs: List[DownloadedSong]) -> List[DownloadedSong]:
        """Order songs for optimal DJ flow based on BPM and energy"""
        if not songs:
            return songs
        
        # Start with a medium-energy song, build up, peak, cool down
        sorted_by_energy = sorted(songs, key=lambda s: s.energy)
        
        n = len(sorted_by_energy)
        if n <= 3:
            return sorted_by_energy
        
        # Create DJ curve: start medium, build to peak, cool down
        result = []
        
        # Start with medium energy (25th percentile)
        start_idx = n // 4
        result.append(sorted_by_energy[start_idx])
        sorted_by_energy.pop(start_idx)
        
        # Build up to peak (pick highest energy songs)
        peak_count = n // 3
        high_energy = sorted_by_energy[-peak_count:]
        sorted_by_energy = sorted_by_energy[:-peak_count]
        
        # Remaining for opening and cooldown
        remaining = sorted_by_energy
        
        # Opening section: build energy
        opening = remaining[:len(remaining)//2]
        opening.sort(key=lambda s: s.bpm)  # Sort by BPM for smooth transitions
        result.extend(opening)
        
        # Peak section
        high_energy.sort(key=lambda s: -s.energy)  # Highest energy in middle
        result.extend(high_energy)
        
        # Cool down
        cooldown = remaining[len(remaining)//2:]
        cooldown.sort(key=lambda s: -s.energy)  # Descending energy
        result.extend(cooldown)
        
        return result
    
    def generate_from_prompt(
        self,
        prompt: str,
        target_duration_minutes: int = 30,
        segment_duration: int = 60,  # 45-60 seconds per song - enough to enjoy the best part
        output_name: Optional[str] = None,
        custom_shoutouts: Optional[List[str]] = None,  # Friends to call out
        dj_special_notes: Optional[str] = None  # Extra DJ instructions
    ) -> AutoPlaylistResult:
        """
        Main entry: Generate a complete DJ playlist from a natural language prompt.
        
        1. Parse prompt with AI to get song recommendations
        2. Search and download from YouTube
        3. Analyze songs for BPM/energy
        4. Create optimal mix order
        5. Export with AI DJ commentary
        """
        from services.song_recommender import create_playlist_from_prompt
        
        result = AutoPlaylistResult(success=False)
        
        try:
            # Step 1: Parse prompt and get song recommendations
            self.log("[MUSIC] Analyzing your request with AI...", 0.05)
            plan = create_playlist_from_prompt(prompt, target_duration_minutes, find_youtube=True)
            
            if not plan:
                result.error = "Failed to parse prompt or find songs"
                return result
            
            result.theme = plan.theme
            self.log(f"[OK] Theme: {plan.theme}", 0.10)
            self.log(f"  Found {len(plan.songs)} song recommendations", 0.10)
            
            # Step 2: Download songs with YouTube URLs
            self.log("[DOWNLOAD] Downloading songs from YouTube...", 0.15)
            songs_with_url = [s for s in plan.songs if s.youtube_url]
            
            if not songs_with_url:
                result.error = "No songs found on YouTube"
                return result
            
            downloaded_songs: List[DownloadedSong] = []
            for i, song in enumerate(songs_with_url):
                progress = 0.15 + (0.45 * i / len(songs_with_url))
                downloaded = self.download_song(song, i+1, len(songs_with_url))
                if downloaded:
                    downloaded_songs.append(downloaded)
            
            if not downloaded_songs:
                result.error = "Failed to download any songs"
                return result
            
            result.songs_downloaded = len(downloaded_songs)
            self.log(f"[OK] Downloaded {len(downloaded_songs)} songs", 0.60)
            
            # Step 3: Analyze songs
            self.log("[ANALYZE] Analyzing songs for BPM and energy...", 0.62)
            for i, song in enumerate(downloaded_songs):
                self.analyze_song(song)
                self.log(f"  {song.original.title}: {song.bpm:.0f} BPM, Energy {song.energy:.0%}", 
                        0.62 + (0.08 * i / len(downloaded_songs)))
            
            # Step 4: Create optimal mix order
            self.log("[MIX] Creating optimal mix order...", 0.72)
            ordered_songs = self.create_mix_order(downloaded_songs)
            
            # Step 5: Add to database and create playlist
            self.log("[SAVE] Adding songs to database...", 0.75)
            playlist_id, db_songs = self._create_database_entries(ordered_songs, plan, segment_duration)
            result.playlist_id = playlist_id
            
            # Step 6: Export with AI DJ
            if output_name:
                self.log("[DJ] Generating AI DJ commentary and export...", 0.80)
                export_path = self._export_with_dj(
                    playlist_id, ordered_songs, plan, output_name,
                    custom_shoutouts=custom_shoutouts,
                    dj_special_notes=dj_special_notes
                )
                result.export_path = export_path
            
            # Calculate total duration
            result.total_duration = sum(
                min(segment_duration, s.duration) for s in ordered_songs
            )
            
            result.success = True
            self.log("[SUCCESS] Playlist created successfully!", 1.0)
            
            return result
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            result.error = str(e)
            return result
    
    def _create_database_entries(
        self, 
        songs: List[DownloadedSong], 
        plan: PlaylistPlan,
        segment_duration: int
    ) -> str:
        """Create database entries for songs and segments, return playlist ID"""
        import sqlite3
        import uuid
        
        db_path = Path(__file__).parent.parent.parent / "database.sqlite"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Ensure tables exist with correct schema matching architecture.md
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS songs (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                artist TEXT,
                language TEXT NOT NULL,
                duration INTEGER NOT NULL,
                thumbnail_url TEXT,
                youtube_url TEXT NOT NULL,
                bpm REAL,
                energy_score REAL,
                analysis_status TEXT DEFAULT 'pending',
                cached_audio_path TEXT,
                cached_video_path TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS segments (
                id TEXT PRIMARY KEY,
                song_id TEXT NOT NULL REFERENCES songs(id),
                start_time REAL NOT NULL,
                end_time REAL NOT NULL,
                duration REAL NOT NULL,
                energy_score REAL NOT NULL,
                is_primary INTEGER DEFAULT 0,
                label TEXT,
                cached_clip_path TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS playlists (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                target_duration INTEGER DEFAULT 2700,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS playlist_items (
                id TEXT PRIMARY KEY,
                playlist_id TEXT NOT NULL REFERENCES playlists(id),
                segment_id TEXT NOT NULL REFERENCES segments(id),
                position INTEGER NOT NULL,
                crossfade_duration REAL DEFAULT 2.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(playlist_id, position)
            )
        ''')
        
        # Create playlist (standard columns only - theme/notes stored in export config)
        playlist_id = str(uuid.uuid4())
        cursor.execute(
            'INSERT INTO playlists (id, name) VALUES (?, ?)',
            (playlist_id, f"AI Mix: {plan.theme}")
        )
        
        segment_ids = []
        
        for position, song in enumerate(songs):
            # Create or get song entry - using actual database schema
            song_id = str(uuid.uuid4())
            youtube_url = f"https://www.youtube.com/watch?v={song.original.youtube_id}" if song.original.youtube_id else ""
            
            cursor.execute('''
                INSERT INTO songs (id, title, artist, language, duration, youtube_url, bpm, energy_score, cached_video_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                song_id,
                song.original.title,
                song.original.artist,
                song.original.language,
                int(song.duration),
                youtube_url,
                song.bpm,
                song.energy / 100.0,  # Convert 0-100 to 0.0-1.0
                song.video_path
            ))
            
            # Create segment entry - using the pre-calculated best segment from analyze_song
            # which already has energy-based duration (45-90s)
            segment_id = str(uuid.uuid4())
            start_time = song.best_segment_start
            end_time = song.best_segment_end
            segment_duration_actual = end_time - start_time
            
            # Safety check: ensure minimum 45s if song is long enough
            if segment_duration_actual < 45 and song.duration >= 50:
                start_time = max(0, song.duration - 60)
                end_time = min(start_time + 60, song.duration)
                segment_duration_actual = end_time - start_time
            
            cursor.execute('''
                INSERT INTO segments (id, song_id, start_time, end_time, duration, energy_score, is_primary)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (segment_id, song_id, start_time, end_time, segment_duration_actual, song.energy, 1))
            
            # Add to playlist - using actual table name: playlist_items
            ps_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO playlist_items (id, playlist_id, segment_id, position)
                VALUES (?, ?, ?, ?)
            ''', (ps_id, playlist_id, segment_id, position))
            
            segment_ids.append(segment_id)
        
        conn.commit()
        conn.close()
        
        self.log(f"  Created playlist {playlist_id} with {len(segment_ids)} segments")
        return playlist_id, songs  # Return songs too for export
    
    def _export_with_dj(
        self, 
        playlist_id: str,
        songs: List[DownloadedSong],
        plan: PlaylistPlan,
        output_name: str,
        custom_shoutouts: Optional[List[str]] = None,
        dj_special_notes: Optional[str] = None
    ) -> Optional[str]:
        """Export playlist with AI DJ commentary"""
        try:
            from services.exporter import ExportSegment, export_playlist
            
            # Build segments from downloaded songs with correct ExportSegment fields
            segments = []
            for i, song in enumerate(songs):
                youtube_id = song.original.youtube_id or ""
                youtube_url = f"https://www.youtube.com/watch?v={youtube_id}" if youtube_id else ""
                
                # Use the best_segment_start/end that was calculated based on energy analysis
                # This already factors in 45-90s duration based on energy level
                segment_len = song.best_segment_end - song.best_segment_start
                
                # Safety check: ensure minimum 45s if song is long enough
                if segment_len < 45 and song.duration >= 50:
                    segment_len = min(60, song.duration - song.best_segment_start)
                    if segment_len < 45:
                        song.best_segment_start = max(0, song.duration - 60)
                        segment_len = min(60, song.duration - song.best_segment_start)
                
                segment = ExportSegment(
                    youtube_id=youtube_id,
                    youtube_url=youtube_url,
                    start_time=song.best_segment_start,
                    end_time=song.best_segment_start + segment_len,
                    song_title=song.original.title,
                    language=song.original.language,
                    position=i,
                    artist=song.original.artist or "Unknown Artist",
                    bpm=song.bpm or 120.0
                )
                # Attach local file path for the exporter to use
                segment.source_path = song.video_path
                segments.append(segment)
                
                self.log(f"  {song.original.title}: {segment_len:.0f}s segment @ {song.best_segment_start:.0f}s (energy: {song.energy:.0%})")
            
            # Export with AI DJ enabled
            # Combine plan notes with custom DJ notes
            combined_notes = plan.dj_notes or ""
            if dj_special_notes:
                combined_notes = f"{combined_notes}\n{dj_special_notes}".strip()
            
            result = export_playlist(
                segments=segments,
                output_name=output_name,
                crossfade_duration=3.5,  # Extended crossfade for smooth music blending
                transition_type="random",
                add_text_overlay=True,
                video_quality="1080p",
                dj_enabled=True,
                dj_voice="energetic_male",
                dj_frequency="moderate",
                dj_context={
                    'theme': plan.theme,
                    'mood': plan.mood,
                    'special_notes': combined_notes,
                    'original_prompt': plan.original_prompt,
                    'custom_shoutouts': custom_shoutouts or []
                }
            )
            
            if result and result.success and result.output_path:
                return result.output_path
                
        except Exception as e:
            self.log(f"Export error: {e}")
        
        return None


async def generate_playlist_async(
    prompt: str,
    target_duration: int = 30,
    output_name: Optional[str] = None,
    progress_callback: Optional[Callable[[str, float], None]] = None
) -> AutoPlaylistResult:
    """Async wrapper for playlist generation"""
    generator = AutoPlaylistGenerator(progress_callback=progress_callback)
    
    # Run in thread pool to not block
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: generator.generate_from_prompt(
            prompt, 
            target_duration,
            segment_duration=30,
            output_name=output_name
        )
    )
    
    return result


# Test
if __name__ == "__main__":
    test_prompt = """
    New Year 2026 party mix!
    Include some Bollywood hits from SRK movies.
    Add Tamil kuttu songs like Apdi Podu.
    Some Michael Jackson classics.
    Recent hits like Industry Baby.
    Badshah and Honey Singh bangers.
    AR Rahman hits in both Hindi and Tamil.
    80s/90s classics: Ice Ice Baby, George Michael, Bryan Adams.
    Make it a high energy dance party!
    """
    
    print("=" * 60)
    print("TESTING AUTO PLAYLIST GENERATOR")
    print("=" * 60)
    
    generator = AutoPlaylistGenerator()
    result = generator.generate_from_prompt(
        test_prompt,
        target_duration_minutes=15,  # Short for testing
        output_name="test_auto_mix"
    )
    
    print("\n" + "=" * 60)
    print("RESULT:")
    print(f"  Success: {result.success}")
    print(f"  Theme: {result.theme}")
    print(f"  Songs Downloaded: {result.songs_downloaded}")
    print(f"  Duration: {result.total_duration:.0f}s")
    print(f"  Playlist ID: {result.playlist_id}")
    print(f"  Export Path: {result.export_path}")
    if result.error:
        print(f"  Error: {result.error}")
