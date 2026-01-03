"""
AI-Powered Song Recommendation Service

Uses Azure OpenAI to interpret natural language prompts and find songs on YouTube.
"""

import os
import json
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

# Azure OpenAI
try:
    from openai import AzureOpenAI
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    AZURE_OPENAI_AVAILABLE = True
except ImportError:
    AZURE_OPENAI_AVAILABLE = False

# YouTube search
try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False


@dataclass
class SongRecommendation:
    """A recommended song with metadata"""
    title: str
    artist: str
    language: str
    era: str  # e.g., "80s", "90s", "2020s", "recent"
    genre: str
    search_query: str  # What to search on YouTube
    youtube_url: Optional[str] = None
    youtube_id: Optional[str] = None
    reason: str = ""  # Why this song was recommended


@dataclass 
class PlaylistPlan:
    """AI-generated playlist plan from user prompt"""
    theme: str
    mood: List[str]
    target_duration_minutes: int
    songs: List[SongRecommendation]
    dj_notes: str  # Notes for DJ commentary
    original_prompt: str


class SongRecommender:
    """AI-powered song recommendation using Azure OpenAI"""
    
    def __init__(self):
        self.client = None
        self.model = "gpt-4o"
        
        if AZURE_OPENAI_AVAILABLE:
            try:
                endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
                
                # Use AAD authentication
                credential = DefaultAzureCredential()
                token_provider = get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")
                
                self.client = AzureOpenAI(
                    azure_endpoint=endpoint,
                    azure_ad_token_provider=token_provider,
                    api_version="2024-02-15-preview"
                )
                print("[RECOMMENDER] Azure OpenAI initialized with AAD auth")
            except Exception as e:
                print(f"[RECOMMENDER] Failed to initialize Azure OpenAI: {e}")
                self.client = None
    
    def parse_prompt(self, user_prompt: str, target_duration: int = 30) -> Optional[PlaylistPlan]:
        """
        Parse a natural language prompt into a playlist plan.
        
        Example prompt:
        "New year party, goodbye 2025! Include SRK songs, Tamil kuttu like Apdi Podu,
         MJ hits, recent English hits like Industry Baby, some Badshah and Honey Singh,
         AR Rahman songs, and 80s/90s classics like Ice Ice Baby, Informer, George Michael"
        """
        if not self.client:
            print("[RECOMMENDER] No Azure OpenAI client available")
            return None
        
        system_prompt = """You are a music expert DJ assistant. Your job is to interpret user requests 
and create a playlist plan with specific song recommendations.

Given a user's description of what kind of music they want, extract:
1. The overall theme/occasion
2. The mood(s) they want
3. Specific artists mentioned
4. Specific songs mentioned
5. Languages/regions mentioned
6. Time periods/eras mentioned
7. Genres mentioned

Then create a list of specific song recommendations that match their request.
The NUMBER of songs should be based on target duration:
- For 30 min: 25-30 songs (1 min segments)
- For 60 min: 50-60 songs  
- For 90 min: 75-90 songs
- For 120 min: 100-120 songs

For each song, provide:
- title: The exact song title
- artist: The artist/band name
- language: The language (english, hindi, tamil, malayalam, arabic, turkish, etc.)
- era: The era (80s, 90s, 2000s, 2010s, 2020s)
- genre: The genre (pop, dance, hip-hop, bollywood, kollywood, etc.)
- search_query: What to search on YouTube to find this song (title + artist + "official video" or "audio")
- reason: Brief reason why this song fits the request

IMPORTANT: 
- Include a good mix based on what they asked for
- For party playlists, prioritize high-energy dance tracks
- Include the specific songs/artists they mentioned
- Add complementary songs that fit the vibe
- Ensure variety in languages if they mentioned multiple

Respond in JSON format:
{
    "theme": "string describing the party/occasion",
    "mood": ["list", "of", "moods"],
    "dj_notes": "Notes for the DJ on how to present this mix - mention key artists, the occasion, etc.",
    "songs": [
        {
            "title": "Song Title",
            "artist": "Artist Name", 
            "language": "language",
            "era": "era",
            "genre": "genre",
            "search_query": "search query for youtube",
            "reason": "why this fits"
        }
    ]
}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"""Create a playlist plan for this request:

"{user_prompt}"

