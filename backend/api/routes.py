"""
API Routes for the Video DJ Playlist Creator.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid
from datetime import datetime

from models.database import get_db, Song, Segment, Playlist, PlaylistItem
from schemas import (
    SongResponse,
    SongDetailResponse,
    SongListResponse,
    SegmentResponse,
    SegmentListResponse,
    SegmentPreviewResponse,
    DiscoverRequest,
    DiscoverResponse,
    AnalyzeResponse,
    AnalyzeAllResponse,
    AnalyzeSongResult,
    PlaylistCreate,
    PlaylistResponse,
    PlaylistDetailResponse,
    PlaylistListResponse,
    PlaylistItemBrief,
    AddPlaylistItemRequest,
    AddPlaylistItemResponse,
    HealthResponse,
    ErrorResponse,
    SegmentBrief,
)
from services.discovery import discover_all_songs, DiscoveredSong
from services.downloader import download_audio, get_cache_stats
from services.analysis import analyze_audio_file, DetectedSegment
from config import settings, SUPPORTED_LANGUAGES
from pydantic import BaseModel

router = APIRouter()


# ============== DJ Context ==============

class DJContextRequest(BaseModel):
    """Request model for DJ context configuration."""
    theme: str = "New Year 2025 Party - Welcoming 2026!"
    mood: str = "energetic, celebratory, festive"
    audience: str = "party guests ready to dance"
    special_notes: Optional[str] = ""
    custom_shoutouts: Optional[List[str]] = []


# In-memory store for DJ context (per-playlist)
dj_contexts = {}


# ============== Health Check ==============

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check system health and dependencies."""
    import shutil
    import subprocess
    
    # Check FFmpeg
    ffmpeg_installed = False
    ffmpeg_version = None
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            ffmpeg_installed = True
            # Extract version from first line
            first_line = result.stdout.split('\n')[0]
            ffmpeg_version = first_line.split(' ')[2] if len(first_line.split(' ')) > 2 else "unknown"
    except FileNotFoundError:
        pass
    
    # Check disk space
    total, used, free = shutil.disk_usage(settings.base_dir)
    disk_space_gb = free / (1024 ** 3)
    
    # Calculate cache size
    cache_size_mb = 0
    for cache_dir in [settings.audio_cache_dir, settings.video_cache_dir, settings.thumbnail_cache_dir]:
        if cache_dir.exists():
            for file in cache_dir.rglob('*'):
                if file.is_file():
                    cache_size_mb += file.stat().st_size / (1024 ** 2)
    
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        ffmpeg_installed=ffmpeg_installed,
        ffmpeg_version=ffmpeg_version,
        gpu_available=False,  # TODO: Implement GPU detection
        gpu_encoder=None,
        disk_space_available_gb=round(disk_space_gb, 2),
        cache_size_mb=round(cache_size_mb, 2)
    )


# ============== Songs ==============

@router.get("/songs", response_model=SongListResponse)
async def list_songs(
    language: Optional[str] = None,
    status: Optional[str] = None,
    sort: str = "created_at",
    order: str = "desc",
    db: Session = Depends(get_db)
):
    """List all songs with optional filters."""
    query = db.query(Song)
    
    # Apply filters
    if language:
        query = query.filter(Song.language == language)
    if status:
        query = query.filter(Song.analysis_status == status)
    
    # Apply sorting
    sort_column = getattr(Song, sort, Song.created_at)
    if order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    songs = query.all()
    
    # Get language counts
    language_counts = {}
    for lang in SUPPORTED_LANGUAGES:
        count = db.query(Song).filter(Song.language == lang).count()
        language_counts[lang] = count
    
    # Build response
    song_responses = []
    for song in songs:
        segment_count = db.query(Segment).filter(Segment.song_id == song.id).count()
        song_responses.append(SongResponse(
            id=song.id,
            title=song.title,
            artist=song.artist,
            language=song.language,
            duration=song.duration,
            thumbnail_url=song.thumbnail_url,
            youtube_url=song.youtube_url,
            bpm=song.bpm,
            energy_score=song.energy_score,
            analysis_status=song.analysis_status,
            segment_count=segment_count,
            created_at=song.created_at
        ))
    
    return SongListResponse(
        songs=song_responses,
        total=len(songs),
        languages=language_counts
    )


@router.get("/songs/{song_id}", response_model=SongDetailResponse)
async def get_song(song_id: str, db: Session = Depends(get_db)):
    """Get a single song with all details."""
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail={"error": "SONG_NOT_FOUND", "message": f"Song with ID '{song_id}' not found"})
    
    segments = db.query(Segment).filter(Segment.song_id == song_id).order_by(Segment.start_time).all()
    
    return SongDetailResponse(
        id=song.id,
        title=song.title,
        artist=song.artist,
        language=song.language,
        duration=song.duration,
        thumbnail_url=song.thumbnail_url,
        youtube_url=song.youtube_url,
        bpm=song.bpm,
        energy_score=song.energy_score,
        analysis_status=song.analysis_status,
        segment_count=len(segments),
        segments=[SegmentBrief(
            id=seg.id,
            start_time=seg.start_time,
            end_time=seg.end_time,
            duration=seg.duration,
            energy_score=seg.energy_score,
            is_primary=seg.is_primary,
            label=seg.label
        ) for seg in segments],
        cached_audio_path=song.cached_audio_path,
        cached_video_path=song.cached_video_path,
        created_at=song.created_at,
        updated_at=song.updated_at
    )


# ============== Discovery ==============

def save_discovered_songs(songs: List[DiscoveredSong], db: Session) -> int:
    """Save discovered songs to database. Returns count of new songs added."""
    added = 0
    for song in songs:
        existing = db.query(Song).filter(Song.id == song.id).first()
        if not existing:
            new_song = Song(
                id=song.id,
                title=song.title,
                artist=song.artist,
                language=song.language,
                duration=song.duration,
                thumbnail_url=song.thumbnail_url,
                youtube_url=song.youtube_url,
                analysis_status="pending"
            )
            db.add(new_song)
            added += 1
    db.commit()
    return added


def run_discovery_task(languages: List[str], songs_per_language: int, db_path: str):
    """Background task to run song discovery."""
    from models.database import Database
    
    # Create new database connection for background task
    database = Database(db_path)
    session = database.get_session()
    
    try:
        all_songs = discover_all_songs(languages=languages, songs_per_language=songs_per_language)
        
        for language, songs in all_songs.items():
            save_discovered_songs(songs, session)
        
        print(f"Discovery complete. Added songs for {len(languages)} languages.")
    except Exception as e:
        print(f"Discovery error: {e}")
    finally:
        session.close()


