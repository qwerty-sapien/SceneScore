@echo off
cd /d "%~dp0"
echo Open http://127.0.0.1:8780 after the server starts.
echo Keep this window open. Press Ctrl-C to stop.
if exist ".venv-muse\Scripts\python.exe" (
  ".venv-muse\Scripts\python.exe" tools\muse_test_app.py
) else (
  python tools\muse_test_app.py
)
pause
