@echo off
cd /d C:\Users\saziz\video-dj-playlist\backend
C:\Users\saziz\video-dj-playlist\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 9876
pause
