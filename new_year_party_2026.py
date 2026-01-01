#!/usr/bin/env python3
"""
🎉 NEW YEAR 2026 PARTY MIX - THE REAL DEAL! 🎉
120 minutes of pure fire - Goodbye 2025, Welcome 2026!

Features:
- 120 minutes max duration
- 45-90 second segments based on energy
- Multi-language: Hindi, Tamil, Malayalam, Arabic, Turkish, Uzbek, English
- SRK hits across the years
- MJ classics
- AR Rahman magic
- Badshah, Honey Singh, Anu Malik bangers
- 80s/90s throwbacks
- Recent English hits
- Personalized friend callouts with cultural flair!
"""

import sys
import os
from pathlib import Path

# Setup paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "backend"))
os.chdir(project_root)

from services.auto_playlist import AutoPlaylistGenerator

def main():
    print("=" * 80)
    print("🎉 NEW YEAR 2026 PARTY MIX - GOODBYE 2025! 🎉")
    print("=" * 80)
    print()
    
    # The MEGA prompt with all requirements
    prompt = """
    🎊 NEW YEAR 2026 PARTY MIX - Goodbye 2025, Welcome 2026! 🎊
    
    This is THE party of the year! Create a 120-minute high-energy dance mix.
    
    === SONG REQUIREMENTS ===
    
    IMPORTANT: We need 100-120 songs total for 120 minutes! Include LOTS of regional songs!
    
    BOLLYWOOD/HINDI (40-50 songs):
    - Shah Rukh Khan hits across ALL years: Chaiyya Chaiyya, Lungi Dance, Chaleya, Jhoome Jo Pathaan, Gerua, Tujhe Dekha To, Bole Chudiyan, Koi Mil Gaya, Zara Sa Jhoom Loon Main
    - Badshah bangers: Genda Phool, Paani Paani, DJ Waley Babu, Kar Gayi Chull, Mercy, She Move It Like
    - Honey Singh: Blue Eyes, Lungi Dance, Angrezi Beat, Desi Kalakaar, Love Dose, Brown Rang
    - Anu Malik classics: Dhoom Machale, Tip Tip Barsa Paani, Taal Se Taal, Nazar Ke Saamne
    - AR Rahman Hindi: Chaiyya Chaiyya, Jai Ho, Dil Se Re, Roja Jaaneman, Tere Bina, Khwaja Mere Khwaja, Rang De Basanti
    - Recent Bollywood hits from 2022-2025
    - Aashiqui songs, 90s Bollywood dance numbers
    
    TAMIL (10-12 songs) - KUTHU KUTHU! 🔥:
    - AR Rahman Tamil: Muqabla, Urvashi Urvashi, Mustafa Mustafa, Chaiyya Chaiyya Tamil version
    - Anirudh bangers: Vaathi Coming, Arabic Kuthu, Rowdy Baby, Why This Kolaveri Di, Aaluma Doluma
    - Vijay mass: Kutty Story, Verithanam, Selfie Pulla, Vaadi Vaadi, Villu songs
    - Rajini: Oruvan Oruvan, Style, Aathichudi, Neruppu Da
    - Dhanush: Kolaveri Di, Rowdy Baby, Po Po, Yennai Maatrum Kadhale
    - Simbu: Beep Song, Vaanam, Manmadha songs
    - Classic Tamil party: Appadi Podu, En Peru Padayappa, Otha Sollala
    
    MALAYALAM (8-10 songs) - ADIPOLI TIME! 🌴:
    - Mass songs: Illuminati (Aavesham), Jimmiki Kammal, Thudakkam Mangalyam, Kalakkatha
    - Sushin Shyam: Thee Minnal (Minnal Murali), Karikku songs
    - Prithviraj/Mohanlal: Aadu songs, Lucifer songs, Bangalore Days
    - Classic: Kilimanjaro, Appangalembadum, Premam songs, Oru Adaar Love songs
    - Recent hits: Romancham songs, Bheeshma Parvam songs, 2018 movie songs
    - Vineeth Sreenivasan hits: Arikil Oraal, Thallipoli, Udan Panam
    
    PUNJABI (10-12 songs) - BALLE BALLE! 💃:
    - Diljit Dosanjh: GOAT, Born to Shine, Lover, Do You Know, Proper Patola, Laembadgini, 5 Taara
    - AP Dhillon: Excuses, Brown Munde, Summer High, Insane, With You
    - Sidhu Moosewala: 295, So High, Tochan, Legend
    - Guru Randhawa: High Rated Gabru, Lahore, Made in India, Slowly Slowly
    - Classic Bhangra: Mundian To Bach Ke, Tunak Tunak Tun, Bolo Ta Ra Ra
    - Jazzy B, Daler Mehndi hits
    - Karan Aujla: Softly, Players, 52 Bars
    
    ARABIC (8-10 songs) - HABIBI PARTY! 🕌:
    - Youm Wara Youm (Samira Said & Cheb Mami) - MUST HAVE!
    - Amr Diab: Tamally Maak, Nour El Ain, Leily Nahary, Habibi Ya Nour El Ain
    - Nancy Ajram: Ah W Noss, Ya Tabtab, Fi Hagat
    - Elissa: Aa Bali Habibi, Bastanak, Ahwak
    - Khaled: Aicha, Didi, C'est La Vie
    - Arabic pop classics from 2000s
    - Egyptian Mahraganat party songs
    - Saad Lamjarred: Lm3allem, Ghaltana
    
    TURKISH (5-6 songs) - ÇILGIN PARTI! 🇹🇷:
    - Tarkan: Şımarık (Kiss Kiss), Dudu, Kuzu Kuzu, Simarik, Hüp
    - Sezen Aksu: Geri Dön, Firuze
    - Modern Turkish pop: Hadise, Tarkan recent hits
    - Classic Turkish dance: Istanbul, Kara Sevda soundtrack songs
    
    UZBEK (3-4 songs) - TASHKENT VIBES! 🎵:
    - Popular Uzbek dance hits: Davraga Tush
    - Osman Navruzov: Lyubimaya, Shirin Salom
    - Yulduz Usmonova hits
    - Modern Uzbek pop bangers
    
    ENGLISH (8-10 songs only - focus more on regional!):
    - Michael Jackson: Thriller, Beat It, Billie Jean, Smooth Criminal, Bad
    - 80s/90s classics: Ice Ice Baby (Vanilla Ice), Informer (Snow), Summer of 69
    - Recent hits: Industry Baby (Lil Nas X), Blinding Lights, 24K Magic
    - Keep English limited - we want MORE regional variety!
    
    === MUSIC STYLE ===
    - High energy dance numbers ONLY
    - Party anthems, no slow songs
    - Mix of nostalgic classics and recent bangers
    - Build energy through the night, peak around 60-80 minutes, gradual cooldown at end
    - PRIORITIZE Tamil, Malayalam, Punjabi, Arabic songs over English!
    """
    
    # Friends to shout out during the party
    friends = [
        "Karim", "Doni", "Halima",  # For Turkish/Uzbek/Punjabi songs
        "Ayesha", "Anisha", "Remin", 
        "Muskaan", "SMAT", "Daisy", 
        "Mehr", "Shamir"
    ]
    
    # Special DJ instructions for cultural callouts
    dj_instructions = """
    PARTY HOST INSTRUCTIONS:
    
    🎤 FRIEND CALLOUTS (randomly throughout, keep brief!):
    - Call out friends by name occasionally: "Hey Karim!", "Doni, break a leg!", "Halima, dance time!"
    - Mix it up - sometimes intro, sometimes middle of song
    - Don't overdo it - just a few per hour
    
    🌍 CULTURAL FLAVOR (match the language!):
    - Hindi songs: "Arey yaar!", "Kya baat hai!", "Let's go!", "Jhoom baby!"
    - Tamil songs: "Maas da!", "Thala vera level!", "Kuthu time!", "Semma!"
    - Malayalam songs: "Adipoli!", "Poli sanam!", "Pwoli!", "Kollam mone!", "Kalakkals!"  
    - Punjabi: "Balle balle!", "Oye hoye!", "Paaji!", "Tusi great ho!", "Bangda te naach!"
    - Turkish/Uzbek: "Karim, Doni, Halima - çok güzel!", "This is YOUR jam!"
    - Arabic: "Yalla habibi!", "Ahlan wa sahlan!", "Mabrouk!"
    
    🎯 DJ STYLE:
    - Keep it SHORT - 5-10 words max per comment
    - Be energetic but not cheesy
    - Sometimes intro, sometimes middle, keep it random
    - Reference the New Year: "2026 loading!", "Last dance of 2025!", "New year new vibes!"
    - For regional songs, USE LOCAL LANGUAGE phrases!
    
    FRIENDS AT THE PARTY: Karim, Doni, Halima, Ayesha, Anisha, Remin, Muskaan, SMAT, Daisy, Mehr, Shamir
    
    SPECIAL: When playing Arabic/Turkish songs, call out Karim, Doni, Halima specifically!
    When playing Malayalam songs, say "Adipoli!" or "Poli!"
    When playing Tamil songs, say "Mass!" or "Thala!"
    When playing Punjabi songs, say "Balle balle!" or "Paaji!"
    """
    
    # Create the generator
    generator = AutoPlaylistGenerator(
        downloads_dir=str(project_root / "downloads"),
        exports_dir=str(project_root / "exports")
    )
    
    print("🎵 Starting the MEGA party mix generation...")
    print(f"📁 Downloads: {generator.downloads_dir}")
    print(f"📁 Exports: {generator.exports_dir}")
    print()
    print("⚠️  This will take a LONG time (120 min = ~80-100 songs)")
    print("⚠️  Make sure you have stable internet and enough disk space!")
    print()
    
    # Generate the playlist
    result = generator.generate_from_prompt(
        prompt=prompt,
        target_duration_minutes=120,  # 2 hours!
        segment_duration=60,  # Base 60s, but will vary 45-90s based on energy
        output_name="new_year_2026_party_mix",
        custom_shoutouts=friends,
        dj_special_notes=dj_instructions
    )
    
    print()
    print("=" * 80)
    print("🎉 PARTY MIX GENERATION COMPLETE! 🎉")
    print("=" * 80)
    print()
    print(f"✅ Success: {result.success}")
    print(f"🎨 Theme: {result.theme}")
    print(f"🎵 Songs Downloaded: {result.songs_downloaded}")
    print(f"⏱️  Total Duration: {result.total_duration / 60:.1f} minutes")
    print(f"📋 Playlist ID: {result.playlist_id}")
    print(f"🎬 Export Path: {result.export_path}")
    
    if result.error:
        print(f"❌ Error: {result.error}")
    
    if result.export_path and Path(result.export_path).exists():
        size_mb = Path(result.export_path).stat().st_size / (1024 * 1024)
        print(f"📦 File Size: {size_mb:.1f} MB")
        print()
        print("🎊 Your New Year 2026 party mix is ready!")
        print(f"🎬 Play it: {result.export_path}")
    
    return result


if __name__ == "__main__":
    result = main()
    sys.exit(0 if result.success else 1)
