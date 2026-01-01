"""
Test script for AI-powered DJ Playlist Generator

This script tests the complete flow:
1. User provides a natural language prompt
2. AI recommends songs based on the prompt
3. Songs are searched on YouTube
4. (Optional) Download and create the mix
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))
os.chdir(Path(__file__).parent)

def test_song_recommendation():
    """Test just the song recommendation part (no downloading)"""
    from backend.services.song_recommender import create_playlist_from_prompt
    
    prompt = """
    New Year 2026 party! Goodbye 2025, welcome 2026.
    Hit dance songs from the last 3 years across Hindi, Tamil, Malayalam, Arabic, Turkish and English.
    Include SRK songs across the years like Chaiyya Chaiyya, Lungi Dance.
    Include popular Tamil kuttu songs like Apdi Podu.
    Include some MJ hits like Thriller, Beat It.
    Include recent English hits like Industry Baby, Blinding Lights.
    Include Badshah hits like Kar Gayi Chull, DJ Waley Babu.
    Include Honey Singh like Lungi Dance, Brown Rang.
    Include AR Rahman songs both Tamil and Hindi like Jai Ho, Roja.
    Include Arabic hit Youm Wara Youm.
    Also add 80s/90s classics like Ice Ice Baby, Informer, George Michael, Bryan Adams.
    """
    
    print("=" * 70)
    print("🎵 AI SONG RECOMMENDATION TEST")
    print("=" * 70)
    print(f"\nPrompt: {prompt[:100]}...")
    print("\n⏳ Analyzing prompt with AI...")
    
    plan = create_playlist_from_prompt(prompt, target_duration_minutes=45, find_youtube=True)
    
    if not plan:
        print("❌ Failed to create playlist plan")
        return False
    
    print(f"\n✅ Theme: {plan.theme}")
    print(f"🎭 Mood: {', '.join(plan.mood)}")
    print(f"🎤 DJ Notes: {plan.dj_notes[:100]}...")
    print(f"\n📋 Recommended Songs ({len(plan.songs)} total):")
    print("-" * 70)
    
    by_language = {}
    for song in plan.songs:
        lang = song.language.lower()
        if lang not in by_language:
            by_language[lang] = []
        by_language[lang].append(song)
    
    for lang, songs in sorted(by_language.items()):
        print(f"\n🌍 {lang.upper()} ({len(songs)} songs):")
        for song in songs:
            yt_icon = "✓" if song.youtube_url else "✗"
            print(f"   [{yt_icon}] {song.artist} - {song.title}")
            if song.youtube_url:
                print(f"       🔗 {song.youtube_url}")
    
    found = sum(1 for s in plan.songs if s.youtube_url)
    print(f"\n📊 Summary: Found {found}/{len(plan.songs)} songs on YouTube")
    
    return True


def test_full_generation_preview():
    """Test preview API (shows what would be generated)"""
    from backend.services.song_recommender import create_playlist_from_prompt
    
    # Shorter prompt for quick test
    prompt = """
    Quick party test: Include 3-4 songs only.
    One SRK Bollywood hit.
    One MJ classic.
    One recent English hit.
    """
    
    print("\n" + "=" * 70)
    print("🎬 PREVIEW MODE TEST (No Download)")
    print("=" * 70)
    
    plan = create_playlist_from_prompt(prompt, target_duration_minutes=10, find_youtube=True)
    
    if plan:
        print(f"✅ Would create: '{plan.theme}'")
        print(f"   Songs: {len(plan.songs)}")
        print(f"   Found on YT: {sum(1 for s in plan.songs if s.youtube_url)}")
        return True
    
    return False


if __name__ == "__main__":
    print("\n" + "🎧 " * 20)
    print("    AI DJ PLAYLIST GENERATOR - TEST SUITE")
    print("🎧 " * 20 + "\n")
    
    # Run tests
    success = True
    
    try:
        if not test_song_recommendation():
            success = False
    except Exception as e:
        print(f"❌ Recommendation test failed: {e}")
        import traceback
        traceback.print_exc()
        success = False
    
    try:
        if not test_full_generation_preview():
            success = False
    except Exception as e:
        print(f"❌ Preview test failed: {e}")
        import traceback
        traceback.print_exc()
        success = False
    
    print("\n" + "=" * 70)
    if success:
        print("✅ ALL TESTS PASSED")
        print("\n📝 To generate a full playlist with AI DJ, run:")
        print("   python -c \"")
        print("   from backend.services.auto_playlist import AutoPlaylistGenerator")
        print("   gen = AutoPlaylistGenerator()")
        print("   result = gen.generate_from_prompt('Your party prompt here', 30, 'my_mix')")
        print("   print(result)")
        print("   \"")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 70)