Target duration: approximately {target_duration} minutes of music.
Recommend enough songs to fill this duration (assume ~3-4 minutes per song on average).
"""}
                ],
                temperature=0.7,
                max_tokens=16000  # Increased to handle 100+ songs
            )
            
            content = response.choices[0].message.content
            
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', content)
            if not json_match:
                print(f"[RECOMMENDER] No JSON found in response")
                return None
            
            data = json.loads(json_match.group())
            
            # Parse into PlaylistPlan
            songs = []
            for s in data.get("songs", []):
                songs.append(SongRecommendation(
                    title=s.get("title", "Unknown"),
                    artist=s.get("artist", "Unknown"),
                    language=s.get("language", "english"),
                    era=s.get("era", "2020s"),
                    genre=s.get("genre", "pop"),
                    search_query=s.get("search_query", f"{s.get('title', '')} {s.get('artist', '')} official"),
                    reason=s.get("reason", "")
                ))
            
            plan = PlaylistPlan(
                theme=data.get("theme", "Party Mix"),
                mood=data.get("mood", ["energetic"]),
                target_duration_minutes=target_duration,
                songs=songs,
                dj_notes=data.get("dj_notes", ""),
                original_prompt=user_prompt
            )
            
            print(f"[RECOMMENDER] Created playlist plan: {plan.theme}")
            print(f"[RECOMMENDER] {len(songs)} songs recommended")
            
            return plan
            
        except Exception as e:
            print(f"[RECOMMENDER] Error parsing prompt: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def search_youtube(self, query: str, max_results: int = 1) -> Optional[Dict[str, Any]]:
        """Search YouTube for a song and return video info"""
        if not YT_DLP_AVAILABLE:
            print("[RECOMMENDER] yt-dlp not available")
            return None
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'default_search': 'ytsearch',
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Search YouTube
                result = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
                
                if result and 'entries' in result and result['entries']:
                    video = result['entries'][0]
                    return {
                        'id': video.get('id'),
                        'title': video.get('title'),
                        'url': f"https://www.youtube.com/watch?v={video.get('id')}",
                        'duration': video.get('duration', 0),
                        'channel': video.get('channel', video.get('uploader', 'Unknown'))
                    }
        except Exception as e:
            print(f"[RECOMMENDER] YouTube search error for '{query}': {e}")
        
        return None
    
    def find_youtube_urls(self, plan: PlaylistPlan) -> PlaylistPlan:
        """Find YouTube URLs for all songs in the plan"""
        print(f"[RECOMMENDER] Searching YouTube for {len(plan.songs)} songs...")
        
        found_count = 0
        for i, song in enumerate(plan.songs):
            print(f"[RECOMMENDER] [{i+1}/{len(plan.songs)}] Searching: {song.search_query[:50]}...")
            
            result = self.search_youtube(song.search_query)
            if result:
                song.youtube_url = result['url']
                song.youtube_id = result['id']
                found_count += 1
                print(f"[RECOMMENDER]   ✓ Found: {result['title'][:50]}...")
            else:
                # Try a simpler search
                simple_query = f"{song.title} {song.artist}"
                result = self.search_youtube(simple_query)
                if result:
                    song.youtube_url = result['url']
                    song.youtube_id = result['id']
                    found_count += 1
                    print(f"[RECOMMENDER]   ✓ Found (simple): {result['title'][:50]}...")
                else:
                    print(f"[RECOMMENDER]   ✗ Not found")
        
        print(f"[RECOMMENDER] Found {found_count}/{len(plan.songs)} songs on YouTube")
        return plan


def create_playlist_from_prompt(
    prompt: str,
    target_duration_minutes: int = 30,
    find_youtube: bool = True
) -> Optional[PlaylistPlan]:
    """
    Main entry point: Create a complete playlist plan from a natural language prompt.
    
    Args:
        prompt: Natural language description of desired playlist
        target_duration_minutes: Target playlist duration
        find_youtube: Whether to search for YouTube URLs
    
    Returns:
        PlaylistPlan with song recommendations and YouTube URLs
    """
    recommender = SongRecommender()
    
    # Step 1: Parse the prompt with AI
    plan = recommender.parse_prompt(prompt, target_duration_minutes)
    if not plan:
        return None
    
    # Step 2: Find YouTube URLs (optional)
    if find_youtube:
        plan = recommender.find_youtube_urls(plan)
    
    return plan


# Test function
if __name__ == "__main__":
    test_prompt = """
    New year party 2026! Goodbye 2025, welcome 2026.
    Hit dance songs from the last 3 years across Hindi, Tamil, Malayalam, Arabic, Turkish and English.
    Include SRK songs across the years.
    Include popular Tamil kuttu songs like Apdi Podu.
    Include some MJ hits.
    Include recent English hits and Industry Baby.
    Include Badshah, Honey Singh and AR Rahman songs (both Tamil and Hindi).
    Include Youm Wara Youm.
    Also add 80s/90s classics like Ice Ice Baby, Informer, George Michael, Bryan Adams.
    """
    
    print("=" * 60)
    print("TESTING AI SONG RECOMMENDER")
    print("=" * 60)
    
    plan = create_playlist_from_prompt(test_prompt, target_duration_minutes=45, find_youtube=True)
    
    if plan:
        print("\n" + "=" * 60)
        print(f"PLAYLIST PLAN: {plan.theme}")
        print(f"Mood: {', '.join(plan.mood)}")
        print(f"DJ Notes: {plan.dj_notes[:100]}...")
        print("=" * 60)
        
        for i, song in enumerate(plan.songs):
            yt_status = "✓" if song.youtube_url else "✗"
            print(f"{i+1:2}. [{yt_status}] {song.artist} - {song.title} ({song.language}, {song.era})")
            if song.youtube_url:
                print(f"       {song.youtube_url}")
    else:
        print("Failed to create playlist plan")
