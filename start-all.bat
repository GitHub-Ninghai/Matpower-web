@echo off
REM MATPOWER Web Platform - Start All Services
echo ========================================
echo MATPOWER Web Platform
echo ========================================
echo.

REM Start backend in new window
echo [1/2] Starting Backend...
start "MATPOWER Backend" cmd /c "cd backend && start.bat"

REM Wait for backend to start
echo Waiting for backend to initialize...
timeout /t 5 /nobreak >nul

REM Start frontend in new window
echo [2/2] Starting Frontend...
start "MATPOWER Frontend" cmd /c "cd frontend && start.bat"

echo.
echo ========================================
echo All services started!
echo ========================================
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo API Docs: http://localhost:8000/docs
echo ========================================
echo.

pause
