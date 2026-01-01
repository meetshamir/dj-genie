# Video DJ Playlist Creator — Specification

> **Version:** 1.0  
> **Date:** December 31, 2025  
> **Status:** Phase 0 — Specification

---

## 1. Overview

### 1.1 Problem Statement

Creating a high-energy dance video playlist from YouTube requires hours of manual work:
- Searching for popular songs across multiple languages
- Watching full videos to find the exciting parts
- Manually downloading and editing video segments
- Sequencing clips for good flow
- Exporting the final compilation

### 1.2 Solution

An automated desktop application that:
1. **Discovers** popular dance songs across 7 languages automatically
2. **Analyzes** audio to detect high-energy segments (hooks, choruses, drops)
3. **Presents** a grid interface for rapid hover-to-preview selection
4. **Assembles** selected segments with crossfades automatically
5. **Exports** a seamless video playlist with one click

### 1.3 Target Output

- **Duration:** 45 minutes
- **Segment length:** 45-90 seconds per song (exciting parts only)
- **Languages:** English, Hindi, Malayalam, Tamil, Turkish, Uzbek, Arabic
- **Songs needed:** ~30-60 depending on segment length
- **Manual effort:** ~5 minutes of browsing/clicking

---

## 2. Tech Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| Desktop Shell | Tauri | 2.0 | Lightweight native app wrapper |
| Frontend | React + TypeScript | 18.x | UI components |
| Styling | Tailwind CSS | 3.x | Rapid UI development |
| Backend | Python | 3.11+ | Audio/video processing workers |
| Video Download | yt-dlp | Latest | YouTube video/audio fetching |
| Audio Analysis | librosa | 0.10+ | Beat detection, energy analysis |
| Video Processing | FFmpeg | 6.x | Segment extraction, concatenation |
| FFmpeg Bindings | ffmpeg-python | 0.2+ | Pythonic FFmpeg interface |
| Database | SQLite | 3.x | Song/segment metadata cache |
| IPC | HTTP REST | - | Tauri ↔ Python communication |

### 2.1 Why This Stack?

- **Tauri over Electron:** 10x smaller bundle, lower memory usage, Rust security
- **Python for processing:** Best-in-class libraries (librosa, yt-dlp) with no viable JS alternatives
- **SQLite:** Zero-config, file-based, perfect for single-user desktop app
- **REST over WebSocket:** Simpler debugging, sufficient for our request/response pattern

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        TAURI SHELL                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    React Frontend                          │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐  │  │
│  │  │ Discovery   │ │ Preview     │ │ Playlist Builder    │  │  │
│  │  │ Grid        │ │ Modal       │ │ + Export            │  │  │
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              │ HTTP (localhost:9876)             │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                 Python Sidecar Process                     │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐  │  │
│  │  │ Discovery   │ │ Analysis    │ │ Export              │  │  │
│  │  │ Service     │ │ Service     │ │ Service             │  │  │
│  │  │ (yt-dlp)    │ │ (librosa)   │ │ (FFmpeg)            │  │  │
│  │  └─────────────┘ └─────────────┘ └─────────────────────┘  │  │
│  │                         │                                  │  │
│  │                         ▼                                  │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │                 SQLite Database                      │  │  │
│  │  │  songs │ segments │ playlists │ export_jobs          │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    File System                             │  │
│  │  ~/video-dj-playlist/                                      │  │
│  │  ├── cache/audio/      # Downloaded audio for analysis    │  │
│  │  ├── cache/video/      # Downloaded video segments        │  │
│  │  ├── cache/thumbnails/ # Video thumbnails                 │  │
│  │  └── exports/          # Final rendered playlists         │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.1 Process Flow

```
User launches app
       │
       ▼
┌──────────────────┐
│ Discovery Phase  │ ← Automatic on startup
│ (3 songs × 7 lang│   
│  = 21 songs)     │   
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Analysis Phase   │ ← Background, parallel
│ - Download audio │
│ - Detect energy  │
│ - Find segments  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Selection Phase  │ ← User interaction
│ - Grid browse    │
│ - Hover preview  │
│ - Click to add   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Assembly Phase   │ ← Automatic
│ - Auto-sequence  │
│ - Crossfade calc │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Export Phase     │ ← One click
│ - FFmpeg concat  │
│ - Progress UI    │
└────────┬─────────┘
         │
         ▼
    final.mp4
```

---

## 4. Data Models

