"""
Quick test for full AI DJ Playlist generation (download + mix + AI DJ)

This will download a few songs and create a mini mix with AI DJ commentary.
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))
os.chdir(Path(__file__).parent)

def main():
    from backend.services.auto_playlist import AutoPlaylistGenerator
    
    # Short prompt for quick test (only 3-4 songs)
    prompt = """
    Quick New Year test party mix! Include only 4 songs:
    1. One SRK Bollywood song (Chaiyya Chaiyya or any hit)
    2. One Michael Jackson hit (Thriller or Beat It)
    3. One 90s classic (Ice Ice Baby or similar)
    4. One recent English hit (Blinding Lights or similar)
    Make it high energy dance party vibes!
    """
    
    print("=" * 70)
    print("🎧 AI DJ PLAYLIST - FULL GENERATION TEST")
    print("=" * 70)
    print(f"\nPrompt: {prompt.strip()}")
    print("\n⏳ This will:")
    print("   1. Parse the prompt with AI")
    print("   2. Search YouTube for each song")
    print("   3. Download the songs")
    print("   4. Analyze for BPM and energy")
    print("   5. Create optimal mix order")
    print("   6. Add database entries")
    print("   7. Export with AI DJ commentary")
    print("-" * 70)
    
    generator = AutoPlaylistGenerator()
    result = generator.generate_from_prompt(
        prompt=prompt,
        target_duration_minutes=10,  # Short for testing
        segment_duration=50,  # 45-60 second clips to enjoy the best parts
        output_name="ai_test_quick_mix"
    )
    
    print("\n" + "=" * 70)
    print("📊 RESULT:")
    print(f"   Success: {result.success}")
    print(f"   Theme: {result.theme}")
    print(f"   Songs Downloaded: {result.songs_downloaded}")
    print(f"   Total Duration: {result.total_duration:.0f}s")
    print(f"   Playlist ID: {result.playlist_id}")
    print(f"   Export Path: {result.export_path}")
    if result.error:
        print(f"   Error: {result.error}")
    print("=" * 70)
    
    if result.success and result.export_path:
        print(f"\n🎉 SUCCESS! Your AI DJ mix is ready:")
        print(f"   {result.export_path}")
        print("\n   Play it to hear the AI DJ introduce the party!")


if __name__ == "__main__":
    main()
