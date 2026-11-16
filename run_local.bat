@echo off
title WheatVision Local Server
echo ==========================================================
echo           Starting WheatVision AI Application
echo ==========================================================
echo.
echo Opening browser at http://127.0.0.1:5000 ...
start http://127.0.0.1:5000
echo.
echo Starting Flask backend with ONNX models and local SQLite database...
echo Press Ctrl+C in this window to stop the server when done.
echo.
cd /d "%~dp0backend"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" app.py
) else (
    python app.py
)
pause
