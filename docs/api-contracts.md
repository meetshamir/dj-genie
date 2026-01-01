# API Contracts — Video DJ Playlist Creator

> **Version:** 1.0  
> **Base URL:** `http://localhost:9876/api`

---

## 1. Songs API

### 1.1 List Songs

```http
GET /songs
```

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `language` | string | - | Filter by language code |
| `status` | string | - | Filter by analysis_status |
| `sort` | string | `created_at` | Sort field: `energy`, `bpm`, `title`, `created_at` |
| `order` | string | `desc` | Sort order: `asc`, `desc` |

**Response: 200 OK**

```json
{
  "songs": [
    {
      "id": "dQw4w9WgXcQ",
      "title": "Song Title",
      "artist": "Artist Name",
      "language": "english",
      "duration": 213,
      "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
      "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "bpm": 128.5,
      "energy_score": 78.3,
      "analysis_status": "complete",
      "segment_count": 2,
      "created_at": "2025-12-31T10:00:00Z"
    }
  ],
  "total": 21,
  "languages": {
    "english": 3,
    "hindi": 3,
    "malayalam": 3,
    "tamil": 3,
    "turkish": 3,
    "uzbek": 3,
    "arabic": 3
  }
}
```

---

### 1.2 Get Single Song

```http
GET /songs/{song_id}
```

**Response: 200 OK**

```json
{
  "id": "dQw4w9WgXcQ",
  "title": "Song Title",
  "artist": "Artist Name",
  "language": "english",
  "duration": 213,
  "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
  "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "bpm": 128.5,
  "energy_score": 78.3,
  "analysis_status": "complete",
  "cached_audio_path": "/cache/audio/dQw4w9WgXcQ.mp3",
  "cached_video_path": null,
  "segments": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "start_time": 45.2,
      "end_time": 95.8,
      "duration": 50.6,
      "energy_score": 85.2,
      "is_primary": true,
      "label": "chorus_1"
    }
  ],
  "created_at": "2025-12-31T10:00:00Z",
  "updated_at": "2025-12-31T10:05:00Z"
}
```

**Response: 404 Not Found**

```json
{
  "error": "SONG_NOT_FOUND",
  "message": "Song with ID 'xyz' not found"
}
```

---

### 1.3 Trigger Discovery

```http
POST /discover
```

**Request Body:**

```json
{
  "languages": ["english", "hindi", "tamil"],
  "songs_per_language": 3,
  "force_refresh": false
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `languages` | string[] | all 7 | Languages to discover |
| `songs_per_language` | int | 3 | Songs to fetch per language |
| `force_refresh` | bool | false | Ignore cache, re-fetch |

**Response: 202 Accepted**

```json
{
  "status": "discovering",
  "languages": ["english", "hindi", "tamil"],
  "expected_songs": 9
}
```

---

### 1.4 Trigger Analysis

```http
POST /analyze/{song_id}
```

**Response: 202 Accepted**

```json
{
  "song_id": "dQw4w9WgXcQ",
  "status": "queued",
  "position_in_queue": 3
}
```

**Response: 409 Conflict** (already analyzing)

```json
{
  "error": "ALREADY_ANALYZING",
  "message": "Song is already being analyzed",
  "current_status": "analyzing"
}
```

---

### 1.5 Analyze All Pending

```http
POST /analyze-all
```

**Response: 202 Accepted**

```json
{
  "queued": 15,
  "already_complete": 6,
  "failed": 0
}
```

---

## 2. Segments API

### 2.1 Get Segments for Song

```http
GET /segments/{song_id}
```

**Response: 200 OK**

```json
{
  "song_id": "dQw4w9WgXcQ",
  "segments": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "start_time": 45.2,
      "end_time": 95.8,
      "duration": 50.6,
      "energy_score": 85.2,
      "is_primary": true,
      "label": "chorus_1",
      "cached_clip_path": null
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "start_time": 142.0,
      "end_time": 195.5,
      "duration": 53.5,
      "energy_score": 72.8,
      "is_primary": false,
      "label": "chorus_2",
      "cached_clip_path": null
    }
  ]
}
```

---

### 2.2 Get Segment Preview URL

```http
GET /segments/{segment_id}/preview
```

**Response: 200 OK**

```json
{
  "segment_id": "550e8400-e29b-41d4-a716-446655440000",
  "preview_type": "youtube_embed",
  "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "start_time": 45.2,
  "end_time": 95.8,
  "embed_url": "https://www.youtube.com/embed/dQw4w9WgXcQ?start=45&end=96&autoplay=1"
}
```

---

## 3. Playlists API

### 3.1 List Playlists

```http
GET /playlists
```

**Response: 200 OK**

```json
{
  "playlists": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440000",
      "name": "Party Mix 2025",
      "target_duration": 2700,
      "current_duration": 1250,
      "item_count": 18,
      "created_at": "2025-12-31T10:00:00Z",
      "updated_at": "2025-12-31T11:30:00Z"
    }
  ],
  "total": 1
}
```

---

### 3.2 Create Playlist

```http
POST /playlists
```

**Request Body:**

```json
{
  "name": "Party Mix 2025",
  "target_duration": 2700
}
```

**Response: 201 Created**

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440000",
  "name": "Party Mix 2025",
  "target_duration": 2700,
  "current_duration": 0,
  "item_count": 0,
  "items": [],
  "created_at": "2025-12-31T10:00:00Z",
  "updated_at": "2025-12-31T10:00:00Z"
}
```