### 4.1 Song

```typescript
interface Song {
  id: string;                    // YouTube video ID
  title: string;                 // Video title
  artist: string;                // Extracted artist name (best effort)
  language: Language;            // Detected/assigned language
  duration: number;              // Total duration in seconds
  thumbnail_url: string;         // YouTube thumbnail
  youtube_url: string;           // Full YouTube URL
  bpm: number | null;            // Detected BPM
  energy_score: number;          // 0-100 overall energy rating
  analysis_status: AnalysisStatus;
  created_at: string;            // ISO timestamp
  cached_audio_path: string | null;
  cached_video_path: string | null;
}

type Language = 'english' | 'hindi' | 'malayalam' | 'tamil' | 'turkish' | 'uzbek' | 'arabic';
type AnalysisStatus = 'pending' | 'downloading' | 'analyzing' | 'complete' | 'failed';
```

### 4.2 Segment

```typescript
interface Segment {
  id: string;                    // UUID
  song_id: string;               // FK to Song
  start_time: number;            // Start in seconds
  end_time: number;              // End in seconds
  duration: number;              // Computed: end - start
  energy_score: number;          // Segment-specific energy (0-100)
  is_primary: boolean;           // Highest energy segment for this song
  label: string;                 // 'chorus_1', 'drop', 'hook_2', etc.
  cached_clip_path: string | null;
}
```

### 4.3 Playlist

```typescript
interface Playlist {
  id: string;                    // UUID
  name: string;                  // User-provided or auto-generated
  target_duration: number;       // Target length in seconds (2700 = 45min)
  created_at: string;
  updated_at: string;
}

interface PlaylistItem {
  id: string;
  playlist_id: string;           // FK to Playlist
  segment_id: string;            // FK to Segment
  position: number;              // Order in playlist (0-indexed)
  crossfade_duration: number;    // Seconds to crossfade with next (default: 2)
}
```

### 4.4 ExportJob

```typescript
interface ExportJob {
  id: string;                    // UUID
  playlist_id: string;           // FK to Playlist
  status: ExportStatus;
  progress: number;              // 0-100
  output_path: string | null;    // Final file path when complete
  output_format: 'mp4' | 'webm' | 'mov';
  resolution: '1080p' | '720p';
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
}

type ExportStatus = 'queued' | 'downloading' | 'processing' | 'encoding' | 'complete' | 'failed';
```

---

## 5. Discovery Module

### 5.1 Search Queries by Language

| Language | Primary Query | Fallback Query |
|----------|---------------|----------------|
| English | `"popular dance songs 2024 party hits"` | `"top EDM songs 2023"` |
| Hindi | `"bollywood party songs 2024 dance"` | `"hindi dance songs hit"` |
| Malayalam | `"malayalam dance songs 2024"` | `"malayalam disco songs"` |
| Tamil | `"tamil kuthu songs 2024 dance"` | `"tamil party songs hit"` |
| Turkish | `"türkçe pop dans şarkıları 2024"` | `"turkish dance music"` |
| Uzbek | `"o'zbek raqs qo'shiqlari 2024"` | `"uzbek dance songs"` |
| Arabic | `"اغاني رقص عربية 2024"` | `"arabic dance songs 2024"` |

### 5.2 Discovery Algorithm

```python
def discover_songs(language: str, count: int = 3) -> list[Song]:
    query = SEARCH_QUERIES[language]['primary']
    
    # Use yt-dlp to search YouTube
    results = yt_dlp_search(f"ytsearch{count * 2}:{query}")
    
    # Filter: must be music, 2-7 minutes, not live/remix
    filtered = [
        r for r in results
        if 120 < r['duration'] < 420
        and 'live' not in r['title'].lower()
        and 'remix' not in r['title'].lower()  # Optional: can include remixes
    ]
    
    return filtered[:count]
```

### 5.3 Caching Strategy

- Songs cached in SQLite with 7-day TTL
- Re-discovery triggered manually or on app update
- Thumbnails cached to disk for instant grid loading

---

## 6. Analysis Module

### 6.1 Energy Detection Algorithm

