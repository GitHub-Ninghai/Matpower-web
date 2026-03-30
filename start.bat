@echo off
echo Starting MATPOWER Web Platform...
echo.
echo Starting backend...
start "Backend" cmd /k "cd /d E:\matpower-web\backend && python run.py"
timeout /t 3 >nul
echo Starting frontend...
start "Frontend" cmd /k "cd /d E:\matpower-web\frontend && npm run dev"
echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173 (check console for actual port)
echo API Docs: http://localhost:8000/docs
pause
