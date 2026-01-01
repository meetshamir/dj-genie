# Architecture — Video DJ Playlist Creator

> **Version:** 1.0  
> **Date:** December 31, 2025

---

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER'S MACHINE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         TAURI APPLICATION                              │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │ │
│  │  │                     WEBVIEW (React Frontend)                     │  │ │
│  │  │                                                                  │  │ │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │  │ │
│  │  │  │  Discovery  │  │   Preview   │  │   Playlist Builder      │  │  │ │
│  │  │  │    Grid     │  │   Player    │  │   + Export Controls     │  │  │ │
│  │  │  └─────────────┘  └─────────────┘  └─────────────────────────┘  │  │ │
│  │  │                           │                                      │  │ │
│  │  │                           │ API Calls (fetch)                    │  │ │
│  │  │                           ▼                                      │  │ │
│  │  │  ┌───────────────────────────────────────────────────────────┐  │  │ │
│  │  │  │               API Client (TypeScript)                     │  │  │ │
│  │  │  │  - SongService, SegmentService, PlaylistService          │  │  │ │
│  │  │  │  - ExportService, PreferencesService                     │  │  │ │
│  │  │  └───────────────────────────────────────────────────────────┘  │  │ │
│  │  └──────────────────────────────────────────────────────────────────┘  │ │
│  │                               │                                         │ │
│  │                               │ HTTP REST (localhost:9876)              │ │
│  │                               ▼                                         │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │ │
│  │  │                  RUST LAYER (Tauri Core)                         │  │ │
│  │  │  - Spawns Python sidecar on startup                              │  │ │
│  │  │  - Manages process lifecycle                                     │  │ │
│  │  │  - Handles file system permissions                               │  │ │
│  │  └──────────────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                               │                                              │
│                               │ Process spawn + HTTP                         │
│                               ▼                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    PYTHON SIDECAR PROCESS                              │ │
│  │                                                                         │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │ │
│  │  │                    FastAPI Server (:9876)                        │  │ │
│  │  │  /api/songs, /api/segments, /api/playlists, /api/export         │  │ │
│  │  └──────────────────────────────────────────────────────────────────┘  │ │
│  │                               │                                         │ │
│  │            ┌──────────────────┼──────────────────┐                     │ │
│  │            ▼                  ▼                  ▼                     │ │
│  │  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐          │ │
│  │  │   Discovery     │ │    Analysis     │ │     Export      │          │ │
│  │  │   Service       │ │    Service      │ │     Service     │          │ │
│  │  │                 │ │                 │ │                 │          │ │
│  │  │  - yt-dlp       │ │  - librosa      │ │  - FFmpeg       │          │ │
│  │  │  - YouTube API  │ │  - numpy        │ │  - GPU detect   │          │ │
│  │  └────────┬────────┘ └────────┬────────┘ └────────┬────────┘          │ │
│  │           │                   │                   │                    │ │
│  │           └───────────────────┼───────────────────┘                    │ │
│  │                               ▼                                        │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │ │
│  │  │                    Data Access Layer                             │ │ │
│  │  │  - SQLAlchemy ORM                                                │ │ │
│  │  │  - SQLite database                                               │ │ │
│  │  └──────────────────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                               │                                              │
│                               ▼                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         FILE SYSTEM                                    │ │
│  │                                                                         │ │
│  │  ~/video-dj-playlist/                                                  │ │
│  │  ├── database.sqlite        # All metadata                             │ │
│  │  ├── config.json            # User preferences                         │ │
│  │  ├── cache/                                                            │ │
│  │  │   ├── audio/            # Downloaded MP3s for analysis              │ │
│  │  │   ├── video/            # Cached video segments                     │ │
│  │  │   └── thumbnails/       # Video thumbnails                          │ │
│  │  └── exports/              # Final rendered playlists                  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                               │
                               │ HTTPS
                               ▼
                    ┌─────────────────────┐
                    │   EXTERNAL APIS     │
                    │  - YouTube          │
                    │  - SponsorBlock     │
                    └─────────────────────┘
