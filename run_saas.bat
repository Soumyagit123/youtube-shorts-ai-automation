@echo off
TITLE Ghost Creator SaaS Launcher
echo 👻 Starting Ghost Creator AI SAAS...

:: Set D drive as the workspace for npm/pip
set npm_config_cache=d:\npm-cache
set npm_config_tmp=d:\npm-tmp
set TEMP=d:\npm-tmp
set TMP=d:\npm-tmp
set PYTHONPATH=%CD%\backend\site-packages;%CD%\backend

:: 1. Start Backend (New window)
start "Ghost Backend" cmd /k "cd backend && py main.py"

:: 2. Start Frontend (New window)
start "Ghost Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ✅ Launcher scripts triggered.
echo 🌐 Frontend: http://localhost:3001 (or 3000)
echo ⚙️ Backend API: http://localhost:8002
echo.
echo 👻 The Aurora Portal is coming online...
pause
