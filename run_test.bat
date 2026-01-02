@echo off
cd /d C:\Users\saziz\video-dj-playlist
call .venv\Scripts\activate.bat
python test_export_only.py
pause