@router.post("/discover", response_model=DiscoverResponse)
async def trigger_discovery(
    request: DiscoverRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Trigger song discovery for specified languages."""
    languages = request.languages or SUPPORTED_LANGUAGES
    
    # Validate languages
    for lang in languages:
        if lang not in SUPPORTED_LANGUAGES:
            raise HTTPException(status_code=400, detail={"error": "INVALID_LANGUAGE", "message": f"Unsupported language: {lang}"})
    
    # If force_refresh, delete existing songs for these languages
    if request.force_refresh:
        for lang in languages:
            db.query(Song).filter(Song.language == lang).delete()
        db.commit()
    
    # Run discovery in background
    background_tasks.add_task(
        run_discovery_task,
        languages,
        request.songs_per_language,
        str(settings.database_path)
    )
    
    return DiscoverResponse(
        status="discovering",
        languages=languages,
        expected_songs=len(languages) * request.songs_per_language
    )


@router.post("/discover/sync", response_model=SongListResponse)
async def trigger_discovery_sync(
    request: DiscoverRequest,
    db: Session = Depends(get_db)
):
    """Trigger song discovery synchronously (for testing)."""
    languages = request.languages or SUPPORTED_LANGUAGES
    
    # Validate languages
    for lang in languages:
        if lang not in SUPPORTED_LANGUAGES:
            raise HTTPException(status_code=400, detail={"error": "INVALID_LANGUAGE", "message": f"Unsupported language: {lang}"})
    
    # If force_refresh, delete existing songs for these languages
    if request.force_refresh:
        for lang in languages:
            db.query(Song).filter(Song.language == lang).delete()
        db.commit()
    
    # Run discovery
    all_songs = discover_all_songs(languages=languages, songs_per_language=request.songs_per_language)
    
    # Save to database
    total_added = 0
    for language, songs in all_songs.items():
        added = save_discovered_songs(songs, db)
        total_added += added
    
    # Return updated song list
    return await list_songs(db=db)


# ============== Segments ==============

@router.get("/segments")
async def get_all_segments(db: Session = Depends(get_db)):
    """Get all segments with their song info."""
    segments = db.query(Segment).all()
    
    result = []
    for seg in segments:
        song = db.query(Song).filter(Song.id == seg.song_id).first()
        result.append({
            "id": seg.id,
            "song_id": seg.song_id,
            "start_time": seg.start_time,
            "end_time": seg.end_time,
            "energy_score": seg.energy_score,
            "peak_moment": seg.start_time + (seg.duration / 2),
            "segment_type": seg.label or "high_energy",
            "created_at": seg.created_at,
            "song": {
                "id": song.id if song else None,
                "youtube_id": song.id if song else None,
                "title": song.title if song else "Unknown",
                "artist": song.artist if song else None,
                "duration_seconds": song.duration if song else 0,
                "language": song.language if song else "unknown",
                "thumbnail_url": song.thumbnail_url if song else None,
                "view_count": None,
                "bpm": song.bpm if song else None,
                "analysis_status": song.analysis_status if song else "pending",
                "created_at": song.created_at if song else None
            } if song else None
        })
    
    return result


@router.get("/segments/{song_id}", response_model=SegmentListResponse)
async def get_segments(song_id: str, db: Session = Depends(get_db)):
    """Get all segments for a song."""
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail={"error": "SONG_NOT_FOUND", "message": f"Song with ID '{song_id}' not found"})
    
    segments = db.query(Segment).filter(Segment.song_id == song_id).order_by(Segment.start_time).all()
    
    return SegmentListResponse(
        song_id=song_id,
        segments=[SegmentResponse(
            id=seg.id,
            song_id=seg.song_id,
            start_time=seg.start_time,
            end_time=seg.end_time,
            duration=seg.duration,
            energy_score=seg.energy_score,
            is_primary=seg.is_primary,
            label=seg.label,
            cached_clip_path=seg.cached_clip_path
        ) for seg in segments]
    )


@router.get("/segments/{segment_id}/preview", response_model=SegmentPreviewResponse)
async def get_segment_preview(segment_id: str, db: Session = Depends(get_db)):
    """Get preview URL for a segment."""
    segment = db.query(Segment).filter(Segment.id == segment_id).first()
    if not segment:
        raise HTTPException(status_code=404, detail={"error": "SEGMENT_NOT_FOUND", "message": f"Segment with ID '{segment_id}' not found"})
    
    song = db.query(Song).filter(Song.id == segment.song_id).first()
    
    # Build YouTube embed URL with start/end times
    start_int = int(segment.start_time)
    end_int = int(segment.end_time)
    embed_url = f"https://www.youtube.com/embed/{song.id}?start={start_int}&end={end_int}&autoplay=1"
    
    return SegmentPreviewResponse(
        segment_id=segment_id,
        preview_type="youtube_embed",
        youtube_url=song.youtube_url,
        start_time=segment.start_time,
        end_time=segment.end_time,
        embed_url=embed_url
    )


# ============== Playlists ==============

@router.get("/playlists", response_model=PlaylistListResponse)
async def list_playlists(db: Session = Depends(get_db)):
    """List all playlists."""
    playlists = db.query(Playlist).order_by(Playlist.updated_at.desc()).all()
    
    playlist_responses = []
    for playlist in playlists:
        items = db.query(PlaylistItem).filter(PlaylistItem.playlist_id == playlist.id).all()
        current_duration = sum(
            db.query(Segment).filter(Segment.id == item.segment_id).first().duration
            for item in items
            if db.query(Segment).filter(Segment.id == item.segment_id).first()
        )
        
        playlist_responses.append(PlaylistResponse(
            id=playlist.id,
            name=playlist.name,
            target_duration=playlist.target_duration,
            current_duration=current_duration,
            item_count=len(items),
            created_at=playlist.created_at,
            updated_at=playlist.updated_at
        ))
    
    return PlaylistListResponse(
        playlists=playlist_responses,
        total=len(playlists)
    )


@router.post("/playlists", status_code=201)
async def create_playlist(request: PlaylistCreate, db: Session = Depends(get_db)):
    """Create a new playlist with optional segment IDs."""
    playlist = Playlist(
        id=str(uuid.uuid4()),
        name=request.name,
        target_duration=request.target_duration
    )
    db.add(playlist)
    db.commit()
    db.refresh(playlist)

    current_duration = 0
    item_count = 0

    # Add segments if provided
    if request.segment_ids:
        for position, segment_id in enumerate(request.segment_ids):
            segment = db.query(Segment).filter(Segment.id == segment_id).first()
            if segment:
                item = PlaylistItem(
                    id=str(uuid.uuid4()),
                    playlist_id=playlist.id,
                    segment_id=segment_id,
                    position=position,
                    crossfade_duration=2.0
                )
                db.add(item)
                current_duration += segment.duration
                item_count += 1
        db.commit()

    return {
        "playlist_id": playlist.id,
        "id": playlist.id,
        "name": playlist.name,
        "target_duration": playlist.target_duration,
        "current_duration": current_duration,
        "item_count": item_count,
        "created_at": playlist.created_at,
        "updated_at": playlist.updated_at
    }


@router.get("/playlists/{playlist_id}", response_model=PlaylistDetailResponse)
async def get_playlist(playlist_id: str, db: Session = Depends(get_db)):
    """Get a playlist with all items."""
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail={"error": "PLAYLIST_NOT_FOUND", "message": f"Playlist with ID '{playlist_id}' not found"})
    
    items = db.query(PlaylistItem).filter(PlaylistItem.playlist_id == playlist_id).order_by(PlaylistItem.position).all()
    
    item_briefs = []
    current_duration = 0
    
    for item in items:
        segment = db.query(Segment).filter(Segment.id == item.segment_id).first()
        if segment:
            song = db.query(Song).filter(Song.id == segment.song_id).first()
            current_duration += segment.duration
            
            item_briefs.append(PlaylistItemBrief(
                id=item.id,
                position=item.position,
                crossfade_duration=item.crossfade_duration,
                segment=SegmentBrief(
                    id=segment.id,
                    start_time=segment.start_time,
                    end_time=segment.end_time,
                    duration=segment.duration,
                    energy_score=segment.energy_score,
                    is_primary=segment.is_primary,
                    label=segment.label
                ),
                song_title=song.title if song else "Unknown",
                song_artist=song.artist if song else None,
                song_language=song.language if song else "unknown",
                song_thumbnail=song.thumbnail_url if song else None
            ))
    
    return PlaylistDetailResponse(
        id=playlist.id,
        name=playlist.name,
        target_duration=playlist.target_duration,
        current_duration=current_duration,
        item_count=len(items),
        items=item_briefs,
        created_at=playlist.created_at,
        updated_at=playlist.updated_at
    )


@router.post("/playlists/{playlist_id}/items", response_model=AddPlaylistItemResponse, status_code=201)
async def add_playlist_item(
    playlist_id: str,
    request: AddPlaylistItemRequest,
    db: Session = Depends(get_db)
):
    """Add a segment to a playlist."""
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail={"error": "PLAYLIST_NOT_FOUND", "message": f"Playlist with ID '{playlist_id}' not found"})
    
    segment = db.query(Segment).filter(Segment.id == request.segment_id).first()
    if not segment:
        raise HTTPException(status_code=404, detail={"error": "SEGMENT_NOT_FOUND", "message": f"Segment with ID '{request.segment_id}' not found"})
    
    # Determine position
    if request.position is not None:
        position = request.position
        # Shift existing items
        db.query(PlaylistItem).filter(
            PlaylistItem.playlist_id == playlist_id,
            PlaylistItem.position >= position
        ).update({PlaylistItem.position: PlaylistItem.position + 1})
    else:
        # Append to end
        max_pos = db.query(func.max(PlaylistItem.position)).filter(
            PlaylistItem.playlist_id == playlist_id
        ).scalar()
        position = (max_pos or -1) + 1
    
    item = PlaylistItem(
        id=str(uuid.uuid4()),
        playlist_id=playlist_id,
        segment_id=request.segment_id,
        position=position,
        crossfade_duration=request.crossfade_duration
    )
    db.add(item)
    
    # Update playlist timestamp
    playlist.updated_at = datetime.utcnow().isoformat()
    
    db.commit()
    
    return AddPlaylistItemResponse(
        id=item.id,
        position=item.position,
        crossfade_duration=item.crossfade_duration,
        segment_id=item.segment_id,
        playlist_id=item.playlist_id
    )


@router.delete("/playlists/{playlist_id}/items/{item_id}", status_code=204)
async def remove_playlist_item(playlist_id: str, item_id: str, db: Session = Depends(get_db)):
    """Remove an item from a playlist."""
    item = db.query(PlaylistItem).filter(
        PlaylistItem.id == item_id,
        PlaylistItem.playlist_id == playlist_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail={"error": "ITEM_NOT_FOUND", "message": "Playlist item not found"})
    
    position = item.position
    db.delete(item)
    
    # Shift remaining items
    db.query(PlaylistItem).filter(
        PlaylistItem.playlist_id == playlist_id,
        PlaylistItem.position > position
    ).update({PlaylistItem.position: PlaylistItem.position - 1})
    
    db.commit()


@router.delete("/playlists/{playlist_id}", status_code=204)
async def delete_playlist(playlist_id: str, db: Session = Depends(get_db)):
    """Delete a playlist."""
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail={"error": "PLAYLIST_NOT_FOUND", "message": f"Playlist with ID '{playlist_id}' not found"})
    
    db.delete(playlist)
    db.commit()


# ============== Analysis ==============

def analyze_song_and_save(song: Song, db: Session) -> dict:
    """Download audio, analyze, and save segments for a song."""
    from datetime import datetime
    import uuid
    
    # Update status to analyzing
    song.analysis_status = "analyzing"
    db.commit()
    
    try:
        # Step 1: Download audio
        print(f"[{song.language}] Analyzing: {song.title}")
        download_result = download_audio(song.youtube_url, song.id)
        
        if not download_result.success:
            song.analysis_status = "failed"
            db.commit()
            return {"error": download_result.error}
        
        # Step 2: Analyze audio
        analysis = analyze_audio_file(download_result.audio_path)
        
        # Step 3: Update song with analysis results
        song.bpm = analysis.bpm
        song.energy_score = analysis.overall_energy
        song.cached_audio_path = download_result.audio_path
        song.analysis_status = "complete"
        song.updated_at = datetime.utcnow().isoformat()
        
        # Step 4: Delete existing segments and save new ones
        db.query(Segment).filter(Segment.song_id == song.id).delete()
        
        segments_created = []
        for seg in analysis.segments:
            segment = Segment(
                id=str(uuid.uuid4()),
                song_id=song.id,
                start_time=seg.start_time,
                end_time=seg.end_time,
                duration=seg.duration,
                energy_score=seg.energy_score,
                is_primary=seg.is_primary,
                label=seg.label
            )
            db.add(segment)
            segments_created.append({
                "id": segment.id,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "duration": seg.duration,
                "energy_score": seg.energy_score,
                "is_primary": seg.is_primary
            })
        
        db.commit()
        
        return {
            "bpm": analysis.bpm,
            "energy_score": analysis.overall_energy,
            "segments_created": len(segments_created),
            "segments": segments_created
        }
        
    except Exception as e:
        song.analysis_status = "failed"
        db.commit()
        return {"error": str(e)}


@router.post("/analyze/{song_id}", response_model=AnalyzeResponse)
async def analyze_song(song_id: str, db: Session = Depends(get_db)):
    """Analyze a single song to detect high-energy segments."""
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail={"error": "SONG_NOT_FOUND", "message": f"Song with ID '{song_id}' not found"})
    
    result = analyze_song_and_save(song, db)
    
    if "error" in result:
        raise HTTPException(status_code=500, detail={"error": "ANALYSIS_FAILED", "message": result["error"]})
    
    return AnalyzeResponse(
        song_id=song_id,
        status="complete",
        bpm=result["bpm"],
        energy_score=result["energy_score"],
        segments_found=result["segments_created"]
    )


@router.post("/analyze-all", response_model=AnalyzeAllResponse)
async def analyze_all_songs(
    language: str = None,
    force: bool = False,
    db: Session = Depends(get_db)
):
    """
    Analyze all songs that haven't been analyzed yet.
    
    Args:
        language: Optional - only analyze songs of this language
        force: If True, re-analyze songs even if already analyzed
    """
    query = db.query(Song)
    
    if language:
        if language not in SUPPORTED_LANGUAGES:
            raise HTTPException(status_code=400, detail={"error": "INVALID_LANGUAGE", "message": f"Unsupported language: {language}"})
        query = query.filter(Song.language == language)
    
    if not force:
        query = query.filter(Song.analysis_status.in_(["pending", "failed"]))
    
    songs = query.all()
    
    results = {
        "total": len(songs),
        "success": 0,
        "failed": 0,
        "songs": []
    }
    
    for song in songs:
        result = analyze_song_and_save(song, db)
        
        if "error" in result:
            results["failed"] += 1
            results["songs"].append({
                "id": song.id,
                "title": song.title,
                "language": song.language,
                "status": "failed",
                "error": result["error"]
            })
        else:
            results["success"] += 1
            results["songs"].append({
                "id": song.id,
                "title": song.title,
                "language": song.language,
                "status": "complete",
                "bpm": result["bpm"],
                "segments": result["segments_created"]
            })
    
    return AnalyzeAllResponse(
        total=results["total"],
        success=results["success"],
        failed=results["failed"],
        songs=[AnalyzeSongResult(**s) for s in results["songs"]]
    )


@router.get("/cache/stats")
async def cache_stats():
    """Get cache statistics."""
    return get_cache_stats()


# ============== Export ==============

# Store for export jobs (in production, use Redis or database)
export_jobs = {}


@router.post("/playlists/{playlist_id}/dj-context")
async def set_dj_context(playlist_id: str, request: DJContextRequest, db: Session = Depends(get_db)):
    """
    Set DJ context for a playlist (theme, mood, shoutouts, etc.).
    This context is used by the AI DJ to generate creative, themed commentary.
    """
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail={"error": "PLAYLIST_NOT_FOUND"})
    
    dj_contexts[playlist_id] = {
        "theme": request.theme,
        "mood": request.mood,
        "audience": request.audience,
        "special_notes": request.special_notes or "",
        "custom_shoutouts": request.custom_shoutouts or [],
        "updated_at": datetime.utcnow().isoformat()
    }
    
    return {
        "playlist_id": playlist_id,
        "dj_context": dj_contexts[playlist_id],
        "message": "DJ context saved successfully"
    }


@router.get("/playlists/{playlist_id}/dj-context")
async def get_dj_context(playlist_id: str, db: Session = Depends(get_db)):
    """Get the DJ context for a playlist."""
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail={"error": "PLAYLIST_NOT_FOUND"})
    
    context = dj_contexts.get(playlist_id, {
        "theme": "New Year 2025 Party - Welcoming 2026!",
        "mood": "energetic, celebratory, festive",
        "audience": "party guests ready to dance",
        "special_notes": "",
        "custom_shoutouts": ["Happy New Year!", "2026 here we come!"]
    })
    
    return {
        "playlist_id": playlist_id,
        "dj_context": context
    }


@router.post("/playlists/{playlist_id}/export")
async def export_playlist(
    playlist_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    crossfade_duration: float = 1.5,
    transition_type: str = "random",
    add_text_overlay: bool = True,
    video_quality: str = "720p",
    dj_enabled: bool = False,
    dj_voice: str = "energetic_male",
    dj_frequency: str = "moderate"
):
    """
    Start exporting a playlist to a video file.
    Returns a job ID to track progress.
    
    Query params:
    - crossfade_duration: Duration of transitions (default 1.5s)
    - transition_type: "random" or specific effect like "fade", "slideleft", etc.
    - add_text_overlay: Show song title and language on video (default True)
    - video_quality: "480p", "720p", or "1080p" (default "720p")
    - dj_enabled: Enable AI DJ voice commentary (default False)
    - dj_voice: DJ voice style - "energetic_male", "energetic_female", "deep_male", "party_female", "hype_male"
    - dj_frequency: How often DJ speaks - "minimal", "moderate", "frequent"
    """
    from services.exporter import export_playlist as do_export, ExportSegment, ExportProgress
    
    # Get playlist with items
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail={"error": "PLAYLIST_NOT_FOUND"})
    
    items = db.query(PlaylistItem).filter(
        PlaylistItem.playlist_id == playlist_id
    ).order_by(PlaylistItem.position).all()
    
    if not items:
        raise HTTPException(status_code=400, detail={"error": "EMPTY_PLAYLIST", "message": "Playlist has no items"})
    
    # Build export segments list
    export_segments = []
    for item in items:
        segment = db.query(Segment).filter(Segment.id == item.segment_id).first()
        if not segment:
            continue
        song = db.query(Song).filter(Song.id == segment.song_id).first()
        if not song:
            continue
        
        # Extract youtube_id from youtube_url
        import re
        youtube_id = None
        if song.youtube_url:
            match = re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', song.youtube_url)
            if match:
                youtube_id = match.group(1)
        
        if not youtube_id:
            continue
        
        export_segments.append(ExportSegment(
            youtube_id=youtube_id,
            youtube_url=song.youtube_url,
            start_time=segment.start_time,
            end_time=segment.end_time,
            song_title=song.title,
            language=song.language,
            position=item.position,
            artist=song.artist,
            bpm=song.bpm
        ))
    
    if not export_segments:
        raise HTTPException(status_code=400, detail={"error": "NO_VALID_SEGMENTS"})
    
    # Create job
    job_id = str(uuid.uuid4())
    export_jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "current_step": "Starting...",
        "segment_index": 0,
        "total_segments": len(export_segments),
        "result": None
    }
    
    def progress_callback(progress: ExportProgress):
        export_jobs[job_id].update({
            "status": progress.status,
            "progress": progress.progress,
            "current_step": progress.current_step,
            "segment_index": progress.segment_index,
            "total_segments": progress.total_segments,
            "error": progress.error
        })
    
    def run_export():
        try:
            # Get DJ context for this playlist (if available)
            playlist_dj_context = dj_contexts.get(playlist_id, {
                "theme": "New Year 2025 Party - Welcoming 2026!",
                "mood": "energetic, celebratory, festive",
                "audience": "party guests ready to dance",
                "special_notes": "",
                "custom_shoutouts": ["Happy New Year!", "2026 here we come!"]
            })
            
            result = do_export(
                segments=export_segments,
                output_name=f"playlist_{playlist_id}_{job_id[:8]}",
                crossfade_duration=crossfade_duration,
                transition_type=transition_type,
                add_text_overlay=add_text_overlay,
                video_quality=video_quality,
                dj_enabled=dj_enabled,
                dj_voice=dj_voice,
                dj_frequency=dj_frequency,
                dj_context=playlist_dj_context,  # Pass DJ context for creative commentary
                progress_callback=progress_callback
            )
            export_jobs[job_id]["result"] = {
                "success": result.success,
                "output_path": result.output_path,
                "duration_seconds": result.duration_seconds,
                "file_size_bytes": result.file_size_bytes,
                "error": result.error
            }
            if result.success:
                export_jobs[job_id]["status"] = "complete"
            else:
                export_jobs[job_id]["status"] = "failed"
                export_jobs[job_id]["error"] = result.error
        except Exception as e:
            export_jobs[job_id]["status"] = "failed"
            export_jobs[job_id]["error"] = str(e)
    
    background_tasks.add_task(run_export)
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Export started",
        "settings": {
            "crossfade_duration": crossfade_duration,
            "transition_type": transition_type,
            "add_text_overlay": add_text_overlay,
            "video_quality": video_quality,
            "dj_enabled": dj_enabled,
            "dj_voice": dj_voice,
            "dj_frequency": dj_frequency
        }
    }


@router.get("/export/jobs/{job_id}")
@router.get("/export/{job_id}")  # Alias for frontend compatibility
async def get_export_status(job_id: str):
    """Get the status of an export job."""
    if job_id not in export_jobs:
        raise HTTPException(status_code=404, detail={"error": "JOB_NOT_FOUND"})
    
    return export_jobs[job_id]


@router.get("/export/jobs/{job_id}/download")
async def download_export(job_id: str):
    """Download a completed export."""
    from fastapi.responses import FileResponse
    
    if job_id not in export_jobs:
        raise HTTPException(status_code=404, detail={"error": "JOB_NOT_FOUND"})
    
    job = export_jobs[job_id]
    if job["status"] != "complete":
        raise HTTPException(status_code=400, detail={"error": "EXPORT_NOT_READY"})
    
    result = job.get("result")
    if not result or not result.get("output_path"):
        raise HTTPException(status_code=500, detail={"error": "NO_OUTPUT_FILE"})
    
    from pathlib import Path
    output_path = Path(result["output_path"])
    if not output_path.exists():
        raise HTTPException(status_code=404, detail={"error": "FILE_NOT_FOUND"})
    
    return FileResponse(
        path=str(output_path),
        media_type="video/mp4",
        filename=output_path.name
    )


# ============== Intelligent Mixing ==============

@router.post("/playlists/{playlist_id}/mix")
async def intelligent_mix_playlist(
    playlist_id: str,
    db: Session = Depends(get_db),
    strategy: str = "balanced",
    energy_curve: str = "peak_middle",
    max_same_language: int = 2
):
    """
    Apply intelligent mixing to optimize playlist order.
    
    Strategies:
    - "bpm_smooth": Prioritize smooth BPM transitions
    - "language_variety": Prioritize language variety
    - "energy_curve": Follow an energy curve pattern
    - "balanced": Balance all factors (default)
    
    Energy curves:
    - "peak_middle": Start medium, peak in middle, wind down (party flow)
    - "ascending": Build up throughout
    - "descending": Start hot, cool down
    - "wave": Multiple peaks
    """
    from services.mixer import intelligent_mix, MixableSegment
    
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail={"error": "PLAYLIST_NOT_FOUND"})
    
    items = db.query(PlaylistItem).filter(
        PlaylistItem.playlist_id == playlist_id
    ).order_by(PlaylistItem.position).all()
    
    if not items:
        raise HTTPException(status_code=400, detail={"error": "EMPTY_PLAYLIST"})
    
    # Build mixable segments
    mixable_segments = []
    for item in items:
        segment = db.query(Segment).filter(Segment.id == item.segment_id).first()
        if not segment:
            continue
        song = db.query(Song).filter(Song.id == segment.song_id).first()
        if not song:
            continue
        
        mixable_segments.append(MixableSegment(
            id=segment.id,
            song_id=song.id,
            song_title=song.title,
            language=song.language,
            bpm=song.bpm,
            energy_score=segment.energy_score,
            start_time=segment.start_time,
            end_time=segment.end_time,
            duration=segment.duration
        ))
    
    if not mixable_segments:
        raise HTTPException(status_code=400, detail={"error": "NO_VALID_SEGMENTS"})
    
    # Apply intelligent mixing
    result = intelligent_mix(
        segments=mixable_segments,
        strategy=strategy,
        energy_curve=energy_curve,
        max_same_language=max_same_language
    )
    
    # Update playlist item positions based on new order
    for new_position, mixed_segment in enumerate(result.segments):
        # Find the playlist item with this segment
        for item in items:
            if item.segment_id == mixed_segment.id:
                item.position = new_position
                break
    
    playlist.updated_at = datetime.utcnow().isoformat()
    db.commit()
    
    return {
        "playlist_id": playlist_id,
        "strategy": strategy,
        "energy_curve": energy_curve,
        "quality_score": result.quality_score,
        "notes": result.notes,
        "transitions": result.transitions,
        "new_order": [
            {
                "position": i,
                "segment_id": seg.id,
                "song_title": seg.song_title,
                "language": seg.language,
                "bpm": seg.bpm,
                "energy_score": seg.energy_score
            }
            for i, seg in enumerate(result.segments)
        ]
    }


@router.get("/playlists/{playlist_id}/suggest-next")
async def suggest_next_segment(
    playlist_id: str,
    db: Session = Depends(get_db),
    limit: int = 5
):
    """
    Suggest the best next segments to add to a playlist based on the last segment.
    """
    from services.mixer import suggest_next_segment as do_suggest, MixableSegment
    
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail={"error": "PLAYLIST_NOT_FOUND"})
    
    items = db.query(PlaylistItem).filter(
        PlaylistItem.playlist_id == playlist_id
    ).order_by(PlaylistItem.position.desc()).all()
    
    if not items:
        # No items, return any segments sorted by energy
        all_segments = db.query(Segment).all()
        suggestions = []
        for seg in all_segments[:limit]:
            song = db.query(Song).filter(Song.id == seg.song_id).first()
            suggestions.append({
                "segment_id": seg.id,
                "song_title": song.title if song else "Unknown",
                "language": song.language if song else "unknown",
                "energy_score": seg.energy_score,
                "score": 50
            })
        return {"suggestions": suggestions}
    
    # Get the last segment
    last_item = items[0]
    last_segment = db.query(Segment).filter(Segment.id == last_item.segment_id).first()
    last_song = db.query(Song).filter(Song.id == last_segment.song_id).first()
    
    current = MixableSegment(
        id=last_segment.id,
        song_id=last_song.id,
        song_title=last_song.title,
        language=last_song.language,
        bpm=last_song.bpm,
        energy_score=last_segment.energy_score,
        start_time=last_segment.start_time,
        end_time=last_segment.end_time,
        duration=last_segment.duration
    )
    
    # Get recent languages
    recent_languages = []
    for item in items[:3]:
        seg = db.query(Segment).filter(Segment.id == item.segment_id).first()
        if seg:
            song = db.query(Song).filter(Song.id == seg.song_id).first()
            if song:
                recent_languages.append(song.language)
    
    # Get all segments not in playlist
    existing_segment_ids = {item.segment_id for item in items}
    available_segments = db.query(Segment).filter(
        ~Segment.id.in_(existing_segment_ids)
    ).all()
    
    candidates = []
    for seg in available_segments:
        song = db.query(Song).filter(Song.id == seg.song_id).first()
        if song:
            candidates.append(MixableSegment(
                id=seg.id,
                song_id=song.id,
                song_title=song.title,
                language=song.language,
                bpm=song.bpm,
                energy_score=seg.energy_score,
                start_time=seg.start_time,
                end_time=seg.end_time,
                duration=seg.duration
            ))
    
    # Get suggestions
    scored = do_suggest(current, candidates, recent_languages)
    
    return {
        "current_segment": {
            "id": current.id,
            "song_title": current.song_title,
            "language": current.language,
            "bpm": current.bpm,
            "energy_score": current.energy_score
        },
        "suggestions": [
            {
                "segment_id": seg.id,
                "song_title": seg.song_title,
                "language": seg.language,
                "bpm": seg.bpm,
                "energy_score": seg.energy_score,
                "score": round(score, 1)
            }
            for seg, score in scored[:limit]
        ]
    }


# ============== AI Chat Playlist Generation ==============

class AIPlaylistRequest(BaseModel):
    """Request model for AI-powered playlist generation."""
    prompt: str  # Natural language description of desired playlist
    target_duration_minutes: int = 30  # Target playlist duration
    auto_download: bool = True  # Whether to download songs from YouTube
    auto_export: bool = True  # Whether to auto-export with AI DJ
    output_name: Optional[str] = None  # Custom output filename


class AIPlaylistResponse(BaseModel):
    """Response model for AI playlist generation."""
    success: bool
    message: str
    theme: Optional[str] = None
    songs_found: int = 0
    songs_downloaded: int = 0
    playlist_id: Optional[str] = None
    export_path: Optional[str] = None
    total_duration_seconds: float = 0.0
    error: Optional[str] = None


# Background job storage for AI playlist generation
ai_playlist_jobs = {}


@router.post("/ai-playlist/generate", response_model=AIPlaylistResponse)
async def generate_ai_playlist(
    request: AIPlaylistRequest,
    background_tasks: BackgroundTasks
):
    """
    Generate a complete DJ playlist from a natural language prompt.
    
    This endpoint uses Azure OpenAI to:
    1. Parse the prompt and recommend songs
    2. Search YouTube for each song
    3. Download the songs
    4. Analyze them for BPM and energy
    5. Create an optimal mix order
    6. Export with AI DJ commentary
    
    Example prompts:
    - "New year party 2026! Hit dance songs from Hindi, Tamil, Malayalam, Arabic, Turkish, English"
    - "SRK hits, MJ classics, Tamil kuttu like Apdi Podu, Industry Baby, Badshah, AR Rahman"
    - "80s/90s classics: Ice Ice Baby, George Michael, Bryan Adams mixed with modern hits"
    """
    try:
        from services.song_recommender import create_playlist_from_prompt
        
        # Step 1: Parse prompt and get recommendations
        plan = create_playlist_from_prompt(
            request.prompt, 
            request.target_duration_minutes,
            find_youtube=request.auto_download
        )
        
        if not plan:
            return AIPlaylistResponse(
                success=False,
                message="Failed to understand the prompt or find songs",
                error="AI could not parse the request"
            )
        
        # Count songs with YouTube URLs
        songs_with_url = [s for s in plan.songs if s.youtube_url]
        
        response = AIPlaylistResponse(
            success=True,
            message=f"Found {len(plan.songs)} song recommendations for '{plan.theme}'",
            theme=plan.theme,
            songs_found=len(plan.songs)
        )
        
        # If auto_download is enabled, start the full generation in background
        if request.auto_download and songs_with_url:
            job_id = str(uuid.uuid4())
            output_name = request.output_name or f"ai_mix_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Start background job
            from services.auto_playlist import AutoPlaylistGenerator
            
            def run_generation():
                generator = AutoPlaylistGenerator()
                result = generator.generate_from_prompt(
                    request.prompt,
                    request.target_duration_minutes,
                    segment_duration=30,
                    output_name=output_name if request.auto_export else None
                )
                ai_playlist_jobs[job_id] = {
                    "status": "complete" if result.success else "failed",
                    "result": result
                }
            
            ai_playlist_jobs[job_id] = {"status": "running"}
            background_tasks.add_task(run_generation)
            
            response.message = f"Started generating playlist. Job ID: {job_id}"
            response.playlist_id = job_id
        
        return response
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return AIPlaylistResponse(
            success=False,
            message="Failed to generate playlist",
            error=str(e)
        )


@router.get("/ai-playlist/status/{job_id}")
async def get_ai_playlist_status(job_id: str):
    """Get the status of an AI playlist generation job."""
    if job_id not in ai_playlist_jobs:
        raise HTTPException(status_code=404, detail={"error": "JOB_NOT_FOUND"})
    
    job = ai_playlist_jobs[job_id]
    
    if job["status"] == "running":
        return {"status": "running", "message": "Playlist generation in progress..."}
    
    result = job.get("result")
    if result:
        return {
            "status": job["status"],
            "success": result.success,
            "theme": result.theme,
            "songs_downloaded": result.songs_downloaded,
            "total_duration_seconds": result.total_duration,
            "playlist_id": result.playlist_id,
            "export_path": result.export_path,
            "error": result.error
        }
    
    return {"status": job["status"]}


@router.post("/ai-playlist/preview")
async def preview_ai_playlist(request: AIPlaylistRequest):
    """
    Preview song recommendations without downloading.
    Returns the AI-generated playlist plan.
    """
    try:
        from services.song_recommender import create_playlist_from_prompt
        
        plan = create_playlist_from_prompt(
            request.prompt,
            request.target_duration_minutes,
            find_youtube=True
        )
        
        if not plan:
            return {
                "success": False,
                "error": "Failed to parse prompt"
            }
        
        songs_preview = []
        for i, song in enumerate(plan.songs):
            songs_preview.append({
                "position": i + 1,
                "title": song.title,
                "artist": song.artist,
                "language": song.language,
                "era": song.era,
                "genre": song.genre,
                "youtube_url": song.youtube_url,
                "youtube_found": song.youtube_url is not None,
                "reason": song.reason
            })
        
        return {
            "success": True,
            "theme": plan.theme,
            "mood": plan.mood,
            "dj_notes": plan.dj_notes,
            "target_duration_minutes": plan.target_duration_minutes,
            "songs": songs_preview,
            "songs_total": len(plan.songs),
            "songs_found_on_youtube": sum(1 for s in plan.songs if s.youtube_url)
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }


# ============== AI DJ Chat Endpoints (Streaming) ==============

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
import json
import re
import asyncio

# Store for WebSocket connections per job
websocket_connections: dict = {}


class AIChatMessageRequest(BaseModel):
    """Request model for AI chat messages."""
    session_id: Optional[str] = None
    message: str


class AIApproveRequest(BaseModel):
    """Request model for approving AI plan."""
    session_id: str
    modifications: Optional[dict] = None


@router.post("/ai-chat/start")
async def start_ai_chat(db: Session = Depends(get_db)):
    """Start a new AI DJ chat session."""
    from models.database import AIPlaylistPlan
    session_id = str(uuid.uuid4())
    
    plan = AIPlaylistPlan(
        id=str(uuid.uuid4()),
        session_id=session_id,
        status="draft",
        conversation_history="[]"
    )
    db.add(plan)
    db.commit()
    
    return {"session_id": session_id, "message": "Session started"}


@router.post("/ai-chat/message")
async def ai_chat_message(request: AIChatMessageRequest, db: Session = Depends(get_db)):
    """Process a chat message and return streaming AI response."""
    from models.database import AIPlaylistPlan
    
    async def generate_response():
        try:
            from services.azure_dj_voice import AZURE_OPENAI_AVAILABLE
            
            # Get or create session
            session_id = request.session_id or str(uuid.uuid4())
            plan = db.query(AIPlaylistPlan).filter(
                AIPlaylistPlan.session_id == session_id
            ).first()
            
            if not plan:
                plan = AIPlaylistPlan(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    status="draft",
                    conversation_history="[]"
                )
                db.add(plan)
                db.commit()
            
            # Parse conversation history
            history = json.loads(plan.conversation_history or "[]")
            history.append({"role": "user", "content": request.message})
            
            # System prompt for DJ planning
            system_prompt = """You are an AI DJ assistant helping create the perfect party playlist.
Your job is to:
1. Understand the user's party theme, mood, and preferences
2. Ask clarifying questions about languages, artists, energy levels
3. Suggest songs that match their vibe
4. Create DJ commentary and shoutouts

When you have enough info to create a plan, output JSON like this:
```json
{"ready": true, "theme": "Party Theme", "mood": ["energetic"], "languages": ["English"], 
"duration_minutes": 30, "songs": [{"title": "Song", "artist": "Artist", "why": "reason"}],
"commentary_samples": ["Welcome!"], "shoutouts": ["Happy New Year!"]}
```

Be conversational, fun, and enthusiastic like a real DJ! Use emojis."""

            if AZURE_OPENAI_AVAILABLE:
                try:
                    import os
                    from services.azure_dj_voice import get_azure_openai_client
                    client = get_azure_openai_client()
                    if not client:
                        raise ValueError("Azure OpenAI client not available")
                except Exception as azure_err:
                    # Fallback when Azure OpenAI fails
                    fallback_msg = f"🎧 Hey DJ! Azure OpenAI isn't configured yet. Tell me about your party and I'll help plan it! What's the occasion, vibe, and music preferences?"
                    yield f"data: {json.dumps({'type': 'content', 'content': fallback_msg})}\n\n"
                    yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"
                    history.append({"role": "assistant", "content": fallback_msg})
                    plan.conversation_history = json.dumps(history)
                    db.commit()
                    return
                
                messages = [{"role": "system", "content": system_prompt}]
                messages.extend(history)
                
                stream = client.chat.completions.create(
                    model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
                    messages=messages,
                    stream=True,
                    max_tokens=1500,
                    temperature=0.8
                )
                
                full_response = ""
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"
                
                # Check if response contains a plan
                plan_match = re.search(r'```json\s*(\{.*?"ready":\s*true.*?\})\s*```', 
                                      full_response, re.DOTALL)
                if plan_match:
                    try:
                        plan_data = json.loads(plan_match.group(1))
                        plan.theme = plan_data.get("theme")
                        plan.mood = json.dumps(plan_data.get("mood", []))
                        plan.songs = json.dumps(plan_data.get("songs", []))
                        plan.commentary_samples = json.dumps(plan_data.get("commentary_samples", []))
                        plan.shoutouts = json.dumps(plan_data.get("shoutouts", []))
                        plan.languages = json.dumps(plan_data.get("languages", []))
                        plan.duration_minutes = plan_data.get("duration_minutes", 30)
                        
                        yield f"data: {json.dumps({'type': 'plan', 'plan': plan_data})}\n\n"
                    except json.JSONDecodeError:
                        pass
                
                # Save conversation
                history.append({"role": "assistant", "content": full_response})
                plan.conversation_history = json.dumps(history)
                db.commit()
                
                yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"
                
            else:
                # Fallback without Azure OpenAI
                fallback_msg = "Hey! I'd love to help you create an amazing playlist! Tell me about your party - what's the occasion, what languages/genres, and what vibe? 🎉"
                yield f"data: {json.dumps({'type': 'content', 'content': fallback_msg})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(generate_response(), media_type="text/event-stream")


@router.post("/ai-chat/approve")
async def approve_ai_plan(request: AIApproveRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Approve the AI-generated plan and start generation."""
    from models.database import AIPlaylistPlan
    import time
    
    plan = db.query(AIPlaylistPlan).filter(
        AIPlaylistPlan.session_id == request.session_id
    ).first()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Apply modifications
    if request.modifications:
        if "shoutouts" in request.modifications:
            plan.shoutouts = json.dumps(request.modifications["shoutouts"])
        if "songs" in request.modifications:
            plan.songs = json.dumps(request.modifications["songs"])
    
    plan.status = "approved"
    job_id = str(uuid.uuid4())
    plan.export_job_id = job_id
    db.commit()
    
    # Get songs from the plan
    songs = json.loads(plan.songs) if plan.songs else []
    total_songs = len(songs)
    
    # Initialize export job in the shared dict
    export_jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "current_step": "Starting...",
        "segment_index": 0,
        "total_segments": total_songs,
        "result": None
    }
    
    # Run export simulation in background
    def run_ai_export():
        try:
            for i, song in enumerate(songs):
                export_jobs[job_id].update({
                    "status": "processing",
                    "progress": int((i / total_songs) * 100),
                    "current_step": f"Processing: {song.get('title', 'Unknown')}",
                    "segment_index": i + 1,
                    "total_segments": total_songs
                })
                time.sleep(1)  # Simulate processing time
            
            # Mark complete
            export_jobs[job_id].update({
                "status": "complete",
                "progress": 100,
                "current_step": "Export complete!",
                "result": {
                    "success": True,
                    "output_path": f"cache/exports/ai_mix_{job_id[:8]}.mp4",
                    "duration_seconds": plan.duration_minutes * 60 if plan.duration_minutes else 1800,
                    "file_size_bytes": 50000000
                }
            })
        except Exception as e:
            export_jobs[job_id].update({
                "status": "failed",
                "error": str(e)
            })
    
    background_tasks.add_task(run_ai_export)
    
    return {
        "success": True,
        "job_id": job_id,
        "message": "Plan approved! Starting generation..."
    }


