# Video DJ Playlist Creator - Backend

## Quick Start

### 1. Create Virtual Environment

```powershell
cd C:\Users\saziz\video-dj-playlist\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 3. Run the Server

```powershell
python main.py
```

The server will start at `http://localhost:9876`

### 4. Test the API

Open your browser to:
- Swagger UI: http://localhost:9876/docs
- Health Check: http://localhost:9876/api/health

### 5. Discover Songs (Test)

```powershell
# Using curl or Invoke-WebRequest
Invoke-WebRequest -Uri "http://localhost:9876/api/discover/sync" -Method POST -ContentType "application/json" -Body '{"songs_per_language": 3}'
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/health | System health check |
| GET | /api/songs | List all songs |
| GET | /api/songs/{id} | Get song details |
| POST | /api/discover | Start discovery (async) |
| POST | /api/discover/sync | Run discovery (sync) |
| GET | /api/segments/{song_id} | Get segments for song |
| GET | /api/playlists | List playlists |
| POST | /api/playlists | Create playlist |
| POST | /api/playlists/{id}/items | Add segment to playlist |

## Project Structure

```
backend/
├── main.py              # FastAPI application entry point
├── config.py            # Settings and constants
├── requirements.txt     # Python dependencies
├── api/
│   ├── __init__.py
│   └── routes.py        # All API endpoints
├── models/
│   ├── __init__.py
│   └── database.py      # SQLAlchemy models
├── schemas/
│   └── __init__.py      # Pydantic schemas
├── services/
│   ├── __init__.py
│   └── discovery.py     # YouTube song discovery
└── utils/
    └── __init__.py
```

## Data Storage

All data is stored in:
```
C:\Users\saziz\video-dj-playlist\
├── database.sqlite      # SQLite database
├── cache/
│   ├── audio/          # Downloaded audio files
│   ├── video/          # Downloaded video segments
│   └── thumbnails/     # Video thumbnails
└── exports/            # Final rendered playlists
```
