@echo off
setlocal
echo ========================================================
echo Running NOVA AI Trainer Automated Test Suite
echo ========================================================
set PYTHONPATH=%~dp0..
set PATH=C:\Program Files\nodejs;%PATH%

if exist "%USERPROFILE%\miniconda3\python.exe" (
    "%USERPROFILE%\miniconda3\python.exe" -m pytest backend/tests -v
) else if exist "%USERPROFILE%\miniconda3\envs\api\python.exe" (
    "%USERPROFILE%\miniconda3\envs\api\python.exe" -m pytest backend/tests -v
) else (
    pytest backend/tests -v
)
