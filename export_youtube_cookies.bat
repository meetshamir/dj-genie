@echo off
echo =================================================
echo YouTube Cookie Export Helper
echo =================================================
echo.
echo This script will export YouTube cookies from Edge.
echo.
echo IMPORTANT: You MUST close Microsoft Edge completely before running this!
echo (Check the system tray - Edge often runs in the background)
echo.
pause

echo.
echo Exporting cookies from Edge...
C:\Users\saziz\video-dj-playlist\.venv\Scripts\yt-dlp.exe --cookies-from-browser edge --cookies "C:\Users\saziz\video-dj-playlist\cache\youtube_cookies.txt" --skip-download "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo SUCCESS! Cookies exported successfully.
    echo File: C:\Users\saziz\video-dj-playlist\cache\youtube_cookies.txt
    echo.
    echo You can now use the AI DJ Studio to download videos!
) else (
    echo.
    echo FAILED! Make sure Edge is completely closed.
    echo Try: taskkill /F /IM msedge.exe
    echo Then run this script again.
)

echo.
pause
