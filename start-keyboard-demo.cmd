@echo off
setlocal
cd /d "%~dp0"
echo Opening the SceneScore keyboard playground. Press Ctrl+C to stop the server.
node node_modules/vite/bin/vite.js apps/web --host 127.0.0.1 --port 5177 --strictPort --open /keyboard.html
if errorlevel 1 pause
