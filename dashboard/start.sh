#!/bin/bash
# Startup script for the dashboard

echo "==============================================="
echo "Research Pipeline Dashboard"
echo "==============================================="
echo ""

# Check if we're in the dashboard directory
if [ ! -f "requirements.txt" ]; then
    echo "Error: Please run this script from the dashboard directory"
    exit 1
fi

# Detect Python command (prefer uv)
if command -v uv &> /dev/null; then
    echo "Using uv"
    RUN_CMD="uv run"
    
    # Check if dependencies are installed
    if ! uv run python -c "import uvicorn" &> /dev/null 2>&1; then
        echo "Installing dashboard dependencies with uv..."
        cd ..
        uv pip install -r dashboard/requirements.txt
        cd dashboard
    fi
elif [ -f "../.venv/bin/python" ]; then
    RUN_CMD="../.venv/bin/python -m"
    PYTHON_CMD="../.venv/bin/python"
    echo "Using virtual environment: .venv"
elif command -v python3 &> /dev/null; then
    RUN_CMD="python3 -m"
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    RUN_CMD="python -m"
    PYTHON_CMD="python"
else
    echo "Error: Python not found"
    exit 1
fi

# Check if uvicorn is available (if not using uv)
if [ -n "$PYTHON_CMD" ]; then
    if ! $PYTHON_CMD -c "import uvicorn" &> /dev/null; then
        echo "Error: uvicorn not found"
        echo ""
        echo "Please install dependencies:"
        echo "  pip install -r requirements.txt"
        exit 1
    fi
fi

# Start backend in background
echo "Starting backend server on http://localhost:8000..."
cd ..
$RUN_CMD uvicorn dashboard.backend.api:app --reload --port 8000 &
BACKEND_PID=$!
cd dashboard

# Wait a moment for backend to start
sleep 2

# Start frontend
echo "Starting frontend server on http://localhost:5173..."
cd frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "==============================================="
echo "Dashboard is starting!"
echo "==============================================="
echo "Backend API:  http://localhost:8000"
echo "Frontend:     http://localhost:5173"
echo "API Docs:     http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers"
echo "==============================================="

# Wait for Ctrl+C
trap "echo 'Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID; exit 0" INT

# Keep script running
wait

