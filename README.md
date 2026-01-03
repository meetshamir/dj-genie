# 🧞‍♂️ DJ Genie - Your AI Video Jockey!

> **"Describe Your Vibe. We'll Drop the Beat."**

An intelligent AI-powered YouTube video mixing application that creates professional DJ-style party mixes. DJ Genie combines advanced audio signal processing, crowd-sourced engagement data, and large language models to extract the perfect segments, create seamless transitions, and generate authentic culture-aware DJ commentary—just like a real party DJ.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![React](https://img.shields.io/badge/React-18-61dafb.svg)
![Azure](https://img.shields.io/badge/Azure-OpenAI-0078d4.svg)
![FFmpeg](https://img.shields.io/badge/FFmpeg-8.0-green.svg)

---

## 🧠 The Intelligence Behind DJ Genie

What makes DJ Genie special isn't just that it mixes videos—it's **how intelligently** it does it:

### 🎯 Hybrid Segment Intelligence: Heatmaps + Audio Analysis

Finding the *right* part of a song is crucial. DJ Genie uses a **two-signal hybrid approach**:

#### 1️⃣ YouTube "Most Replayed" Heatmaps
YouTube tracks which parts of videos viewers replay most—a powerful signal for what's catchy and memorable. DJ Genie:
- **Extracts heatmap data** from YouTube's viewer engagement metrics
- **Identifies peak replay zones** where viewers keep coming back
- **Focuses on the first 3 minutes** where hooks and choruses typically live
- Uses a **sliding window algorithm** to find the segment with highest average replay intensity

#### 2️⃣ Librosa Audio Energy Analysis  
Real-time audio analysis using signal processing:
- **RMS Energy (Volume Envelope)** - How loud is each part?
- **Spectral Centroid (Brightness)** - How exciting/bright is the sound?
- **Onset Strength (Punch)** - How rhythmic and punchy are the beats?

These three signals are weighted (40% RMS, 30% spectral, 30% onset) and combined into a **composite energy curve** that reveals the song's high-energy peaks.

#### 🔀 The Hybrid Decision
```
If heatmap_energy > 50% of max_audio_energy OR heatmap_popularity > 0.7:
    → Use YouTube's crowd-sourced wisdom (what viewers love)
Else:
    → Use audio analysis peak (loudest/most energetic part)
```

### 🥁 Beat-Aligned Cuts: Never Cut Mid-Lyric

DJ Genie uses **beat tracking** and **phrase boundary detection** to ensure cuts sound natural:

1. **Beat Detection** - Librosa identifies all beats in the song
2. **Phrase Boundary Detection** - Analyzes RMS energy to find natural pauses
3. **Snap-to-Beat Algorithm**:
   - Start time → snaps to nearest beat **after** (let the phrase begin)
   - End time → snaps to nearest beat **before** (let the phrase finish)

This prevents jarring mid-word cuts that make amateur mixes sound choppy.

### ⚡ Energy-Aware Dynamic Segment Duration

Not all songs deserve equal time. DJ Genie dynamically adjusts:

| Energy Level | Segment Duration | Why? |
|--------------|------------------|------|
| High (>80%) | 45-55 seconds | Keep it punchy! High energy doesn't need to linger |
| Medium (50-80%) | 55-70 seconds | Balanced exposure |
| Lower (<50%) | 70-90 seconds | Atmospheric tracks need time to breathe |

### 🎚️ Intelligent Mix Ordering

Songs aren't just shuffled—they're **orchestrated for energy flow**:

1. **BPM Matching** - Minimize tempo jumps between adjacent songs using nearest-neighbor algorithm
2. **Harmonic Relationships** - Detects half-time/double-time matches (80 BPM → 160 BPM feels natural)
3. **Energy Curve Shaping** - Builds a "peak middle" party curve:
   - Start: Medium energy (get people moving)
   - Middle: Peak energy (party climax!)  
   - End: Cool down (graceful exit)
4. **Language Variety** - Prevents more than 2 consecutive same-language tracks

---

## 🎙️ AI DJ: Culture-Aware, Lifelike Commentary

DJ Genie's voice isn't generic robotic announcements—it's a **culturally intelligent DJ persona** powered by Azure OpenAI GPT-4.

### 🌍 Culture-Specific Knowledge

The AI understands cultural context for each language, for example:

| Language | Cultural Vibe | Notable Artists/References |
|----------|---------------|---------------------------|
| **Hindi** | Bollywood magic | Arijit Singh, Shreya Ghoshal, SRK movies |
| **Tamil** | Kollywood beats | Rajinikanth, Vijay, AR Rahman |
| **Malayalam** | Mollywood melodies | Mohanlal, Mammootty, Dulquer |
| **Turkish** | Turkish pop vibes | Tarkan, Sezen Aksu |
| **Arabic** | Middle Eastern grooves | Amr Diab, Nancy Ajram |
| **Uzbek** | Central Asian rhythms | Uzbek folk fusion |

### 🎤 Real DJ Behavior

The AI generates commentary that mirrors what real DJs do:
- **Quick cultural nods**: "SRK vibes!", "Kollywood heat!", "Arey!"
- **Language switches**: Appropriate greetings in the song's language
- **Star callouts**: References famous actors when detected in song titles
- **Punchy delivery**: 5-12 words max (3-5 seconds)—DJs don't ramble!

### 🎵 Intelligent Comment Placement

Comments are placed at musically appropriate moments:
- **Intro**: 1.5 seconds in (during the opening)
- **Song Intros**: 2 seconds after song transition settles
- **Transitions**: 5 seconds before next song (during crossfade)
- **Hype/Peak**: 40% into high-energy segments
- **Outro**: Final 15% of the mix

### 🔊 Professional Audio Mixing

DJ commentary sits perfectly in the mix:
- **Music ducking**: Background music drops to 20% during DJ voice
- **Voice boost**: DJ clips amplified 3x for clarity
- **Crossfade buffer**: 0.3s fade-in/out on ducking for smoothness
- **Overlap prevention**: Minimum 3-second gap between comments

---

## ⚠️ Legal Disclaimer

**IMPORTANT: This project is for educational and demonstration purposes only.**

This application is designed to showcase what's possible with modern AI technologies, including:
- Large Language Models (GPT-4)
- Text-to-Speech synthesis (Azure OpenAI)
- Audio signal processing and beat detection
- Video processing and transitions

**This code is NOT intended for:**
- Downloading copyrighted content without permission
- Creating commercial products from copyrighted material
- Circumventing any DRM or content protection
- Any form of piracy or copyright infringement

**By using this software, you agree to:**
- Only use it with content you have rights to use
- Comply with all applicable copyright laws in your jurisdiction
- Take full responsibility for how you use this tool
- Not hold the authors liable for any misuse

**The authors do not condone piracy or copyright infringement of any kind.**

---

## ✨ Features at a Glance

### 🧞‍♂️ Natural Language Playlist Creation
Just describe your party:
> "Create a 10-song New Year's Eve party mix with Bollywood hits, 80s classics, and EDM. High energy. Shoutouts to Sarah and Mike!"

The AI understands themes, moods, languages, and cultural preferences.

### 🎬 Cinematic Video Transitions
- **Fade** - Classic smooth fade between clips
- **Dissolve** - Cinematic dissolve effect
- **Fade to Black** - Professional DJ-style transition
- **Circle Crop** - Dynamic circular reveal
- **Radial Wipe** - Energetic radial transition
- **Wipe Effects** - Left, right, smooth variations

### 🎵 Professional Audio Engineering
- **3.5-second crossfades** for seamless song blending
- **Beat-synchronized cuts** that respect musical phrases
- **Adaptive music ducking** during DJ commentary
- **A/V sync preservation** throughout the mix

### 🌍 Multi-Language Intelligence
Understands and mixes songs across:
- English, Hindi, Tamil, Malayalam
- Arabic, Turkish, Uzbek
- And more!

---

## 🔬 Technical Deep Dive

### Audio Analysis Pipeline

```
┌──────────────────────────────────────────────────────────────────┐
│                    AUDIO ANALYSIS PIPELINE                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐  │
│  │  YouTube    │    │   librosa        │    │   Hybrid        │  │
│  │  Heatmap    │───▶│   Energy Curve   │───▶│   Decision      │  │
│  │  (Viewers)  │    │   (Audio Signal) │    │   Engine        │  │
│  └─────────────┘    └──────────────────┘    └────────┬────────┘  │
│                                                       │           │
│  ┌────────────────────────────────────────────────────▼────────┐ │
│  │                    BEAT ALIGNMENT                            │ │
│  │  ┌──────────┐   ┌──────────────┐   ┌───────────────────┐    │ │
│  │  │  Beat    │   │  Phrase      │   │  Snap-to-Beat     │    │ │
│  │  │  Track   │──▶│  Boundary    │──▶│  Refinement       │    │ │
│  │  │  (tempo) │   │  Detection   │   │  (start/end)      │    │ │
│  │  └──────────┘   └──────────────┘   └───────────────────┘    │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  OUTPUT: Beat-aligned segment with optimal start/end times        │
└──────────────────────────────────────────────────────────────────┘
```

### Energy Curve Calculation

```python
# Weighted combination of audio features
energy = (
    0.4 × RMS_normalized +      # Volume envelope (40%)
    0.3 × Spectral_centroid +   # Brightness (30%)
    0.3 × Onset_strength        # Rhythmic punch (30%)
)
# Smoothed with moving average kernel to reduce noise
```

### Intelligent Mix Ordering Algorithm

```
┌─────────────────────────────────────────────────────────────┐
│                  MIX ORDERING STRATEGY                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   INPUT: Unordered songs with BPM + Energy scores            │
│                                                              │
│   Step 1: Sort by energy                                     │
│   Step 2: Apply "Peak Middle" curve                          │
│           ┌─────────────────────────────────────┐            │
│           │     ████████████                    │            │
│           │   ██            ██                  │  ← Energy  │
│           │ ██                ████              │            │
│           │█                      ████████      │            │
│           └─────────────────────────────────────┘            │
│            Start    Build-up    Peak    Cool-down            │
│                                                              │
│   Step 3: Minimize BPM jumps (nearest-neighbor)              │
│   Step 4: Ensure language variety (max 2 consecutive)        │
│                                                              │
│   OUTPUT: Optimally ordered playlist                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.9+**
- **Node.js 18+**
- **FFmpeg** (with ffprobe)
- **Azure OpenAI** access (for AI features)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/meetshamir/video-dj-playlist.git
   cd video-dj-playlist
   ```

2. **Set up Python environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\Activate.ps1  # Windows
   # or: source .venv/bin/activate  # Linux/Mac
   
   pip install -r backend/requirements.txt
   ```

3. **Set up Frontend**
   ```bash
   cd frontend
   npm install
   ```

4. **Configure Azure OpenAI** (for AI features)
   
   Set environment variables:
   ```bash
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_DEPLOYMENT=gpt-4
   AZURE_OPENAI_API_VERSION=2024-02-15-preview
   ```

5. **Start the servers**
   ```bash
   # Terminal 1 - Backend
   cd backend
   python -m uvicorn main:app --host 127.0.0.1 --port 9876
   
   # Terminal 2 - Frontend
   cd frontend
   npm run dev
   ```

6. **Open the app**
   Navigate to `http://localhost:5173`

---

## 🎮 How to Use

### Using DJ Genie

1. Open the app at `http://localhost:5173`
2. Describe your party in natural language
3. Have a conversation with the AI to refine your mix
4. Review the AI's suggested playlist
5. Click **"Approve & Generate 🎧"**
6. Wait for the magic to happen!
7. Download your professional DJ mix

### 💬 Example Conversation

Here's a real conversation with DJ Genie creating a New Year's Eve party mix:

---

**You:** Create a video of 20 mins max. Songs should be between 30 and 60 seconds each. The theme is new year party, goodbye 2025, welcome 2026. Call out my friends in the party from time to time.. like say.. hey Karim break a leg.. Friends in the party are Karim, Doni, Halima, Ayesha, Anisha, Remin, Muskaan, SMAT, Daisy, Mehr, Shamir. When turkish, Uzbeki, punjabi songs turn.. call out Karim, Doni, Halima. When malayalam, tamil, hindi songs happen use some catchy words like adipoli or maas or poli or use paaji.. tusi.. bangda or something like that.. you get the gist, use the language and the culture when playing that language's song. Keep your commentary brief, just a few words.. not paragraphs. If you have intro commentary then don't do middle of the song commentary. Keep it random, sometimes intro sometimes in the middle. Hit songs dance numbers only from the last 3 years across hindi, tamil, malyalam, arabic, turkish, uzbekistan and english. Should include SRK songs across the years. Should include some of the most popular tamil kuttu songs like apdi podu. Should include some MJ hits. Should include some recent English hits. Should include industry baby. Should have badshaa, honey singh and some anu malik numbers. Also include AR Rahman songs both tamil and hindi. Should include youm wara youm. And some yester year hits like ice ice baby, informer, george michael, bryan adams, from the 80s, 90s. Mostly hindi songs, 3-5 tamil, Malayalam, Punjabi, Arabic songs, About 10-15 English hits.

---

**🧞‍♂️ DJ Genie:** 🎉 Hey party people! Let's gear up for an unforgettable New Year's bash as we say goodbye to 2025 and welcome 2026 with a bang! I'm here to make sure your playlist is lit and your dance floor stays packed! 💃🕺 Let's get some deets to nail down the perfect playlist:

1. Do you have any specific artists you absolutely love or want me to focus on?
2. Any particular energy level you're aiming for—high-energy all the way or some cool-down moments?
3. What language balance are you looking for? A bit more Hindi or equal parts of everything?
4. Is there a particular vibe or mood you want to create—like nostalgic, futuristic, or just pure party?

Let me know, and I'll whip up a party playlist that'll have you dancing into the new year in style! 🎶✨

---

**You:** mix it up

---

**🧞‍♂️ DJ Genie:** Awesome! 🎉 Let's mix it up for a dynamic party vibe that has something for everyone! We'll blend high-energy dance tracks, nostalgic throwbacks, and a splash of international hits to make this New Year's Eve unforgettable! Here's what I'm thinking:

- **Energy Level**: High-energy with a few nostalgic and chill moments
- **Language Mix**: Mostly Hindi with a good variety of Tamil, Malayalam, Punjabi, Arabic, Turkish, Uzbek, and English
- **Vibe**: Eclectic and celebratory, with shoutouts to keep the energy up and personalized!

Here's a sneak peek of the playlist:

- **SRK Hits**: Gotta have some Shah Rukh Khan magic in there!
- **Tamil & Malayalam Kuttu**: Songs like "Apdi Podu" and other foot-tapping numbers
- **Punjabi Bangers**: A couple of Punjabi tracks to get that bangda vibe going
- **Arabic & Turkish Beats**: Tracks like "Youm Wara Youm" to bring an exotic twist
- **Uzbek Gems**: A surprise hit or two for some cultural flair
- **English Hits**: Including "Industry Baby" and recent chart-toppers
- **Throwback Classics**: "Ice Ice Baby," "Informer," and some Bryan Adams and George Michael
- **Michael Jackson**: Timeless MJ tunes for classic dance moves

And some shoutouts to keep it lively:

- "Hey Karim, break a leg on the dance floor! 🕺"
- "Ayesha, show them your moves! 💃"
- "Apdi podu, paaji! Tusi rock the floor, Doni! 🇮🇳"
- "Let's see those moves, Halima! Maas! 🎉"
- "Dance like no one's watching, Muskaan! 🎶"

Does this sound like the party mix you're looking for? Ready to create the playlist to kick off the new year with a bang? 🚀✨

---

**You:** yes

---

**🧞‍♂️ DJ Genie:** Fantastic! 🎉 Let's lock in this electrifying party playlist to celebrate the New Year with flair!

*[DJ Genie generates a complete playlist with songs, transitions, and personalized shoutouts...]*

Let's get this party started and make it a night to remember! 🎊 Happy New Year to you and your friends! 🎆

---

The AI then generates a 20-minute video mix with all your requested songs, smooth transitions, and culture-aware DJ commentary calling out your friends by name!

---

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend** | Python, FastAPI, SQLite | API server and data persistence |
| **Frontend** | React 18, TypeScript, Vite | Modern reactive UI |
| **AI/LLM** | Azure OpenAI GPT-4 | Playlist generation, DJ commentary |
| **Text-to-Speech** | Azure OpenAI TTS (gpt-4o-mini-tts) | Lifelike DJ voice synthesis |
| **Audio Analysis** | librosa, numpy, scipy | Beat detection, energy analysis, phrase boundaries |
| **Video Processing** | FFmpeg | Transitions, crossfades, overlays |
| **Video Download** | yt-dlp | YouTube video/heatmap extraction |

### Key Libraries

| Library | Role in DJ Genie |
|---------|------------------|
| **librosa** | BPM detection, beat tracking, RMS energy, spectral analysis |
| **scipy** | Peak detection for phrase boundary finding |
| **numpy** | Signal processing, sliding window algorithms |
| **yt-dlp** | Video download + extraction of "Most Replayed" heatmap data |
| **FFmpeg** | Video transitions (xfade), audio ducking, crossfades |

---

## 🎛️ Configuration

### DJ Voice Settings

| Setting | Options |
|---------|---------|
| Voice Style | `energetic_male`, `smooth_female`, `hype_dj` |
| Frequency | `minimal`, `moderate`, `frequent` |
| Music Duck Level | 20% (during commentary) |
| Voice Boost | 3.0x amplification |

### Segment Analysis Settings

| Setting | Default | Description |
|---------|---------|-------------|
| Min Segment Duration | 45 seconds | Shortest allowed segment |
| Max Segment Duration | 90 seconds | Longest allowed segment |
| Analysis Window | First 3 minutes | Focus area for heatmap + energy analysis |
| Beat Snap Range | ±5 seconds | How far to search for beat boundaries |

### Transition Settings

| Setting | Default |
|---------|---------|
| Crossfade Duration | 3.5 seconds |
| Audio Crossfade | Enabled |
| Visual Effect | Random (fade, dissolve, etc.) |

### Video Quality

| Quality | Resolution |
|---------|------------|
| 480p | 854 × 480 |
| 720p | 1280 × 720 (default) |
| 1080p | 1920 × 1080 |

---

## 📁 Project Structure

```
dj-genie/
├── backend/
│   ├── api/
│   │   └── routes.py              # REST API endpoints
│   ├── services/
│   │   ├── analysis.py            # 🎯 Audio energy & beat detection (librosa)
│   │   ├── auto_playlist.py       # 🧠 Hybrid segment selection (heatmap + energy)
│   │   ├── azure_dj_voice.py      # 🎙️ GPT-4 DJ commentary + TTS
│   │   ├── exporter.py            # 🎬 Video transitions & mixing
│   │   ├── mixer.py               # 🎚️ Intelligent mix ordering (BPM/energy)
│   │   ├── song_recommender.py    # 🎵 AI playlist planning
│   │   └── downloader.py          # ⬇️ YouTube video + heatmap extraction
│   ├── main.py                    # FastAPI application
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   └── AIPlaylistPage.tsx # DJ Genie chat interface
│   │   └── api.ts                 # Backend API client
│   └── package.json
├── exports/                       # Generated video mixes
├── cache/                         # Downloaded videos & analysis cache
└── README.md
```

### Service Responsibilities

| Service | Intelligence |
|---------|-------------|
| **analysis.py** | Calculates composite energy curves, detects BPM, finds beat times |
| **auto_playlist.py** | Hybrid heatmap+energy segment selection, beat-aligned cuts |
| **azure_dj_voice.py** | Culture-aware GPT commentary, intelligent comment placement |
| **mixer.py** | BPM-smooth ordering, energy curve shaping, language variety |
| **exporter.py** | FFmpeg orchestration, crossfades, music ducking |

---

## 🔧 Troubleshooting

### "Video won't play"
- Ensure FFmpeg is installed and in PATH
- Check that all source videos downloaded successfully
- Look for A/V sync warnings in the console

### "DJ voice not audible"
- Verify Azure OpenAI credentials are set
- Check that TTS generation succeeded in logs
- Music ducking should reduce music to 20% during commentary

### "Transitions not visible"
- Ensure `create_transition_concat` is being used (not `simple_concat`)
- Transition duration is 3.5 seconds
- Check FFmpeg supports the xfade filter

### "Download failed"
- YouTube may require authentication cookies (see below)
- Check for rate limiting (wait a few minutes and try again)
- Ensure yt-dlp is up to date: `pip install -U yt-dlp`

---

## 🍪 YouTube Authentication (Cookies)

YouTube sometimes requires authentication to access videos. If downloads fail, you'll need to export your browser cookies:

### Option 1: Automatic (Windows + Edge)
```bash
# Close Edge completely first (check system tray!)
.\export_youtube_cookies.bat
```

### Option 2: Python Script
```bash
python export_cookies.py
```

### Option 3: Manual Export
1. Install browser extension: **"Get cookies.txt LOCALLY"** ([Chrome](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc))
2. Go to https://www.youtube.com and ensure you're logged in
3. Click the extension → Export
4. Save to `cache/youtube_cookies.txt`

**Note:** Cookies expire periodically. Re-export if downloads start failing again.

---

## 🙏 Acknowledgments

- **Azure OpenAI** for GPT-4 and TTS capabilities that power culture-aware DJ commentary
- **librosa** - The backbone of our audio intelligence (BPM, beats, energy analysis)
- **FFmpeg** - Rock-solid video processing and transitions
- **yt-dlp** - Video downloads and "Most Replayed" heatmap extraction
- **scipy** - Signal processing for phrase boundary detection

---

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

**Remember: Use responsibly and respect copyright laws.**

---

## 🤝 Contributing

Contributions are welcome! Areas where you can help:

- **Audio Analysis** - Improve segment selection algorithms
- **Cultural Intelligence** - Add more language/culture profiles for DJ commentary
- **Beat Detection** - Better phrase boundary detection
- **New Transitions** - FFmpeg xfade effects

### How to Contribute

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/better-beat-detection`)
3. Commit your changes (`git commit -m 'Improve phrase boundary detection'`)
4. Push to the branch (`git push origin feature/better-beat-detection`)
5. Open a Pull Request

---

<p align="center">
  <strong>🧞‍♂️ DJ Genie</strong>
  <br>
  <em>"Describe Your Vibe. We'll Drop the Beat."</em>
  <br><br>
  <strong>Intelligent segment extraction • Beat-aligned cuts • Culture-aware DJ</strong>
  <br><br>
  Made with ❤️ and 🤖 AI
  <br>
  <strong>This is a demonstration of AI capabilities - use responsibly!</strong>
</p>