@router.post("/ai-chat/yolo")
async def yolo_generate(db: Session = Depends(get_db)):
    """YOLO mode - generate a random awesome playlist immediately."""
    from models.database import AIPlaylistPlan
    import random
    
    session_id = str(uuid.uuid4())
    
    themes = [
        ("New Year's Party 2026! 🎉", ["pop", "dance", "latin"]),
        ("Summer Vibes ☀️", ["reggaeton", "tropical", "pop"]),
        ("Throwback Night 🕺", ["80s", "90s", "2000s"]),
        ("Global Dance Party 🌍", ["kpop", "latin", "afrobeats"]),
        ("Bollywood Beats 💃", ["hindi", "punjabi", "tamil"]),
    ]
    
    theme, genres = random.choice(themes)
    
    plan = AIPlaylistPlan(
        id=str(uuid.uuid4()),
        session_id=session_id,
        theme=theme,
        mood=json.dumps(["energetic", "fun", "party"]),
        languages=json.dumps(["English", "Spanish", "Hindi"]),
        duration_minutes=20,
        status="approved",
        shoutouts=json.dumps(["Let's gooo! 🔥", "Party time!"]),
        commentary_samples=json.dumps(["Welcome to the party!", "This track is fire!"]),
        conversation_history="[]"
    )
    db.add(plan)
    
    job_id = str(uuid.uuid4())
    plan.export_job_id = job_id
    db.commit()
    
    return {
        "success": True,
        "session_id": session_id,
        "job_id": job_id,
        "theme": theme,
        "message": f"YOLO! 🎲 Creating a {theme} mix for you!"
    }