```python
def analyze_song(song: Song) -> list[Segment]:
    # 1. Download audio only (faster than video)
    audio_path = download_audio(song.youtube_url)
    
    # 2. Load with librosa
    y, sr = librosa.load(audio_path, sr=22050)
    
    # 3. Compute energy features
    rms = librosa.feature.rms(y=y)[0]                    # Volume envelope
    spectral = librosa.feature.spectral_centroid(y=y)[0] # Brightness
    onset_env = librosa.onset.onset_strength(y=y, sr=sr) # Attack density
    
    # 4. Combine into composite energy score
    energy = normalize(rms) * 0.4 + normalize(spectral) * 0.3 + normalize(onset_env) * 0.3
    
    # 5. Detect BPM
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    
    # 6. Find high-energy windows (45-90 sec)
    segments = find_peak_windows(energy, sr, min_duration=45, max_duration=90)
    
    return segments
```

### 6.2 Segment Extraction Rules

1. **Minimum segment duration:** 45 seconds
2. **Maximum segment duration:** 90 seconds
3. **Maximum segments per song:** 3 (to allow multiple hooks)
4. **Minimum gap between segments:** 30 seconds (avoid overlap)
5. **Energy threshold:** Top 30% of song's energy curve

### 6.3 Multi-Hook Detection

```python
def find_peak_windows(energy: np.array, sr: int, min_dur: int, max_dur: int) -> list[Segment]:
    # Sliding window to find high-energy regions
    window_size = min_dur * sr // 512  # Convert to frames
    
    peaks = []
    for start in range(0, len(energy) - window_size, window_size // 2):
        window_energy = np.mean(energy[start:start + window_size])
        peaks.append((start, window_energy))
    
    # Sort by energy, take top 3 non-overlapping
    peaks.sort(key=lambda x: x[1], reverse=True)
    
    selected = []
    for peak in peaks:
        if not overlaps_any(peak, selected, min_gap=30):
            selected.append(peak)
        if len(selected) >= 3:
            break
    
    return selected
```

---

## 7. UI Screens

### 7.1 Discovery Grid (Main Screen)

```
┌─────────────────────────────────────────────────────────────────────┐
│  Video DJ Playlist                                    [Settings] ⚙️  │
├─────────────────────────────────────────────────────────────────────┤
│  Languages: [All ▼]    Status: [Ready ▼]    Sort: [Energy ▼]       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ 🎵       │ │ 🎵       │ │ 🎵       │ │ 🎵       │ │ 🎵       │  │
│  │ Thumbnail│ │ Thumbnail│ │ Thumbnail│ │ Thumbnail│ │ Thumbnail│  │
│  │          │ │          │ │          │ │          │ │          │  │
│  ├──────────┤ ├──────────┤ ├──────────┤ ├──────────┤ ├──────────┤  │
│  │ ████░░░░ │ │ ██████░░ │ │ ███░░░░░ │ │ ███████░ │ │ █████░░░ │  │
│  │ Song Nam │ │ Song Nam │ │ Song Nam │ │ Song Nam │ │ Song Nam │  │
│  │ 🇺🇸 128bpm│ │ 🇮🇳 115bpm│ │ 🇹🇷 122bpm│ │ 🇸🇦 130bpm│ │ 🇮🇳 118bpm│  │
│  │ [2 segs] │ │ [1 seg]  │ │ [3 segs] │ │ [2 segs] │ │ [1 seg]  │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│                                                                      │
│  (Hover to preview • Click to add • Shows detected segments)        │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│  Playlist: 0 songs • 0:00 / 45:00              [Preview] [Export]   │
└─────────────────────────────────────────────────────────────────────┘
```

**Interactions:**
- **Hover:** Auto-plays the highest-energy segment (muted by default, click to unmute)
- **Click thumbnail:** Opens segment selector modal
- **Energy bar:** Visual indicator of song's energy (green = high)
- **Segment count:** Shows how many exciting parts were detected

### 7.2 Segment Selector Modal

