"""
Test AI DJ Video Export
Creates a 4-song video with AI DJ commentary using Azure OpenAI.
"""
import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, 'backend')

from services.exporter import export_playlist, ExportSegment
from services.azure_dj_voice import DJContext, AZURE_OPENAI_AVAILABLE

def main():
    print('='*60)
    print('AI DJ VIDEO EXPORT TEST')
    print('='*60)
    print(f'Azure OpenAI Available: {AZURE_OPENAI_AVAILABLE}')
    print()

    # Connect to database
    conn = sqlite3.connect('database.sqlite')
    conn.row_factory = sqlite3.Row

    # Pick 4 high-energy segments (one from each language)
    segment_ids = [
        '80e7f10c-a242-4b7a-bafd-cd66ae081bd9',  # English - Dua Lipa Dance The Night
        'c4f9ea42-e15e-46f8-a948-651b89ad1057',  # Hindi - Sidharth & Katrina  
        '91fa0bd1-aeae-46f0-b236-7869f1db3704',  # Malayalam - Adi Kapyare
        'deba3f5a-1f43-4021-bc79-68770c39aaa5',  # Tamil - Vikram Thangalaan
    ]

    # Get segment data
    segments = []
    print('SELECTED SONGS:')
    for i, seg_id in enumerate(segment_ids):
        row = conn.execute('''
            SELECT s.title, s.artist, s.language, s.youtube_url, s.bpm, s.energy_score,
                   seg.start_time, seg.end_time, seg.id as segment_id
            FROM segments seg
            JOIN songs s ON seg.song_id = s.id  
            WHERE seg.id = ?
        ''', (seg_id,)).fetchone()
        
        if row:
            seg = ExportSegment(
                youtube_id=row['youtube_url'].split('v=')[-1].split('&')[0] if row['youtube_url'] else '',
                youtube_url=row['youtube_url'] or '',
                start_time=row['start_time'],
                end_time=row['end_time'],
                song_title=row['title'],
                language=row['language'],
                position=i,
                artist=row['artist'] or 'Unknown',
                bpm=row['bpm'] or 120.0
            )
            segments.append(seg)
            print(f'  {i+1}. [{row["language"]:10}] {row["title"][:50]}')
    
    print()
    print(f'Total segments: {len(segments)}')
    print()

    # Configure DJ context for New Year 2025
    dj_context = {
        'theme': 'New Year 2025 Party - Welcoming 2026!',
        'mood': 'energetic, celebratory, festive, dance',
        'audience': 'party guests ready to dance and celebrate',
        'special_notes': 'Last party of 2025! Make it epic! Reference actors like Sidharth, Katrina, Vikram in the songs!',
        'custom_shoutouts': ['Happy New Year!', '2026 here we come!', 'Bollywood style!']
    }

    print('DJ Context:')
    print(f'  Theme: {dj_context["theme"]}')
    print(f'  Mood: {dj_context["mood"]}')
    print(f'  Notes: {dj_context["special_notes"]}')
    print()

    # Export settings
    output_dir = Path('exports')
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / 'ai_dj_test_newyear.mp4'

    print('Starting export with AI DJ...')
    print('='*60)

    # Progress callback
    def on_progress(progress):
        print(f'[{progress.status.upper():12}] {progress.progress:5.1f}% - {progress.current_step}')

    # Run export
    result = export_playlist(
        segments=segments,
        output_name="ai_dj_test_newyear",
        crossfade_duration=1.5,
        transition_type="random",
        add_text_overlay=True,
        video_quality="720p",
        dj_enabled=True,
        dj_voice='energetic_male',
        dj_frequency='moderate',
        dj_context=dj_context,
        progress_callback=on_progress
    )

    print()
    print('='*60)
    print('EXPORT RESULT:')
    print(f'  Success: {result.success}')
    if result.success:
        print(f'  Output: {result.output_path}')
        print(f'  Duration: {result.duration_seconds:.1f}s')
        print(f'  Size: {result.file_size_bytes / 1024 / 1024:.1f} MB')
    else:
        print(f'  Error: {result.error}')
    print('='*60)

if __name__ == '__main__':
    main()