---

### 3.3 Get Playlist

```http
GET /playlists/{playlist_id}
```

**Response: 200 OK**

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440000",
  "name": "Party Mix 2025",
  "target_duration": 2700,
  "current_duration": 1250,
  "item_count": 18,
  "items": [
    {
      "id": "770e8400-e29b-41d4-a716-446655440000",
      "position": 0,
      "crossfade_duration": 2.0,
      "segment": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "start_time": 45.2,
        "end_time": 95.8,
        "duration": 50.6,
        "energy_score": 85.2,
        "label": "chorus_1",
        "song": {
          "id": "dQw4w9WgXcQ",
          "title": "Song Title",
          "artist": "Artist Name",
          "language": "english",
          "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"
        }
      }
    }
  ],
  "created_at": "2025-12-31T10:00:00Z",
  "updated_at": "2025-12-31T11:30:00Z"
}
```

---

### 3.4 Update Playlist

```http
PUT /playlists/{playlist_id}
```

**Request Body:**

```json
{
  "name": "Updated Mix Name",
  "target_duration": 3600
}
```

**Response: 200 OK**

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440000",
  "name": "Updated Mix Name",
  "target_duration": 3600,
  "updated_at": "2025-12-31T12:00:00Z"
}
```

---

### 3.5 Delete Playlist

```http
DELETE /playlists/{playlist_id}
```

**Response: 204 No Content**

---

### 3.6 Add Item to Playlist

```http
POST /playlists/{playlist_id}/items
```

**Request Body:**