```
┌─────────────────────────────────────────────────────────────────────┐
│  Song Title - Artist                                          [X]   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                                                               │  │
│  │                      VIDEO PLAYER                             │  │
│  │                                                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ Energy:  ░░▓▓▓▓▓░░░░░░▓▓▓▓▓▓▓▓░░░░░░░▓▓▓░░░░░░░░░░░░░░░░░░░░ │  │
│  │ Timeline: |----[seg1]-------|---[seg2]---|------[seg3]---|    │  │
│  │           0:00            1:30          2:45            4:00  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  Detected Segments:                                                  │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ [▶] Segment 1: 0:45 - 1:30 (45s) ████████░░ 85%    [+ Add]  │    │
│  │ [▶] Segment 2: 1:50 - 2:45 (55s) ██████████ 92%    [+ Add]  │    │
│  │ [▶] Segment 3: 3:10 - 3:55 (45s) ██████░░░░ 71%    [+ Add]  │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│                              [Add All Segments]                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Interactions:**
- **Play button:** Preview that specific segment
- **Energy bar:** Per-segment energy score
- **Add button:** Add individual segment to playlist
- **Add All:** Add all segments from this song

### 7.3 Playlist Builder (Side Panel)

```
┌────────────────────────────────┐
│  Your Playlist          [Clear]│
├────────────────────────────────┤
│  Duration: 12:30 / 45:00       │
│  Songs: 8 segments             │
├────────────────────────────────┤
│  1. 🇮🇳 Song Name (0:55)    [⋮] │
│  2. 🇺🇸 Song Name (1:02)    [⋮] │
│  3. 🇹🇷 Song Name (0:48)    [⋮] │
│  4. 🇸🇦 Song Name (1:15)    [⋮] │
│  5. 🇮🇳 Song Name (0:52)    [⋮] │
│  6. 🇺🇿 Song Name (0:45)    [⋮] │
│  7. 🇮🇳 Song Name (1:08)    [⋮] │
│  8. 🇺🇸 Song Name (0:55)    [⋮] │
│                                │
│  (Drag to reorder)             │
├────────────────────────────────┤
│  [Auto-Sequence by BPM]        │
│  [Auto-Sequence by Energy]     │
├────────────────────────────────┤
│  Crossfade: [2 sec ▼]          │
│  Fade in/out: [✓]              │
├────────────────────────────────┤
│  [Preview Mix]  [Export Video] │
└────────────────────────────────┘
```

### 7.4 Export Progress Modal

```
┌─────────────────────────────────────────────────────────────────────┐
│  Exporting Playlist...                                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Status: Encoding video segments                                     │
│                                                                      │
│  ████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  45%         │
│                                                                      │
│  Step 3 of 5: Processing segment 8 of 18                            │
│                                                                      │
│  Elapsed: 2:34                                                       │
│  Remaining: ~3:12                                                    │
│                                                                      │
│                                              [Cancel]                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 8. Export Pipeline

### 8.1 Export Steps

1. **Download video segments** (if not cached)
   - Use yt-dlp with `--download-sections` for precise cuts
   - Cache segments for reuse

2. **Normalize audio levels**
   - Target: -14 LUFS (YouTube standard)
   - Prevents jarring volume jumps between songs

3. **Generate crossfade transitions**
   - Default: 2 second audio + video crossfade
   - Uses FFmpeg `xfade` filter

4. **Concatenate segments**
   - FFmpeg concat demuxer for efficiency
   - Re-encode only transition frames

5. **Add fade in/out**
   - 3 second fade in at start
   - 5 second fade out at end

6. **Final encode**
   - H.264 video, AAC audio
   - 1080p (or 720p if selected)
   - GPU acceleration if available (NVENC)

### 8.2 FFmpeg Command (Simplified)

```bash
ffmpeg -i segment1.mp4 -i segment2.mp4 -i segment3.mp4 \
  -filter_complex "
    [0:v][1:v]xfade=transition=fade:duration=2:offset=43[v01];
    [v01][2:v]xfade=transition=fade:duration=2:offset=96[vout];
    [0:a][1:a]acrossfade=d=2[a01];
    [a01][2:a]acrossfade=d=2[aout]
  " \
  -map "[vout]" -map "[aout]" \
  -c:v libx264 -preset fast -crf 22 \
  -c:a aac -b:a 192k \
  output.mp4
```

### 8.3 GPU Acceleration

```python
def get_encoder():
    # Check for NVIDIA GPU
    if has_nvenc():
        return "-c:v h264_nvenc -preset p4 -cq 22"
    # Check for AMD GPU
    elif has_amf():
        return "-c:v h264_amf -quality balanced -qp 22"
    # Fallback to CPU
    else:
        return "-c:v libx264 -preset fast -crf 22"
```

---

## 9. Configuration

### 9.1 User Preferences

