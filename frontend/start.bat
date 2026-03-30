@echo off
REM MATPOWER Web Frontend Startup Script
echo Starting MATPOWER Web Frontend...
echo.

REM Check Node.js installation
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found. Please install Node.js 18+.
    pause
    exit /b 1
)

REM Install dependencies if needed
if not exist "node_modules" (
    echo Installing dependencies...
    npm install
)

REM Create .env file if not exists
if not exist ".env" (
    echo VITE_API_URL=http://localhost:8000 > .env
    echo Created .env file with default API URL
)

REM Start dev server
echo.
echo ========================================
echo MATPOWER Web Frontend
echo ========================================
echo Frontend will be available at: http://localhost:5173
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

npm run dev