```

---

## 2. Component Details

### 2.1 Frontend (React + TypeScript)

```
src/
├── App.tsx                 # Root component, routing
├── main.tsx               # Entry point
├── index.css              # Tailwind imports
│
├── components/
│   ├── layout/
│   │   ├── Header.tsx          # App title, settings button
│   │   ├── MainLayout.tsx      # Grid + sidebar layout
│   │   └── Sidebar.tsx         # Playlist panel container
│   │
│   ├── discovery/
│   │   ├── DiscoveryGrid.tsx   # Main song grid
│   │   ├── SongCard.tsx        # Individual song thumbnail
│   │   ├── SongCardSkeleton.tsx# Loading state
│   │   ├── LanguageFilter.tsx  # Language filter dropdown
│   │   └── StatusBadge.tsx     # Analysis status indicator
│   │
│   ├── preview/
│   │   ├── PreviewModal.tsx    # Full segment selector
│   │   ├── VideoPlayer.tsx     # YouTube embed / local player
│   │   ├── EnergyWaveform.tsx  # Canvas-based energy viz
│   │   ├── SegmentList.tsx     # List of detected segments
│   │   └── SegmentItem.tsx     # Single segment row
│   │
│   ├── playlist/
│   │   ├── PlaylistBuilder.tsx # Main playlist panel
│   │   ├── PlaylistItem.tsx    # Draggable playlist entry
│   │   ├── PlaylistControls.tsx# Auto-sequence, crossfade
│   │   └── DurationBar.tsx     # Progress toward target
│   │
│   └── export/
│       ├── ExportModal.tsx     # Export settings + progress
│       ├── ExportProgress.tsx  # Progress bar + status
│       └── ExportComplete.tsx  # Success state + file link
│
├── services/
│   ├── api.ts              # Base fetch wrapper
│   ├── songService.ts      # Song CRUD operations
│   ├── segmentService.ts   # Segment operations
│   ├── playlistService.ts  # Playlist operations
│   └── exportService.ts    # Export job management
│
├── hooks/
│   ├── useSongs.ts         # Song data + loading state
│   ├── useSegments.ts      # Segment data for a song
│   ├── usePlaylist.ts      # Current playlist state
│   ├── useExport.ts        # Export job polling
│   └── usePreferences.ts   # User settings
│
├── stores/
│   └── playlistStore.ts    # Zustand store for playlist state
│
├── types/
│   └── index.ts            # TypeScript interfaces
│
└── utils/
    ├── formatters.ts       # Duration, date formatting
    └── constants.ts        # Language codes, defaults
```

### 2.2 Backend (Python + FastAPI)

```
backend/
├── main.py                 # FastAPI app, startup/shutdown
├── config.py              # Settings, paths, constants
├── requirements.txt       # Python dependencies
│
├── api/
│   ├── __init__.py
│   ├── routes.py          # All route definitions
│   ├── songs.py           # /api/songs endpoints
│   ├── segments.py        # /api/segments endpoints
│   ├── playlists.py       # /api/playlists endpoints
│   └── export.py          # /api/export endpoints
│
├── services/
│   ├── __init__.py
│   ├── discovery.py       # YouTube search, song fetching
│   ├── download.py        # yt-dlp wrapper, caching
│   ├── analysis.py        # librosa energy analysis
│   ├── segmentation.py    # High-energy segment detection
│   └── export.py          # FFmpeg encoding pipeline
│
├── models/
│   ├── __init__.py
│   ├── database.py        # SQLAlchemy setup
│   ├── song.py            # Song ORM model
│   ├── segment.py         # Segment ORM model
│   ├── playlist.py        # Playlist + PlaylistItem models
│   └── export_job.py      # ExportJob model
│
├── schemas/
│   ├── __init__.py
│   ├── song.py            # Pydantic schemas for Song
│   ├── segment.py         # Pydantic schemas for Segment
│   ├── playlist.py        # Pydantic schemas for Playlist
│   └── export.py          # Pydantic schemas for Export
│
├── workers/
│   ├── __init__.py
│   ├── queue.py           # Simple in-memory job queue
│   ├── analysis_worker.py # Background analysis jobs
│   └── export_worker.py   # Background export jobs
│
└── utils/
    ├── __init__.py
    ├── ffmpeg.py          # FFmpeg command builders
    ├── gpu.py             # GPU detection
    └── paths.py           # Path management
```

---

## 3. Data Flow Diagrams

### 3.1 Discovery Flow

```
User launches app
       │
       ▼
┌──────────────────────────────┐
│  Frontend: App.tsx           │
│  useEffect → fetch /songs    │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  Backend: GET /api/songs     │
│  Check SQLite for cached     │
└──────────────┬───────────────┘
               │
        ┌──────┴──────┐
        │             │
        ▼             ▼
   (cache hit)   (cache miss/stale)
        │             │
        │             ▼
        │    ┌──────────────────────────────┐
        │    │  Backend: discover_songs()   │
        │    │  For each language:          │
        │    │    yt-dlp ytsearch3:query    │
        │    │    Parse results             │
        │    │    Insert into SQLite        │
        │    └──────────────┬───────────────┘
        │                   │
        └───────┬───────────┘
                │
                ▼