```typescript
interface UserPreferences {
  // Discovery
  enabled_languages: Language[];        // Default: all 7
  songs_per_language: number;           // Default: 3 (test), 50 (production)
  include_remixes: boolean;             // Default: false
  
  // Analysis  
  min_segment_duration: number;         // Default: 45 seconds
  max_segment_duration: number;         // Default: 90 seconds
  max_segments_per_song: number;        // Default: 3
  
  // Export
  target_playlist_duration: number;     // Default: 2700 (45 min)
  crossfade_duration: number;           // Default: 2 seconds
  output_format: 'mp4' | 'webm' | 'mov';// Default: mp4
  output_resolution: '1080p' | '720p';  // Default: 1080p
  use_gpu_acceleration: boolean;        // Default: true (if available)
  
  // UI
  auto_play_on_hover: boolean;          // Default: true
  hover_volume: number;                 // Default: 0.3 (30%)
}
```

### 9.2 File Paths

```
Windows: C:\Users\{user}\video-dj-playlist\
macOS:   ~/Library/Application Support/video-dj-playlist/
Linux:   ~/.local/share/video-dj-playlist/

Structure:
├── config.json           # User preferences
├── database.sqlite       # Song/segment/playlist data
├── cache/
│   ├── audio/           # Downloaded audio (MP3, ~5MB each)
│   ├── video/           # Downloaded video segments (~50MB each)
│   └── thumbnails/      # Video thumbnails (~100KB each)
└── exports/             # Final rendered playlists
```

---

## 10. Implementation Phases

### Phase 0: Specification ✅
- [x] SPEC.md (this document)
- [ ] architecture.md (detailed component design)

### Phase 1: Discovery Engine
- [ ] Python project setup (FastAPI, yt-dlp)
- [ ] SQLite schema creation
- [ ] Discovery service with search queries
- [ ] REST endpoints: `GET /songs`, `POST /discover`
- **Test:** 21 songs fetched (3 per language)

### Phase 2: Analysis Pipeline
- [ ] Audio download service
- [ ] librosa energy analysis
- [ ] Segment detection algorithm
- [ ] Background worker queue
- [ ] REST endpoints: `POST /analyze/{song_id}`, `GET /segments/{song_id}`
- **Test:** All 21 songs analyzed, segments extracted

### Phase 3: Desktop UI
- [ ] Tauri project setup
- [ ] React + Tailwind scaffold
- [ ] Discovery grid component
- [ ] Segment selector modal
- [ ] Playlist builder panel
- [ ] Preview player with waveform
- **Test:** Full browse + select workflow

### Phase 4: Export Pipeline
- [ ] FFmpeg wrapper service
- [ ] Crossfade generation
- [ ] Concatenation logic
- [ ] Progress reporting
- [ ] GPU detection
- [ ] REST endpoints: `POST /export`, `GET /export/{job_id}`
- **Test:** 7-song mini playlist exports successfully

### Phase 5: Polish
- [ ] Auto-sequencing by BPM/energy
- [ ] Keyboard shortcuts
- [ ] Error handling + retry logic
- [ ] Settings UI
- [ ] Scale to 50+ songs per language
- **Test:** Full 45-min export with smooth flow

---

## 11. API Contracts

See [docs/api-contracts.md](docs/api-contracts.md) for detailed endpoint specifications.

---

## 12. Open Questions

1. **Offline mode?** Should the app work offline with cached songs, or always require internet?
2. **Song deduplication?** Same song may appear in multiple language searches — detect and merge?
3. **User song additions?** Allow pasting YouTube URLs to add specific songs?
4. **Playlist templates?** Save/load playlist configurations for quick regeneration?

---

## Appendix A: Test Dataset

| Language | Query | Expected Results |
|----------|-------|------------------|
| English | "popular dance songs 2024 party hits" | 3 songs |
| Hindi | "bollywood party songs 2024 dance" | 3 songs |
| Malayalam | "malayalam dance songs 2024" | 3 songs |
| Tamil | "tamil kuthu songs 2024 dance" | 3 songs |
| Turkish | "türkçe pop dans şarkıları 2024" | 3 songs |
| Uzbek | "o'zbek raqs qo'shiqlari 2024" | 3 songs |
| Arabic | "اغاني رقص عربية 2024" | 3 songs |

**Total: 21 songs for Phase 1-4 testing**

---

## Appendix B: Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Play/Pause preview |
| `Enter` | Add current song/segment to playlist |
| `Escape` | Close modal / deselect |
| `←` / `→` | Skip ±5 seconds in preview |
| `↑` / `↓` | Navigate grid |
| `1-9` | Quick-add segment by number |
| `Ctrl+E` | Export playlist |
| `Ctrl+P` | Preview full mix |

---

*End of Specification*
