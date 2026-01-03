"""
Video DJ Playlist Creator - Backend Server

FastAPI application for discovering, analyzing, and exporting video playlists.
"""

import os
import sys
from pathlib import Path

# Load environment variables from .env file FIRST (before any other imports)
from dotenv import load_dotenv
backend_dir = Path(__file__).parent
load_dotenv(backend_dir / ".env")

# Add FFmpeg to PATH (WinGet installation location)
ffmpeg_paths = [
    Path.home() / "AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.0.1-full_build/bin",
    Path("C:/ffmpeg/bin"),
    Path("C:/Program Files/ffmpeg/bin"),
]
for ffmpeg_path in ffmpeg_paths:
    if ffmpeg_path.exists():
        os.environ["PATH"] = str(ffmpeg_path) + os.pathsep + os.environ.get("PATH", "")
        break

# Add backend directory to path for imports
sys.path.insert(0, str(backend_dir))

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import asyncio

from config import settings
from models.database import init_database
from api.routes import router, export_jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    # Startup
    print(f"Starting {settings.app_name} v{settings.app_version}")
    
    # Ensure directories exist
    settings.ensure_directories()
    print(f"Data directory: {settings.base_dir}")
    
    # Initialize database
    init_database(settings.database_path)
    print(f"Database: {settings.database_path}")
    
    print(f"Server running at http://{settings.host}:{settings.port}")
    print("=" * 50)
    
    yield
    
    # Shutdown
    print("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Automated video DJ playlist creator",
    lifespan=lifespan
)

# Add CORS middleware (for Tauri frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tauri uses tauri://localhost
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")

# Mount static files for exports
exports_dir = settings.base_dir / "exports"
exports_dir.mkdir(parents=True, exist_ok=True)
app.mount("/exports", StaticFiles(directory=str(exports_dir)), name="exports")


# WebSocket endpoint at root level (not under /api prefix)
@app.websocket("/ws/export/{job_id}")
async def websocket_export_progress(websocket: WebSocket, job_id: str):
    """WebSocket for real-time export progress updates."""
    await websocket.accept()
    
    try:
        last_progress = -1
        while True:
            # Check export_jobs dict from routes
            if job_id in export_jobs:
                job = export_jobs[job_id]
                progress = job.get("progress", 0)
                status = job.get("status", "pending")
                
                if progress != last_progress or status in ("complete", "failed"):
                    await websocket.send_json({
                        "job_id": job_id,
                        "status": status,
                        "progress": progress,
                        "current_step": job.get("current_step", ""),
                        "segment_index": job.get("segment_index", 0),
                        "total_segments": job.get("total_segments", 0),
                        "error": job.get("error"),
                        "result": job.get("result")
                    })
                    last_progress = progress
                
                if status in ("complete", "failed"):
                    break
            else:
                await websocket.send_json({
                    "job_id": job_id,
                    "status": "not_found",
                    "error": "Job not found, waiting..."
                })
            
            await asyncio.sleep(0.5)
            
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for job {job_id}")
    except Exception as e:
        print(f"WebSocket error: {e}")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "api": "/api"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
