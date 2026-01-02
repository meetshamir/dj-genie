"""
Database models and setup using SQLAlchemy.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, Text, ForeignKey, Index
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from pathlib import Path

Base = declarative_base()


class Song(Base):
    """Song model - represents a YouTube video."""
    
    __tablename__ = "songs"
    
    id = Column(String, primary_key=True)  # YouTube video ID
    title = Column(String, nullable=False)
    artist = Column(String, nullable=True)
    language = Column(String, nullable=False)
    duration = Column(Integer, nullable=False)  # seconds
    thumbnail_url = Column(String, nullable=True)
    youtube_url = Column(String, nullable=False)
    bpm = Column(Float, nullable=True)
    energy_score = Column(Float, nullable=True)
    analysis_status = Column(String, default="pending")  # pending, downloading, analyzing, complete, failed
    cached_audio_path = Column(String, nullable=True)
    cached_video_path = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    updated_at = Column(String, default=lambda: datetime.utcnow().isoformat(), onupdate=lambda: datetime.utcnow().isoformat())
    
    # Relationships
    segments = relationship("Segment", back_populates="song", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_songs_language", "language"),
        Index("idx_songs_status", "analysis_status"),
    )


class Segment(Base):
    """Segment model - represents an exciting part of a song."""
    
    __tablename__ = "segments"
    
    id = Column(String, primary_key=True)  # UUID
    song_id = Column(String, ForeignKey("songs.id"), nullable=False)
    start_time = Column(Float, nullable=False)  # seconds
    end_time = Column(Float, nullable=False)  # seconds
    duration = Column(Float, nullable=False)  # computed
    energy_score = Column(Float, nullable=False)  # 0-100
    is_primary = Column(Boolean, default=False)  # highest energy segment
    label = Column(String, nullable=True)  # 'chorus_1', 'drop', etc.
    cached_clip_path = Column(String, nullable=True)
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    
    # Relationships
    song = relationship("Song", back_populates="segments")
    playlist_items = relationship("PlaylistItem", back_populates="segment")
    
    __table_args__ = (
        Index("idx_segments_song", "song_id"),
    )


class Playlist(Base):
    """Playlist model - a collection of segments."""
    
    __tablename__ = "playlists"
    
    id = Column(String, primary_key=True)  # UUID
    name = Column(String, nullable=False)
    target_duration = Column(Integer, default=2700)  # 45 minutes
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    updated_at = Column(String, default=lambda: datetime.utcnow().isoformat(), onupdate=lambda: datetime.utcnow().isoformat())
    
    # Relationships
    items = relationship("PlaylistItem", back_populates="playlist", cascade="all, delete-orphan", order_by="PlaylistItem.position")
    export_jobs = relationship("ExportJob", back_populates="playlist")


class PlaylistItem(Base):
    """PlaylistItem model - links segments to playlists with ordering."""
    
    __tablename__ = "playlist_items"
    
    id = Column(String, primary_key=True)  # UUID
    playlist_id = Column(String, ForeignKey("playlists.id"), nullable=False)
    segment_id = Column(String, ForeignKey("segments.id"), nullable=False)
    position = Column(Integer, nullable=False)
    crossfade_duration = Column(Float, default=2.0)
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    
    # Relationships
    playlist = relationship("Playlist", back_populates="items")
    segment = relationship("Segment", back_populates="playlist_items")
    
    __table_args__ = (
        Index("idx_playlist_items_playlist", "playlist_id"),
    )


class ExportJob(Base):
    """ExportJob model - tracks video export progress."""
    
    __tablename__ = "export_jobs"
    
    id = Column(String, primary_key=True)  # UUID
    playlist_id = Column(String, ForeignKey("playlists.id"), nullable=False)
    status = Column(String, default="queued")  # queued, downloading, processing, encoding, complete, failed, cancelled
    progress = Column(Integer, default=0)  # 0-100
    current_step = Column(String, nullable=True)
    output_path = Column(String, nullable=True)
    output_format = Column(String, default="mp4")
    resolution = Column(String, default="1080p")
    started_at = Column(String, nullable=True)
    completed_at = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    
    # Relationships
    playlist = relationship("Playlist", back_populates="export_jobs")
    
    __table_args__ = (
        Index("idx_export_jobs_playlist", "playlist_id"),
    )


class AIPlaylistPlan(Base):
    """AI-generated playlist plan from chat conversation."""
    __tablename__ = "ai_playlist_plans"

    id = Column(String, primary_key=True)  # UUID
    session_id = Column(String, unique=True, index=True, nullable=False)
    user_prompt = Column(Text, nullable=True)
    theme = Column(String, nullable=True)
    mood = Column(Text, nullable=True)  # JSON array stored as text
    songs = Column(Text, nullable=True)  # JSON array of song objects
    commentary_samples = Column(Text, nullable=True)  # JSON array
    cultural_phrases = Column(Text, nullable=True)  # JSON array
    shoutouts = Column(Text, nullable=True)  # JSON array
    languages = Column(Text, nullable=True)  # JSON array
    duration_minutes = Column(Integer, default=30)
    status = Column(String, default="draft")  # draft, approved, generating, complete, failed
    conversation_history = Column(Text, nullable=True)  # JSON array of messages
    export_job_id = Column(String, nullable=True)
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    updated_at = Column(String, default=lambda: datetime.utcnow().isoformat())

class Database:
    """Database connection manager."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def create_tables(self):
        """Create all tables."""
        Base.metadata.create_all(self.engine)
    
    def get_session(self):
        """Get a new database session."""
        return self.SessionLocal()


# Global database instance (initialized in main.py)
db: Optional[Database] = None


def init_database(db_path: Path) -> Database:
    """Initialize the database."""
    global db
    db = Database(db_path)
    db.create_tables()
    return db


def get_db():
    """Dependency for FastAPI routes."""
    if db is None:
        raise RuntimeError("Database not initialized")
    session = db.get_session()
    try:
        yield session
    finally:
        session.close()
