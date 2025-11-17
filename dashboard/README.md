# Research Pipeline Dashboard

A web-based dashboard for monitoring and controlling the research pipeline.

## Structure

- `backend/` - FastAPI backend server
- `frontend/` - React frontend application

## Installation & Setup

### Quick Start

The easiest way to run the dashboard is using the provided startup script:

```bash
# Install dependencies (if not already done)
uv pip install -r dashboard/requirements.txt

# Start dashboard
cd dashboard
./start.sh
```

This will start both the backend (port 8000) and frontend (port 5173) servers.

**Note:** The script automatically detects and uses `uv` if available!

### Manual Setup

#### Backend

1. Install dependencies:

```bash
# With uv (recommended)
uv pip install -r dashboard/requirements.txt

# Or with pip
pip install -r dashboard/requirements.txt
```

2. Start the backend server (from repository root):

```bash
# With uv (recommended)
uv run uvicorn dashboard.backend.api:app --reload --port 8000

# Or with Python
python -m uvicorn dashboard.backend.api:app --reload --port 8000
```

The API will be available at `http://localhost:8000`
API documentation at `http://localhost:8000/docs`

#### Frontend

1. Install dependencies:

```bash
cd dashboard/frontend
npm install
```

2. Start the development server:

```bash
npm run dev
```

The dashboard will be available at `http://localhost:5173`

## Features

- **View All Runs**: Browse all pipeline executions with their status and metadata
- **Run Details**: Examine each step of the pipeline with detailed data
- **Real-Time Monitoring**: Watch pipeline execution in real-time via WebSocket
- **Start New Runs**: Trigger new research tasks from the dashboard

## API Endpoints

- `GET /api/runs` - List all pipeline runs
- `GET /api/runs/{run_id}` - Get run details
- `GET /api/runs/{run_id}/step/{step_name}` - Get step data
- `POST /api/runs/start` - Start a new run
- `GET /api/runs/{run_id}/status` - Get run status
- `WebSocket /ws/{run_id}` - Real-time updates

## Removal

To completely remove the dashboard:

```bash
rm -rf dashboard/
```

This will not affect the core pipeline code in `src/`.
