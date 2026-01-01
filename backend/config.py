"""
Video DJ Playlist Creator - Configuration
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # App info
    app_name: str = "Video DJ Playlist Creator"
    app_version: str = "1.0.0"
    debug: bool = False  # Disable hot-reload to avoid file watcher issues
    
    # Server
    host: str = "127.0.0.1"
    port: int = 9876
    
    # Paths
    base_dir: Path = Path.home() / "video-dj-playlist"
    
    @property
    def database_path(self) -> Path:
        return self.base_dir / "database.sqlite"
    
    @property
    def cache_dir(self) -> Path:
        return self.base_dir / "cache"
    
    @property
    def audio_cache_dir(self) -> Path:
        return self.cache_dir / "audio"
    
    @property
    def video_cache_dir(self) -> Path:
        return self.cache_dir / "video"
    
    @property
    def thumbnail_cache_dir(self) -> Path:
        return self.cache_dir / "thumbnails"
    
    @property
    def exports_dir(self) -> Path:
        return self.base_dir / "exports"
    
    # Discovery settings
    songs_per_language: int = 5  # More songs per language
    
    # Analysis settings
    min_segment_duration: int = 30  # seconds (shorter segments)
    max_segment_duration: int = 45  # seconds (shorter segments)
    max_segments_per_song: int = 2  # Fewer segments per song since shorter
    min_segment_gap: int = 20  # seconds between segments
    
    # Export settings
    default_crossfade_duration: float = 2.0  # seconds
    target_playlist_duration: int = 2700  # 45 minutes
    
    def ensure_directories(self):
        """Create all required directories."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.audio_cache_dir.mkdir(parents=True, exist_ok=True)
        self.video_cache_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnail_cache_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)


# Search queries for each language - focus on biggest hits by year
SEARCH_QUERIES = {
    "english": {
        "2024": "biggest dance hits 2024 official music video",
        "2023": "top dance songs 2023 most viewed official video",
        "2022": "best party songs 2022 official video",
        "all_time": "most viewed dance songs all time music video"
    },
    "hindi": {
        "2024": "biggest bollywood dance hits 2024 official video",
        "2023": "top hindi party songs 2023 most viewed",
        "2022": "best bollywood dance songs 2022 official",
        "all_time": "most viewed bollywood dance songs all time"
    },
    "malayalam": {
        "2024": "malayalam hit songs 2024 official video",
        "2023": "best malayalam dance songs 2023",
        "2022": "top malayalam songs 2022 official video",
        "all_time": "most viewed malayalam songs all time"
    },
    "tamil": {
        "2024": "tamil kuthu songs 2024 official video biggest hits",
        "2023": "top tamil dance songs 2023 most viewed",
        "2022": "best tamil party songs 2022 official",
        "all_time": "most viewed tamil songs all time"
    },
    "turkish": {
        "2024": "en çok dinlenen türkçe pop 2024",
        "2023": "türkçe hit şarkılar 2023",
        "2022": "en popüler türkçe şarkılar 2022",
        "all_time": "en çok izlenen türkçe şarkılar"
    },
    "uzbek": {
        "2024": "eng sara o'zbek qo'shiqlari 2024",
        "2023": "top uzbek songs 2023",
        "2022": "uzbek hit music 2022",
        "all_time": "most popular uzbek songs"
    },
    "arabic": {
        "2024": "اغاني عربية 2024 الاكثر مشاهدة",
        "2023": "افضل اغاني عربية 2023",
        "2022": "اغاني عربية 2022 رقص",
        "all_time": "اكثر الاغاني العربية مشاهدة"
    }
}

# Supported languages
SUPPORTED_LANGUAGES = list(SEARCH_QUERIES.keys())

# Create global settings instance
settings = Settings()