┌──────────────────────────────┐
│  Return Song[] to frontend   │
│  (21 songs, 3 per language)  │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  Frontend: DiscoveryGrid     │
│  Render SongCard for each    │
└──────────────────────────────┘
```

### 3.2 Analysis Flow

```
Songs discovered
       │
       ▼
┌──────────────────────────────┐
│  Backend: POST /api/analyze  │
│  Queue songs for analysis    │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  Worker: analysis_worker.py  │
│  Process queue in background │
└──────────────┬───────────────┘
               │
     ┌─────────┴─────────┐
     ▼                   ▼
┌──────────────┐  ┌──────────────┐
│ Download     │  │ (parallel    │
│ audio via    │  │  processing) │
│ yt-dlp       │  │              │
└──────┬───────┘  └──────────────┘
       │
       ▼
┌──────────────────────────────┐
│  librosa.load(audio.mp3)     │
│  Compute:                    │
│  - RMS energy                │
│  - Spectral centroid         │
│  - Onset strength            │
│  - BPM                       │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  find_peak_windows()         │
│  Detect 1-3 high-energy      │
│  segments (45-90 sec each)   │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  Insert Segments into SQLite │
│  Update Song.analysis_status │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  Frontend polls for updates  │
│  Refresh grid with segments  │
└──────────────────────────────┘
```

### 3.3 Selection Flow

```
User hovers over SongCard
       │
       ▼
┌──────────────────────────────┐
│  Frontend: SongCard          │
│  onMouseEnter → load preview │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  GET /api/segments/{song_id} │
│  Return Segment[]            │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  Play highest-energy segment │
│  via YouTube embed           │
│  (start_time param)          │
└──────────────────────────────┘

User clicks SongCard
       │
       ▼
┌──────────────────────────────┐
│  Open PreviewModal           │
│  Show all segments           │
│  User clicks [+ Add]         │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  playlistStore.addSegment()  │
│  Update local state          │
│  POST /api/playlists/{id}/   │
│       items                  │
└──────────────────────────────┘
```

### 3.4 Export Flow

```
User clicks [Export Video]
       │
       ▼
┌──────────────────────────────┐
│  Frontend: ExportModal       │
│  Select format, resolution   │
│  Click [Start Export]        │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  POST /api/export            │
│  { playlist_id, format, res }│
│  Returns: { job_id }         │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  Worker: export_worker.py    │
│  Process in background       │
└──────────────┬───────────────┘
               │
     ┌─────────┴─────────┐
     ▼                   │
┌──────────────┐         │
│ For each     │         │
│ segment:     │         │
│ - Download   │         │
│   video clip │         │
│ - Normalize  │         │
│   audio      │         │
└──────┬───────┘         │
       │                 │
       ▼                 │
┌──────────────┐         │
│ Generate     │         │
│ concat file  │         │
│ with xfades  │         │
└──────┬───────┘         │
       │                 │
       ▼                 │
