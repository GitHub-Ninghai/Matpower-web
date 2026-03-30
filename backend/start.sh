#!/bin/bash
# MATPOWER Web Backend Startup Script

echo "Starting MATPOWER Web Backend..."
echo ""

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 not found. Please install Python 3.9+."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Create exports directory if not exists
mkdir -p exports

# Start the server
echo ""
echo "========================================"
echo "MATPOWER Web Backend"
echo "========================================"
echo "API will be available at: http://localhost:8000"
echo "API docs at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo "========================================"
echo ""

python run.py
