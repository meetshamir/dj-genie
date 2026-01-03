"""
Pydantic schemas for API request/response validation.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ============== Song Schemas ==============

class SongBase(BaseModel):
    """Base song schema."""
    title: str
    artist: Optional[str] = None
    language: str
    duration: int
    thumbnail_url: Optional[str] = None
    youtube_url: str


class SongCreate(SongBase):
    """Schema for creating a song."""
    id: str  # YouTube video ID


class SegmentBrief(BaseModel):
    """Brief segment info for song responses."""
    id: str
    start_time: float
    end_time: float
    duration: float
    energy_score: float
    is_primary: bool
    label: Optional[str] = None
    
    class Config:
        from_attributes = True


class SongResponse(SongBase):
    """Schema for song response."""
    id: str
    bpm: Optional[float] = None
    energy_score: Optional[float] = None
    analysis_status: str
    segment_count: int = 0
    created_at: str
    
    class Config:
        from_attributes = True


class SongDetailResponse(SongResponse):
    """Schema for detailed song response with segments."""
    segments: List[SegmentBrief] = []
    cached_audio_path: Optional[str] = None
    cached_video_path: Optional[str] = None
    updated_at: str
    
    class Config:
        from_attributes = True


class SongListResponse(BaseModel):
    """Schema for song list response."""
    songs: List[SongResponse]
    total: int
    languages: dict[str, int]


# ============== Segment Schemas ==============

class SegmentResponse(BaseModel):
    """Schema for segment response."""
    id: str
    song_id: str
    start_time: float
    end_time: float
    duration: float
    energy_score: float
    is_primary: bool
    label: Optional[str] = None
    cached_clip_path: Optional[str] = None
    
    class Config:
        from_attributes = True


class SegmentListResponse(BaseModel):
    """Schema for segment list response."""
    song_id: str
    segments: List[SegmentResponse]


class SegmentPreviewResponse(BaseModel):
    """Schema for segment preview URL response."""
    segment_id: str
    preview_type: str = "youtube_embed"
    youtube_url: str
    start_time: float
    end_time: float
    embed_url: str


# ============== Discovery Schemas ==============

class DiscoverRequest(BaseModel):
    """Schema for discovery request."""
    languages: Optional[List[str]] = None  # None = all languages
    songs_per_language: int = 3
    force_refresh: bool = False


class DiscoverResponse(BaseModel):
    """Schema for discovery response."""
    status: str
    languages: List[str]
    expected_songs: int


# ============== Analysis Schemas ==============

class AnalyzeResponse(BaseModel):
    """Schema for analyze response."""
    song_id: str
    status: str
    bpm: Optional[float] = None
    energy_score: Optional[float] = None
    segments_found: int = 0


class AnalyzeSongResult(BaseModel):
    """Individual song analysis result."""
    id: str
    title: str
    language: str
    status: str
    bpm: Optional[float] = None
    segments: Optional[int] = None
    error: Optional[str] = None


class AnalyzeAllResponse(BaseModel):
    """Schema for analyze-all response."""
    total: int
    success: int
    failed: int
    songs: List[AnalyzeSongResult] = []


# ============== Playlist Schemas ==============

class PlaylistItemBrief(BaseModel):
    """Brief playlist item for list responses."""
    id: str
    position: int
    crossfade_duration: float
    segment: SegmentBrief
    song_title: str
    song_artist: Optional[str]
    song_language: str
    song_thumbnail: Optional[str]
    
    class Config:
        from_attributes = True


class PlaylistBase(BaseModel):
    """Base playlist schema."""
    name: str
    target_duration: int = 2700


class PlaylistCreate(PlaylistBase):
    """Schema for creating a playlist."""
    segment_ids: Optional[List[str]] = None  # Optional list of segment IDs to add immediately


class PlaylistResponse(PlaylistBase):
    """Schema for playlist response."""
    id: str
    current_duration: float = 0
    item_count: int = 0
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class PlaylistDetailResponse(PlaylistResponse):
    """Schema for detailed playlist response."""
    items: List[PlaylistItemBrief] = []
    
    class Config:
        from_attributes = True


class PlaylistListResponse(BaseModel):
    """Schema for playlist list response."""
    playlists: List[PlaylistResponse]
    total: int


class AddPlaylistItemRequest(BaseModel):
    """Schema for adding item to playlist."""
    segment_id: str
    position: Optional[int] = None  # None = append to end
    crossfade_duration: float = 2.0


class AddPlaylistItemResponse(BaseModel):
    """Schema for add item response."""
    id: str
    position: int
    crossfade_duration: float
    segment_id: str
    playlist_id: str


class ReorderPlaylistRequest(BaseModel):
    """Schema for reordering playlist items."""
    item_ids: List[str]


class ReorderPlaylistResponse(BaseModel):
    """Schema for reorder response."""
    reordered: int


class AutoSequenceRequest(BaseModel):
    """Schema for auto-sequence request."""
    strategy: str = "energy_arc"  # bpm, energy_arc, energy_desc


class AutoSequenceResponse(BaseModel):
    """Schema for auto-sequence response."""
    reordered: int
    strategy: str
    new_order: List[str]


# ============== Export Schemas ==============

class ExportRequest(BaseModel):
    """Schema for export request."""
    playlist_id: str
    format: str = "mp4"
    resolution: str = "1080p"
    crossfade_duration: float = 2.0
    fade_in: bool = True
    fade_out: bool = True


class ExportJobResponse(BaseModel):
    """Schema for export job response."""
    job_id: str
    status: str
    playlist_id: str
    progress: int = 0
    current_step: Optional[str] = None
    output_path: Optional[str] = None
    output_size_bytes: Optional[int] = None
    duration_seconds: Optional[int] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    elapsed_seconds: Optional[int] = None
    estimated_remaining_seconds: Optional[int] = None
    error: Optional[dict] = None
    created_at: str
    
    class Config:
        from_attributes = True


# ============== System Schemas ==============

class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str
    version: str
    ffmpeg_installed: bool
    ffmpeg_version: Optional[str] = None
    gpu_available: bool
    gpu_encoder: Optional[str] = None
    disk_space_available_gb: float
    cache_size_mb: float
    openai_available: bool = False
    openai_error: Optional[str] = None


class ClearCacheRequest(BaseModel):
    """Schema for cache clear request."""
    types: List[str] = ["audio", "video", "thumbnails"]


class ClearCacheResponse(BaseModel):
    """Schema for cache clear response."""
    cleared: dict
    total_freed_mb: float


# ============== Error Schemas ==============

class ErrorResponse(BaseModel):
    """Schema for error responses."""
    error: str
    message: str
    details: Optional[dict] = None

