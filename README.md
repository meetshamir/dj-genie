# 🧞‍♂️ DJ Genie - your AI Video Jockey!

> **"Describe Your Vibe. We'll Drop the Beat."**
>
> An AI-powered YouTube video mixing application that creates professional DJ-style party mixes with smooth transitions, beat-aligned cuts, and AI-generated commentary.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![React](https://img.shields.io/badge/React-18-61dafb.svg)
![Azure](https://img.shields.io/badge/Azure-OpenAI-0078d4.svg)
![FFmpeg](https://img.shields.io/badge/FFmpeg-8.0-green.svg)

---

## ⚠️ Legal Disclaimer

**IMPORTANT: This project is for educational and demonstration purposes only.**

This application is designed to showcase what's possible with modern AI technologies, including:
- Large Language Models (GPT-4)
- Text-to-Speech synthesis (Azure OpenAI)
- Audio analysis and beat detection
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

## ✨ Features

### �‍♂️ AI-Powered Wish Granting
Just tell DJ Genie about your party and watch the magic happen! Describe your event, and the AI will:
- Suggest songs based on your theme, mood, and preferences
- Create a cohesive playlist with the right energy flow
- Generate creative DJ commentary for your mix

### 🎬 Professional Video Transitions
- **Fade** - Classic smooth fade between clips
- **Dissolve** - Cinematic dissolve effect
- **Fade to Black** - Professional DJ-style transition
- **Circle Crop** - Dynamic circular reveal
- **Radial Wipe** - Energetic radial transition
- **And more!** (wipeleft, wiperight, smoothleft, etc.)

### 🎵 Smart Audio Mixing
- **3.5-second crossfade** between songs for smooth blending
- **Perfect A/V sync** - Audio and video stay perfectly aligned
- **Music ducking** - Automatically lowers music during DJ commentary

### 🎙️ AI DJ Voice Commentary
Powered by **Azure OpenAI GPT-4** and **Text-to-Speech**:
- **Intro** - Welcomes listeners to your mix
- **Song Introductions** - Introduces each track with flair
- **Transitions** - Hypes up the next song
- **Shoutouts** - Personalized messages for your guests
- **Peak Energy** - Gets the crowd excited at high points

### 🎯 Beat-Aligned Segment Extraction
Using **librosa** for audio analysis:
- Detects beats and tempo (BPM)
- Finds phrase boundaries for natural-sounding cuts
- Uses YouTube's "Most Replayed" data for optimal segment selection
- Never cuts mid-word or mid-lyric

### 🌍 Multi-Language Support
- English, Hindi, Tamil, Malayalam, Arabic, Turkish, Uzbek, and more!
- AI understands and can mix songs from different languages

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
   git clone https://github.com/yourusername/dj-genie.git
   cd dj-genie
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
2. Describe your party:
   > "Create a 10-song New Year's Eve party mix with Bollywood hits, 80s classics, and some EDM bangers. High energy throughout. Shoutouts to Sarah and Mike!"
3. Review the AI's suggested playlist
4. Click **"Approve & Generate 🎧"**
5. Wait for the magic to happen!
6. Download your professional DJ mix

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend** | Python, FastAPI, SQLite |
| **Frontend** | React 18, TypeScript, Vite |
| **AI/LLM** | Azure OpenAI GPT-4 |
| **Text-to-Speech** | Azure OpenAI TTS (gpt-4o-mini-tts) |
| **Audio Analysis** | librosa, numpy |
| **Video Processing** | FFmpeg |
| **Video Download** | yt-dlp |

---

## 🎛️ Configuration

### DJ Voice Settings

| Setting | Options |
|---------|---------|
| Voice Style | `energetic_male`, `smooth_female`, `hype_dj` |
| Frequency | `minimal`, `moderate`, `frequent` |
| Music Duck Level | 20% (during commentary) |
| Voice Boost | 3.0x amplification |

### Transition Settings

| Setting | Default |
|---------|---------|
| Duration | 3.5 seconds |
| Audio Crossfade | Enabled |
| Visual Effect | Random (fade, dissolve, etc.) |

### Video Quality

| Quality | Resolution |
|---------|------------|
| 480p | 854 x 480 |
| 720p | 1280 x 720 (default) |
| 1080p | 1920 x 1080 |

---

## 📁 Project Structure

```
dj-genie/
├── backend/
│   ├── api/
│   │   └── routes.py          # API endpoints
│   ├── services/
│   │   ├── auto_playlist.py   # YouTube search & download
│   │   ├── azure_dj_voice.py  # GPT commentary + TTS
│   │   ├── exporter.py        # Video transitions & mixing
│   │   └── analysis.py        # Beat detection
│   ├── main.py                # FastAPI app
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   └── AIPlaylistPage.tsx  # DJ Genie main page
│   │   └── api.ts
│   └── package.json
├── exports/                   # Generated videos
├── cache/                     # Downloaded videos
└── README.md
```

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

- **OpenAI** for GPT-4 and TTS capabilities
- **FFmpeg** for video processing magic
- **librosa** for audio analysis
- **yt-dlp** for media handling

---

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

**Remember: Use responsibly and respect copyright laws.**

---

## 🤝 Contributing

Contributions are welcome! Please read the contributing guidelines before submitting a PR.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

<p align="center">
  <strong>🧞‍♂️ DJ Genie</strong>
  <br>
  <em>"Describe Your Vibe. We'll Drop the Beat."</em>
  <br><br>
  Made with ❤️ and 🤖 AI
  <br>
  <strong>This is a demonstration of AI capabilities - use responsibly!</strong>
</p>