```json
{
  "segment_id": "550e8400-e29b-41d4-a716-446655440000",
  "position": null,
  "crossfade_duration": 2.0
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `segment_id` | string | required | Segment to add |
| `position` | int | null | Position (null = append to end) |
| `crossfade_duration` | float | 2.0 | Crossfade with next item |

**Response: 201 Created**

```json
{
  "id": "770e8400-e29b-41d4-a716-446655440001",
  "position": 18,
  "crossfade_duration": 2.0,
  "segment_id": "550e8400-e29b-41d4-a716-446655440000",
  "playlist_id": "660e8400-e29b-41d4-a716-446655440000"
}
```

---

### 3.7 Reorder Playlist Items

```http
PUT /playlists/{playlist_id}/items
```

**Request Body:**

```json
{
  "item_ids": [
    "770e8400-e29b-41d4-a716-446655440002",
    "770e8400-e29b-41d4-a716-446655440000",
    "770e8400-e29b-41d4-a716-446655440001"
  ]
}
```

**Response: 200 OK**

```json
{
  "reordered": 3
}
```

---

### 3.8 Remove Item from Playlist

```http
DELETE /playlists/{playlist_id}/items/{item_id}
```

**Response: 204 No Content**

---

### 3.9 Auto-Sequence Playlist

```http
POST /playlists/{playlist_id}/auto-sequence
```

**Request Body:**

```json
{
  "strategy": "energy_arc"
}
```

| Strategy | Description |
|----------|-------------|
| `bpm` | Sort by BPM (low to high) |
| `energy_arc` | DJ-style: medium → high → peak → cooldown |
| `energy_desc` | High energy first, fade out |

**Response: 200 OK**

```json
{
  "reordered": 18,
  "strategy": "energy_arc",
  "new_order": [
    "770e8400-e29b-41d4-a716-446655440005",
    "770e8400-e29b-41d4-a716-446655440002",
    ...
  ]
}
```

---

## 4. Export API

### 4.1 Start Export

```http
POST /export
```

**Request Body:**

```json
{
  "playlist_id": "660e8400-e29b-41d4-a716-446655440000",
  "format": "mp4",
  "resolution": "1080p",
  "crossfade_duration": 2.0,
  "fade_in": true,
  "fade_out": true
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `playlist_id` | string | required | Playlist to export |
| `format` | string | `mp4` | Output format: `mp4`, `webm`, `mov` |
| `resolution` | string | `1080p` | Output resolution: `1080p`, `720p` |
| `crossfade_duration` | float | 2.0 | Crossfade between clips (seconds) |
| `fade_in` | bool | true | Fade in at start |
| `fade_out` | bool | true | Fade out at end |

**Response: 202 Accepted**

```json
{
  "job_id": "880e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "playlist_id": "660e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-12-31T12:00:00Z"
}
```

---

### 4.2 Get Export Status

```http
GET /export/{job_id}
```

**Response: 200 OK (In Progress)**

```json
{
  "job_id": "880e8400-e29b-41d4-a716-446655440000",
  "status": "encoding",
  "progress": 45,
  "current_step": "Processing segment 8 of 18",
  "steps": [
    { "name": "Downloading segments", "status": "complete" },
    { "name": "Normalizing audio", "status": "complete" },
    { "name": "Encoding video", "status": "in_progress", "progress": 45 },
    { "name": "Finalizing", "status": "pending" }
  ],
  "started_at": "2025-12-31T12:00:05Z",
  "elapsed_seconds": 154,
  "estimated_remaining_seconds": 188
}
```

**Response: 200 OK (Complete)**

```json
{
  "job_id": "880e8400-e29b-41d4-a716-446655440000",
  "status": "complete",
  "progress": 100,
  "output_path": "C:/Users/saziz/video-dj-playlist/exports/Party_Mix_2025.mp4",
  "output_size_bytes": 524288000,
  "duration_seconds": 2700,
  "started_at": "2025-12-31T12:00:05Z",
  "completed_at": "2025-12-31T12:08:45Z",
  "elapsed_seconds": 520
}
```

**Response: 200 OK (Failed)**

```json
{
  "job_id": "880e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "progress": 67,
  "error": {
    "code": "ENCODING_FAILED",
    "message": "FFmpeg error: unable to decode segment 12",
    "segment_index": 12
  },
  "started_at": "2025-12-31T12:00:05Z",
  "failed_at": "2025-12-31T12:05:30Z"
}
```

---

### 4.3 Cancel Export

```http
DELETE /export/{job_id}
```

**Response: 200 OK**

```json
{
  "job_id": "880e8400-e29b-41d4-a716-446655440000",
  "status": "cancelled",
  "cancelled_at": "2025-12-31T12:03:00Z"
}
```

**Response: 409 Conflict** (already complete)

```json
{
  "error": "CANNOT_CANCEL",
  "message": "Export job has already completed"
}
```

---

## 5. Preferences API

### 5.1 Get Preferences

```http
GET /preferences
```

**Response: 200 OK**

```json
{
  "discovery": {
    "enabled_languages": ["english", "hindi", "malayalam", "tamil", "turkish", "uzbek", "arabic"],
    "songs_per_language": 3,
    "include_remixes": false
  },
  "analysis": {
    "min_segment_duration": 45,
    "max_segment_duration": 90,
    "max_segments_per_song": 3
  },
  "export": {
    "target_playlist_duration": 2700,
    "crossfade_duration": 2,
    "output_format": "mp4",
    "output_resolution": "1080p",
    "use_gpu_acceleration": true
  },
  "ui": {
    "auto_play_on_hover": true,
    "hover_volume": 0.3
  }
}
```

---

### 5.2 Update Preferences

```http
PUT /preferences
```

**Request Body:** (partial update supported)

```json
{
  "discovery": {
    "songs_per_language": 50
  },
  "export": {
    "output_resolution": "720p"
  }
}
```

**Response: 200 OK**

```json
{
  "updated": ["discovery.songs_per_language", "export.output_resolution"]
}
```

---

## 6. System API

### 6.1 Health Check

```http
GET /health
```

**Response: 200 OK**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "ffmpeg_installed": true,
  "ffmpeg_version": "6.1",
  "gpu_available": true,
  "gpu_encoder": "nvenc",
  "disk_space_available_gb": 125.4,
  "cache_size_mb": 342.5
}
```

---

### 6.2 Clear Cache

```http
POST /cache/clear
```

**Request Body:**

```json
{
  "types": ["audio", "video", "thumbnails"]
}
```

**Response: 200 OK**

```json
{
  "cleared": {
    "audio": { "files": 21, "size_mb": 105.2 },
    "video": { "files": 45, "size_mb": 2250.0 },
    "thumbnails": { "files": 21, "size_mb": 2.1 }
  },
  "total_freed_mb": 2357.3
}
```

---

## 7. Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `SONG_NOT_FOUND` | 404 | Song ID doesn't exist |
| `SEGMENT_NOT_FOUND` | 404 | Segment ID doesn't exist |
| `PLAYLIST_NOT_FOUND` | 404 | Playlist ID doesn't exist |
| `EXPORT_JOB_NOT_FOUND` | 404 | Export job ID doesn't exist |
| `ALREADY_ANALYZING` | 409 | Song is already being analyzed |
| `CANNOT_CANCEL` | 409 | Export already complete/failed |
| `FFMPEG_NOT_FOUND` | 500 | FFmpeg not installed |
| `DOWNLOAD_FAILED` | 502 | Failed to download from YouTube |
| `ANALYSIS_FAILED` | 500 | Audio analysis failed |
| `ENCODING_FAILED` | 500 | FFmpeg encoding failed |
| `INSUFFICIENT_DISK_SPACE` | 507 | Not enough disk space |

---

## 8. WebSocket Events (Future)

For real-time updates, a WebSocket endpoint will be added:

```
WS /ws
```

**Events:**

```json
// Song analysis progress
{
  "event": "analysis_progress",
  "song_id": "dQw4w9WgXcQ",
  "status": "analyzing",
  "progress": 65
}

// Export progress
{
  "event": "export_progress",
  "job_id": "880e8400-e29b-41d4-a716-446655440000",
  "progress": 45,
  "current_step": "Encoding segment 8/18"
}

// Discovery complete
{
  "event": "discovery_complete",
  "songs_added": 21
}
```

---

*End of API Contracts*
