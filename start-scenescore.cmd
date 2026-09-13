@echo off
setlocal
cd /d "%~dp0"
echo SceneScore: http://127.0.0.1:5188/scenescore.html
echo Upload a video shorter than 30 seconds. Press Ctrl+C to stop.
node --import tsx tools/scenescore-server.ts
if errorlevel 1 pause
