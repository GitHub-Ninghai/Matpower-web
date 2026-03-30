#!/bin/bash
# MATPOWER Web Platform - Start All Services

echo "========================================"
echo "MATPOWER Web Platform"
echo "========================================"
echo ""

# Start backend in new terminal
echo "[1/2] Starting Backend..."
if command -v gnome-terminal &> /dev/null; then
    gnome-terminal -- bash -c "cd backend && ./start.sh"
elif command -v xterm &> /dev/null; then
    xterm -e "cd backend && ./start.sh" &
else
    # Start in background
    cd backend && ./start.sh &
    cd ..
fi

# Wait for backend to start
echo "Waiting for backend to initialize..."
sleep 5

# Start frontend in new terminal
echo "[2/2] Starting Frontend..."
if command -v gnome-terminal &> /dev/null; then
    gnome-terminal -- bash -c "cd frontend && ./start.sh"
elif command -v xterm &> /dev/null; then
    xterm -e "cd frontend && ./start.sh" &
else
    # Start in background
    cd frontend && ./start.sh &
    cd ..
fi

echo ""
echo "========================================"
echo "All services started!"
echo "========================================"
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "API Docs: http://localhost:8000/docs"
echo "========================================"
echo ""
