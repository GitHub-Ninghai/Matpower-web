#!/bin/bash
# MATPOWER Web Frontend Startup Script

echo "Starting MATPOWER Web Frontend..."
echo ""

# Check Node.js installation
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js not found. Please install Node.js 18+."
    exit 1
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Create .env file if not exists
if [ ! -f ".env" ]; then
    echo "VITE_API_URL=http://localhost:8000" > .env
    echo "Created .env file with default API URL"
fi

# Start dev server
echo ""
echo "========================================"
echo "MATPOWER Web Frontend"
echo "========================================"
echo "Frontend will be available at: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop the server"
echo "========================================"
echo ""

npm run dev
