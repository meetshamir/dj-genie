@echo off
echo =================================================
echo DJ Genie - YouTube Cookie Export Helper
echo =================================================
echo.
echo This script will export YouTube cookies from Edge.
echo.
echo IMPORTANT: You MUST close Microsoft Edge completely before running this!
echo (Check the system tray - Edge often runs in the background)
echo.
pause

REM Get script directory
set SCRIPT_DIR=%~dp0

echo.
echo Exporting cookies from Edge...
"%SCRIPT_DIR%.venv\Scripts\yt-dlp.exe" --cookies-from-browser edge --cookies "%SCRIPT_DIR%cache\youtube_cookies.txt" --skip-download "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo SUCCESS! Cookies exported successfully.
    echo File: %SCRIPT_DIR%cache\youtube_cookies.txt
    echo.
    echo You can now use DJ Genie to download videos!
) else (
    echo.
    echo FAILED! Make sure Edge is completely closed.
    echo Try: taskkill /F /IM msedge.exe
    echo Then run this script again.
)

echo.
pause
