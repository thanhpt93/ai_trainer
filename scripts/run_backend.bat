@echo off
setlocal
echo ========================================================
echo Starting NOVA AI Trainer Backend Service (FastAPI)
echo ========================================================
set PYTHONPATH=%~dp0..
set NOVA_PORT=8000

REM Check for Conda base or api environment python
if exist "%USERPROFILE%\miniconda3\python.exe" (
    "%USERPROFILE%\miniconda3\python.exe" -m backend.app.main --port %NOVA_PORT% --host 127.0.0.1
) else if exist "%USERPROFILE%\miniconda3\envs\api\python.exe" (
    "%USERPROFILE%\miniconda3\envs\api\python.exe" -m backend.app.main --port %NOVA_PORT% --host 127.0.0.1
) else (
    python -m backend.app.main --port %NOVA_PORT% --host 127.0.0.1
)
