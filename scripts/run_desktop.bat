@echo off
setlocal
echo ========================================================
echo Starting NOVA AI Trainer Desktop Application (Electron)
echo ========================================================
set PATH=C:\Program Files\nodejs;%PATH%
cd "%~dp0..\apps\desktop"

call node_modules\.bin\electron.cmd dist-electron\main.js