┌──────────────┐         │
│ FFmpeg       │◄────────┘
│ encode       │ (progress updates)
│ final.mp4    │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────┐
│  Update ExportJob.status     │
│  = 'complete'                │
│  Set output_path             │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│  Frontend polls GET /export/ │
│  {job_id}                    │
│  Show ExportComplete         │
│  with file link              │
└──────────────────────────────┘
```

---

## 4. Database Schema

```sql
-- Songs table
CREATE TABLE songs (
    id TEXT PRIMARY KEY,              -- YouTube video ID
    title TEXT NOT NULL,
    artist TEXT,
    language TEXT NOT NULL,
    duration INTEGER NOT NULL,        -- seconds
    thumbnail_url TEXT,
    youtube_url TEXT NOT NULL,
    bpm REAL,
    energy_score REAL,
    analysis_status TEXT DEFAULT 'pending',
    cached_audio_path TEXT,
    cached_video_path TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Segments table
CREATE TABLE segments (
    id TEXT PRIMARY KEY,              -- UUID
    song_id TEXT NOT NULL REFERENCES songs(id),
    start_time REAL NOT NULL,         -- seconds
    end_time REAL NOT NULL,           -- seconds
    duration REAL NOT NULL,           -- computed
    energy_score REAL NOT NULL,
    is_primary INTEGER DEFAULT 0,     -- boolean
    label TEXT,                       -- 'chorus_1', 'drop', etc.
    cached_clip_path TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Playlists table
CREATE TABLE playlists (
    id TEXT PRIMARY KEY,              -- UUID
    name TEXT NOT NULL,
    target_duration INTEGER DEFAULT 2700,  -- 45 min
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Playlist items (join table)
CREATE TABLE playlist_items (
    id TEXT PRIMARY KEY,              -- UUID
    playlist_id TEXT NOT NULL REFERENCES playlists(id),
    segment_id TEXT NOT NULL REFERENCES segments(id),
    position INTEGER NOT NULL,
    crossfade_duration REAL DEFAULT 2.0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(playlist_id, position)
);

-- Export jobs table
CREATE TABLE export_jobs (
    id TEXT PRIMARY KEY,              -- UUID
    playlist_id TEXT NOT NULL REFERENCES playlists(id),
    status TEXT DEFAULT 'queued',
    progress INTEGER DEFAULT 0,
    output_path TEXT,
    output_format TEXT DEFAULT 'mp4',
    resolution TEXT DEFAULT '1080p',
    started_at TEXT,
    completed_at TEXT,
    error_message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_songs_language ON songs(language);
CREATE INDEX idx_songs_status ON songs(analysis_status);
CREATE INDEX idx_segments_song ON segments(song_id);
CREATE INDEX idx_playlist_items_playlist ON playlist_items(playlist_id);
CREATE INDEX idx_export_jobs_playlist ON export_jobs(playlist_id);
```

---

## 5. API Endpoints

### 5.1 Songs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/songs` | List all songs (with filters) |
| GET | `/api/songs/{id}` | Get single song |
| POST | `/api/discover` | Trigger discovery for all languages |
| POST | `/api/analyze/{song_id}` | Queue song for analysis |
| DELETE | `/api/songs/{id}` | Remove song from cache |

**GET /api/songs Query Params:**
- `language`: Filter by language
- `status`: Filter by analysis_status
- `sort`: `energy`, `bpm`, `title`, `created_at`

### 5.2 Segments

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/segments/{song_id}` | Get segments for a song |
| GET | `/api/segments/{id}/preview` | Get preview URL for segment |

### 5.3 Playlists

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/playlists` | List all playlists |
| POST | `/api/playlists` | Create new playlist |
| GET | `/api/playlists/{id}` | Get playlist with items |
| PUT | `/api/playlists/{id}` | Update playlist metadata |
| DELETE | `/api/playlists/{id}` | Delete playlist |
| POST | `/api/playlists/{id}/items` | Add segment to playlist |
| PUT | `/api/playlists/{id}/items` | Reorder items |
| DELETE | `/api/playlists/{id}/items/{item_id}` | Remove item |
| POST | `/api/playlists/{id}/auto-sequence` | Auto-sort by BPM/energy |

### 5.4 Export

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/export` | Start export job |
| GET | `/api/export/{job_id}` | Get job status/progress |
| DELETE | `/api/export/{job_id}` | Cancel export job |

---

## 6. Key Algorithms

### 6.1 Energy Calculation

```python
def calculate_energy_curve(audio_path: str) -> np.ndarray:
    """
    Compute composite energy score across time.
    Returns array of energy values (0-1) per audio frame.
    """
    y, sr = librosa.load(audio_path, sr=22050)
    
    # Volume envelope (how loud)
    rms = librosa.feature.rms(y=y)[0]
    
    # Spectral centroid (how bright/exciting)
    spectral = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    
    # Onset strength (how punchy/rhythmic)
    onset = librosa.onset.onset_strength(y=y, sr=sr)
    
    # Normalize each to 0-1
    rms_norm = (rms - rms.min()) / (rms.max() - rms.min() + 1e-8)
    spec_norm = (spectral - spectral.min()) / (spectral.max() - spectral.min() + 1e-8)
    onset_norm = (onset - onset.min()) / (onset.max() - onset.min() + 1e-8)
    
    # Resample to same length
    length = min(len(rms_norm), len(spec_norm), len(onset_norm))
    
    # Weighted combination
    energy = (
        0.4 * rms_norm[:length] +
        0.3 * spec_norm[:length] +
        0.3 * onset_norm[:length]
    )
    
    return energy
```

### 6.2 Segment Detection

```python
def find_segments(
    energy: np.ndarray,
    sr: int,
    hop_length: int = 512,
    min_duration: int = 45,
    max_duration: int = 90,
    max_segments: int = 3,
    min_gap: int = 30
) -> list[dict]:
    """
    Find high-energy windows in the song.
    Returns list of {start_time, end_time, energy_score}.
    """
    frames_per_second = sr / hop_length
    min_frames = int(min_duration * frames_per_second)
    max_frames = int(max_duration * frames_per_second)
    gap_frames = int(min_gap * frames_per_second)
    
    # Sliding window analysis
    candidates = []
    for window_size in range(min_frames, max_frames + 1, min_frames // 2):
        for start in range(0, len(energy) - window_size, window_size // 4):
            end = start + window_size
            window_energy = np.mean(energy[start:end])
            candidates.append({
                'start_frame': start,
                'end_frame': end,
                'energy': window_energy
            })
    
    # Sort by energy (highest first)
    candidates.sort(key=lambda x: x['energy'], reverse=True)
    
    # Select non-overlapping segments
    selected = []
    for candidate in candidates:
        if len(selected) >= max_segments:
            break
        
        # Check for overlap with already selected
        overlaps = False
        for seg in selected:
            if not (candidate['end_frame'] + gap_frames < seg['start_frame'] or
                    candidate['start_frame'] - gap_frames > seg['end_frame']):
                overlaps = True
                break
        
        if not overlaps:
            selected.append(candidate)
    
    # Convert to time and sort by position
    segments = []
    for i, seg in enumerate(sorted(selected, key=lambda x: x['start_frame'])):
        segments.append({
            'start_time': seg['start_frame'] / frames_per_second,
            'end_time': seg['end_frame'] / frames_per_second,
            'duration': (seg['end_frame'] - seg['start_frame']) / frames_per_second,
            'energy_score': seg['energy'] * 100,
            'is_primary': i == 0,
            'label': f'segment_{i + 1}'
        })
    
    return segments
```

### 6.3 Auto-Sequencing

```python
def auto_sequence_playlist(
    items: list[PlaylistItem],
    strategy: str = 'energy_arc'
) -> list[PlaylistItem]:
    """
    Reorder playlist items for optimal flow.
    Strategies: 'bpm', 'energy_arc', 'energy_high_to_low'
    """
    if strategy == 'bpm':
        # Sort by BPM for smooth tempo transitions
        return sorted(items, key=lambda x: x.segment.song.bpm or 0)
    
    elif strategy == 'energy_arc':
        # DJ-style energy arc: medium → high → peak → cooldown
        sorted_by_energy = sorted(items, key=lambda x: x.segment.energy_score)
        
        n = len(sorted_by_energy)
        if n < 4:
            return sorted_by_energy
        
        # Split into quartiles
        low = sorted_by_energy[:n//4]
        mid = sorted_by_energy[n//4:n//2]
        high = sorted_by_energy[n//2:3*n//4]
        peak = sorted_by_energy[3*n//4:]
        
        # Arrange: mid → high → peak → mid → low
        return mid + high + peak + mid[::-1] + low[::-1]
    
    elif strategy == 'energy_high_to_low':
        return sorted(items, key=lambda x: x.segment.energy_score, reverse=True)
    
    return items
```

---

## 7. FFmpeg Pipeline

### 7.1 Segment Download

```python
def download_segment(song_url: str, start: float, end: float, output_path: str):
    """Download specific video segment using yt-dlp."""
    ydl_opts = {
        'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
        'outtmpl': output_path,
        'download_ranges': lambda info, ydl: [{
            'start_time': start,
            'end_time': end
        }],
        'force_keyframes_at_cuts': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([song_url])
```

### 7.2 Audio Normalization

```python
def normalize_audio(input_path: str, output_path: str, target_lufs: float = -14.0):
    """Normalize audio to target LUFS."""
    # First pass: measure loudness
    measure_cmd = [
        'ffmpeg', '-i', input_path,
        '-af', 'loudnorm=I=-14:TP=-1:LRA=11:print_format=json',
        '-f', 'null', '-'
    ]
    result = subprocess.run(measure_cmd, capture_output=True, text=True)
    
    # Parse measured values and apply correction
    # ... (parse JSON from stderr)
    
    # Second pass: apply normalization
    normalize_cmd = [
        'ffmpeg', '-i', input_path,
        '-af', f'loudnorm=I={target_lufs}:TP=-1:LRA=11:measured_I=...',
        '-c:v', 'copy',
        output_path
    ]
    subprocess.run(normalize_cmd)
```

### 7.3 Crossfade Concatenation

```python
def create_crossfade_concat(
    segments: list[str],
    crossfade_duration: float,
    output_path: str,
    use_gpu: bool = False
):
    """Concatenate video segments with crossfade transitions."""
    
    if len(segments) == 1:
        shutil.copy(segments[0], output_path)
        return
    
    # Build filter complex
    filter_parts = []
    
    # Video crossfades
    for i in range(len(segments) - 1):
        if i == 0:
            prev = f'[0:v]'
        else:
            prev = f'[v{i-1}]'
        
        offset = sum(get_duration(s) for s in segments[:i+1]) - crossfade_duration * (i + 1)
        filter_parts.append(
            f'{prev}[{i+1}:v]xfade=transition=fade:duration={crossfade_duration}:offset={offset}[v{i}]'
        )
    
    # Audio crossfades
    for i in range(len(segments) - 1):
        if i == 0:
            prev = f'[0:a]'
        else:
            prev = f'[a{i-1}]'
        
        filter_parts.append(f'{prev}[{i+1}:a]acrossfade=d={crossfade_duration}[a{i}]')
    
    filter_complex = ';'.join(filter_parts)
    
    # Build command
    cmd = ['ffmpeg']
    for seg in segments:
        cmd.extend(['-i', seg])
    
    cmd.extend([
        '-filter_complex', filter_complex,
        '-map', f'[v{len(segments)-2}]',
        '-map', f'[a{len(segments)-2}]',
    ])
    
    # Encoder settings
    if use_gpu:
        cmd.extend(['-c:v', 'h264_nvenc', '-preset', 'p4', '-cq', '22'])
    else:
        cmd.extend(['-c:v', 'libx264', '-preset', 'fast', '-crf', '22'])
    
    cmd.extend(['-c:a', 'aac', '-b:a', '192k', output_path])
    
    subprocess.run(cmd)
```

---

## 8. Error Handling

### 8.1 Retry Strategy

| Operation | Max Retries | Backoff | Fallback |
|-----------|-------------|---------|----------|
| YouTube search | 3 | Exponential (1s, 2s, 4s) | Use cached results |
| Video download | 3 | Exponential | Skip song, mark failed |
| Audio analysis | 2 | Linear (5s) | Use default segments |
| FFmpeg encode | 2 | None | Report error to user |

### 8.2 Error States

```typescript
type AnalysisError = 
  | { code: 'DOWNLOAD_FAILED'; message: string; video_id: string }
  | { code: 'ANALYSIS_FAILED'; message: string; video_id: string }
  | { code: 'NO_SEGMENTS_FOUND'; video_id: string }
  | { code: 'VIDEO_TOO_SHORT'; video_id: string; duration: number }
  | { code: 'VIDEO_TOO_LONG'; video_id: string; duration: number };

type ExportError =
  | { code: 'FFMPEG_NOT_FOUND' }
  | { code: 'INSUFFICIENT_DISK_SPACE'; required: number; available: number }
  | { code: 'ENCODING_FAILED'; message: string; segment_index: number }
  | { code: 'CANCELLED_BY_USER' };
```

---

## 9. Performance Considerations

### 9.1 Parallel Processing

- **Discovery:** All 7 language searches run in parallel
- **Analysis:** Up to 4 songs analyzed concurrently (CPU-bound)
- **Download:** Up to 2 concurrent downloads (bandwidth-bound)
- **Export:** Single-threaded (FFmpeg handles internal parallelism)

### 9.2 Caching Strategy

| Asset | Cache Location | TTL | Size Estimate |
|-------|---------------|-----|---------------|
| Song metadata | SQLite | 7 days | ~1KB per song |
| Thumbnails | disk | 30 days | ~100KB per song |
| Audio (analysis) | disk | 7 days | ~5MB per song |
| Video segments | disk | 7 days | ~50MB per segment |

### 9.3 Memory Management

- Stream audio files in chunks for analysis (don't load full file)
- Release video segments from memory after encoding
- Use thumbnail previews, not full video, in grid view

---

## 10. Security Considerations

1. **No credentials stored:** YouTube access via public search only
2. **Sandboxed file access:** Tauri restricts file system to app directory
3. **Input validation:** All API inputs validated with Pydantic
4. **No remote code:** FFmpeg commands constructed safely, no user-provided commands
5. **Local only:** Python server binds to localhost only

---

*End of Architecture Document*
