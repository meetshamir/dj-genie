"""
Video DJ Playlist Creator - Backend Server

FastAPI application for discovering, analyzing, and exporting video playlists.
"""

import sys
from pathlib import Path

# Add backend directory to path for imports
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import settings
from models.database import init_database
from api.routes import router


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
