#!/bin/bash
echo "Starting MATPOWER Web Platform..."
echo ""
echo "Starting backend..."
cd backend
python run.py &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"
sleep 3
echo "Starting frontend..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173 (check console for actual port)"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both services"
wait
