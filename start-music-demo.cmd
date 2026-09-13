@echo off
setlocal
cd /d "%~dp0"
node apps/web/tools/catalog.mjs
if errorlevel 1 goto failed
echo Opening the bouncing staircase music demo. Keep this window open while using it.
echo Press Ctrl+C here to stop the local server.
node node_modules/vite/bin/vite.js apps/web --host 127.0.0.1 --port 5176 --strictPort --open /?review=1
if errorlevel 1 goto failed
exit /b 0
:failed
echo The demo could not start. See the error above.
pause
exit /b 1
