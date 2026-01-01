"""
Discovery service - finds popular dance songs on YouTube.
"""

import re
from typing import List, Optional
from dataclasses import dataclass
import yt_dlp

from config import SEARCH_QUERIES, SUPPORTED_LANGUAGES, settings


@dataclass
class DiscoveredSong:
    """Represents a discovered song from YouTube."""
    id: str
    title: str
    artist: Optional[str]
    language: str
    duration: int
    thumbnail_url: Optional[str]
    youtube_url: str
    view_count: int = 0  # Track popularity
    year: Optional[str] = None  # Release/discovery year


def extract_artist(title: str) -> tuple[str, Optional[str]]:
    """
    Try to extract artist name from video title.
    Returns (clean_title, artist).
    """
    # Common patterns: "Artist - Song Title", "Song Title | Artist", "Artist: Song Title"
    patterns = [
        r'^(.+?)\s*[-–—]\s*(.+)$',  # Artist - Title
        r'^(.+?)\s*\|\s*(.+)$',      # Title | Artist  
        r'^(.+?):\s*(.+)$',          # Artist: Title
    ]
    
    for pattern in patterns:
        match = re.match(pattern, title)
        if match:
            part1, part2 = match.groups()
            # Heuristic: shorter part is usually the artist
            if len(part1) < len(part2):
                return part2.strip(), part1.strip()
            else:
                return part1.strip(), part2.strip()
    
    return title, None


def search_youtube(query: str, max_results: int = 10) -> List[dict]:
    """
    Search YouTube using yt-dlp.
    Returns list of video info dictionaries sorted by view count.
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': 'in_playlist',  # Get more metadata
        'force_generic_extractor': False,
    }
    
    search_query = f"ytsearch{max_results}:{query}"
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(search_query, download=False)
            if result and 'entries' in result:
                entries = list(result['entries'])
                # Sort by view count (descending) - biggest hits first
                entries.sort(key=lambda x: x.get('view_count') or 0, reverse=True)
                return entries
    except Exception as e:
        print(f"YouTube search error: {e}")
    
    return []


def get_video_details(video_id: str) -> Optional[dict]:
    """
    Get detailed info for a single video including view count.
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }
    
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except Exception as e:
        print(f"Video details error for {video_id}: {e}")
    
    return None


def filter_dance_songs(videos: List[dict], min_duration: int = 90, max_duration: int = 600) -> List[dict]:
    """
    Filter videos to keep only likely dance songs.
    - Duration: 1.5-10 minutes (more permissive)
    - Exclude: live performances, covers, tutorials
    """
    filtered = []
    
    exclude_keywords = ['live concert', 'cover version', 'karaoke', 'tutorial', 'reaction', 'behind the scenes']
    
    for video in videos:
        if not video:
            continue
            
        title = video.get('title', '').lower()
        duration = video.get('duration') or 0
        
        # Check duration
        if not (min_duration <= duration <= max_duration):
            continue
        
        # Check excluded keywords
        if any(keyword in title for keyword in exclude_keywords):
            continue
        
        filtered.append(video)
    
    return filtered


def discover_songs_for_language(
    language: str,
    count: int = 5,
    years: List[str] = None
) -> List[DiscoveredSong]:
    """
    Discover biggest hit dance songs for a specific language.
    Searches across multiple years and sorts by popularity (view count).
    """
    if language not in SEARCH_QUERIES:
        raise ValueError(f"Unsupported language: {language}")
    
    queries = SEARCH_QUERIES[language]
    
    # Default years to search
    if years is None:
        years = ["2024", "2023", "2022", "all_time"]
    
    all_videos = []
    existing_ids = set()
    
    # Search each year query
    for year in years:
        if year not in queries:
            continue
        
        query = queries[year]
        print(f"    Searching {language} {year}: {query[:50]}...")
        
        videos = search_youtube(query, max_results=count * 2)
        filtered = filter_dance_songs(videos)
        
        # Add unique videos with year tag
        for video in filtered:
            video_id = video.get('id')
            if video_id and video_id not in existing_ids:
                video['_year'] = year
                all_videos.append(video)
                existing_ids.add(video_id)
    
    # Sort all videos by view count (biggest hits first)
    all_videos.sort(key=lambda x: x.get('view_count') or 0, reverse=True)
    
    # Convert to DiscoveredSong objects
    songs = []
    for video in all_videos[:count]:
        video_id = video.get('id')
        if not video_id:
            continue
        
        title = video.get('title', 'Unknown Title')
        clean_title, artist = extract_artist(title)
        
        # Get best thumbnail
        thumbnails = video.get('thumbnails', [])
        thumbnail_url = None
        if thumbnails:
            for thumb in reversed(thumbnails):
                if thumb.get('url'):
                    thumbnail_url = thumb['url']
                    break
        
        if not thumbnail_url:
            thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
        
        view_count = video.get('view_count') or 0
        year = video.get('_year', 'unknown')
        
        songs.append(DiscoveredSong(
            id=video_id,
            title=clean_title,
            artist=artist,
            language=language,
            duration=video.get('duration', 0),
            thumbnail_url=thumbnail_url,
            youtube_url=f"https://www.youtube.com/watch?v={video_id}",
            view_count=view_count,
            year=year
        ))
        
        print(f"      ★ {clean_title[:40]} ({view_count:,} views)")
    
    return songs


def discover_all_songs(
    languages: Optional[List[str]] = None,
    songs_per_language: int = 3
) -> dict[str, List[DiscoveredSong]]:
    """
    Discover songs for all specified languages.
    Returns dict mapping language to list of songs.
    """
    if languages is None:
        languages = SUPPORTED_LANGUAGES
    
    results = {}
    
    for language in languages:
        print(f"Discovering {songs_per_language} songs for {language}...")
        try:
            songs = discover_songs_for_language(language, count=songs_per_language)
            results[language] = songs
            print(f"  Found {len(songs)} songs for {language}")
        except Exception as e:
            print(f"  Error discovering songs for {language}: {e}")
            results[language] = []
    
    return results


# For testing
if __name__ == "__main__":
    print("Testing discovery service...")
    
    # Test single language
    songs = discover_songs_for_language("english", count=3)
    print(f"\nEnglish songs found: {len(songs)}")
    for song in songs:
        print(f"  - {song.title} ({song.duration}s)")
    
    # Test all languages
    print("\n\nDiscovering all languages...")
    all_songs = discover_all_songs(songs_per_language=2)
    
    total = 0
    for lang, songs in all_songs.items():
        print(f"\n{lang}: {len(songs)} songs")
        for song in songs:
            print(f"  - {song.title}")
        total += len(songs)
    
    print(f"\nTotal songs discovered: {total}")
