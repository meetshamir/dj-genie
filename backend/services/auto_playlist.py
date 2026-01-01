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
            self.log(f"  ✗ No YouTube URL for {song.title}")
            return None
        
        if not YT_DLP_AVAILABLE:
            self.log("  ✗ yt-dlp not available")
            return None
        
        # Create safe filename
        safe_name = f"{song.artist}_{song.title}".replace(" ", "_")
        safe_name = "".join(c for c in safe_name if c.isalnum() or c in "_-")[:50]
        output_template = str(self.downloads_dir / f"{safe_name}_%(id)s.%(ext)s")
        
        ydl_opts = {
            'format': 'best[height<=1080]',  # 1080p for HQ output
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'extract_audio': False,
        }
        
        try:
            self.log(f"  [{index}/{total}] Downloading: {song.artist} - {song.title}...")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
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
                    self.log(f"    ✗ Downloaded file not found")
                    return None
                
                downloaded = DownloadedSong(
                    original=song,
                    video_path=video_path,
                    duration=info.get('duration', 180)
                )
                
                self.log(f"    ✓ Downloaded ({downloaded.duration:.0f}s)")
                return downloaded
                
        except Exception as e:
            self.log(f"    ✗ Download failed: {e}")
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
    
    def analyze_song(self, song: DownloadedSong) -> DownloadedSong:
        """Analyze a song for BPM, energy, and find best HIGH-ENERGY segment"""
        if not LIBROSA_AVAILABLE:
            # Use defaults with some variation based on title hash
            song.bpm = 120 + (hash(song.original.title) % 40 - 20)
            song.energy = 0.6 + (hash(song.original.artist) % 40) / 100
            
            # For most songs, the chorus/drop is typically between 25-40% into the song
            # This is where the "popular" part usually is (what people remember)
            duration = song.duration
            
            # Calculate dynamic segment duration based on energy
            seg_duration = self._calculate_segment_duration(song.energy, duration)
            
            if duration > 180:
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
            # Extract audio for analysis - analyze MORE of the song to find the real peak
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                audio_path = tmp.name
            
            # Analyze up to 3 minutes to find the actual high-energy portion
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
                
                # Detect BPM
                tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
                if hasattr(tempo, '__iter__'):
                    tempo = float(tempo[0])
                song.bpm = float(tempo)
                
                # Calculate energy (RMS)
                rms = librosa.feature.rms(y=y)[0]
                song.energy = float(np.mean(rms) * 10)  # Scale to 0-1 range roughly
                song.energy = min(1.0, max(0.0, song.energy))
                
                # Calculate dynamic segment duration based on energy
                seg_duration = self._calculate_segment_duration(song.energy, song.duration)
                
                # Find most energetic segment using a sliding window
                hop_length = 512
                window_seconds = seg_duration  # Match our target segment duration
                window_size = int(window_seconds * sr / hop_length)
                
                if len(rms) > window_size:
                    # Sliding window to find max energy section
                    max_energy = 0
                    best_start_frame = 0
                    for i in range(len(rms) - window_size):
                        window_energy = np.sum(rms[i:i+window_size])
                        if window_energy > max_energy:
                            max_energy = window_energy
                            best_start_frame = i
                    
                    song.best_segment_start = best_start_frame * hop_length / sr
                    song.best_segment_end = song.best_segment_start + seg_duration
                    
                    # Ensure we don't overflow the song duration
                    if song.best_segment_end > song.duration:
                        song.best_segment_start = max(0, song.duration - seg_duration)
                        song.best_segment_end = song.best_segment_start + seg_duration
                else:
                    song.best_segment_start = 0
                    song.best_segment_end = min(seg_duration, song.duration)
                
                # Clean up
                Path(audio_path).unlink(missing_ok=True)
                
        except Exception as e:
            print(f"[AUTO_PLAYLIST] Analysis error for {song.original.title}: {e}")
            # Use defaults
            song.bpm = 120
            song.energy = 0.7
            song.best_segment_start = song.duration * 0.25
            song.best_segment_end = min(song.best_segment_start + 30, song.duration)
        
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
            self.log("🎵 Analyzing your request with AI...", 0.05)
            plan = create_playlist_from_prompt(prompt, target_duration_minutes, find_youtube=True)
            
            if not plan:
                result.error = "Failed to parse prompt or find songs"
                return result
            
            result.theme = plan.theme
            self.log(f"✓ Theme: {plan.theme}", 0.10)
            self.log(f"  Found {len(plan.songs)} song recommendations", 0.10)
            
            # Step 2: Download songs with YouTube URLs
            self.log("📥 Downloading songs from YouTube...", 0.15)
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
            self.log(f"✓ Downloaded {len(downloaded_songs)} songs", 0.60)
            
            # Step 3: Analyze songs
            self.log("🔍 Analyzing songs for BPM and energy...", 0.62)
            for i, song in enumerate(downloaded_songs):
                self.analyze_song(song)
                self.log(f"  {song.original.title}: {song.bpm:.0f} BPM, Energy {song.energy:.0%}", 
                        0.62 + (0.08 * i / len(downloaded_songs)))
            
            # Step 4: Create optimal mix order
            self.log("🎚️ Creating optimal mix order...", 0.72)
            ordered_songs = self.create_mix_order(downloaded_songs)
            
            # Step 5: Add to database and create playlist
            self.log("💾 Adding songs to database...", 0.75)
            playlist_id, db_songs = self._create_database_entries(ordered_songs, plan, segment_duration)
            result.playlist_id = playlist_id
            
            # Step 6: Export with AI DJ
            if output_name:
                self.log("🎤 Generating AI DJ commentary and export...", 0.80)
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
            self.log("✅ Playlist created successfully!", 1.0)
            
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
                crossfade_duration=1.5,
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