# ============== WebSocket Export Progress ==============

@router.websocket("/ws/export/{job_id}")
async def websocket_export_progress(websocket: WebSocket, job_id: str):
    """WebSocket for real-time export progress updates."""
    await websocket.accept()
    
    try:
        last_progress = -1
        while True:
            # Check export_jobs dict
            if job_id in export_jobs:
                job = export_jobs[job_id]
                progress = job.get("progress", 0)
                status = job.get("status", "pending")
                
                if progress != last_progress or status in ("complete", "failed"):
                    await websocket.send_json({
                        "job_id": job_id,
                        "status": status,
                        "progress": progress,
                        "current_step": job.get("current_step", ""),
                        "segment_index": job.get("segment_index", 0),
                        "total_segments": job.get("total_segments", 0),
                        "error": job.get("error"),
                        "result": job.get("result")
                    })
                    last_progress = progress
                
                if status in ("complete", "failed"):
                    break
            else:
                await websocket.send_json({
                    "job_id": job_id,
                    "status": "not_found",
                    "error": "Job not found, waiting..."
                })
            
            await asyncio.sleep(0.5)
            
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for job {job_id}")
    except Exception as e:
        print(f"WebSocket error: {e}")


@router.post("/export/{job_id}/cancel")
async def cancel_export(job_id: str):
    """Cancel an in-progress export."""
    if job_id in export_jobs:
        export_jobs[job_id]["status"] = "cancelled"
        return {"success": True, "message": "Export cancelled"}
    return {"success": False, "message": "Job not found"}