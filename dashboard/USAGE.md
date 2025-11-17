# Dashboard Usage Guide

## Getting Started

### Prerequisites

- Python 3.11+ with `pip`
- Node.js 18+ with `npm`
- Your research pipeline code in `../src/`

### Installation

1. **Backend Dependencies**

```bash
cd dashboard
pip install -r requirements.txt
```

2. **Frontend Dependencies**

```bash
cd dashboard/frontend
npm install
```

### Running the Dashboard

#### Option 1: Quick Start Script (Recommended)

```bash
cd dashboard
./start.sh
```

This starts both servers automatically. Access the dashboard at `http://localhost:5173`

#### Option 2: Manual Start

**Terminal 1 - Backend:**
```bash
cd /path/to/224v-final-project
python -m uvicorn dashboard.backend.api:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd dashboard/frontend
npm run dev
```

The dashboard will be available at `http://localhost:5173`

## Features

### 1. View All Runs

The homepage displays all your pipeline runs in a table with:
- Status (Completed, Running, Failed, Pending)
- Research topic
- Run ID (timestamped directory name)
- Creation time and duration
- Current step

Click on any run to view its details.

### 2. Run Details

When viewing a run, you'll see:

**Sidebar Navigation:**
- List of all 5 pipeline steps
- Visual status indicators (✓ completed, ⟳ in progress, ✗ failed, ○ pending)
- Timeline of when each step completed

**Main Content:**
- Detailed data for the selected step
- Formatted markdown for reports
- Collapsible sections for cited documents
- Search results and RAG responses

**Step-by-Step Breakdown:**
1. **Purpose Generation** - Research needs identified
2. **Outline Generation** - Report structure
3. **Literature Search** - RAG responses with citations
4. **Report Generation** - Individual reports
5. **Final Report** - Complete synthesized report

### 3. Start New Run

Click "New Run" to start a pipeline execution:

1. **Enter Research Topic** - Your research question
2. **Set Max Retriever Calls** - Budget for literature searches (1-20)
3. **Submit** - Pipeline starts immediately

**Real-Time Monitoring:**
- WebSocket connection shows live progress
- Activity log displays pipeline steps
- Auto-redirect to run details page when complete

## API Endpoints

The backend provides a RESTful API at `http://localhost:8000`:

- `GET /api/runs` - List all runs
- `GET /api/runs/{run_id}` - Get run metadata
- `GET /api/runs/{run_id}/step/{step_name}` - Get step data
- `POST /api/runs/start` - Start new run
- `GET /api/runs/{run_id}/status` - Get run status
- `WebSocket /ws/{run_id}` - Real-time updates

Full API documentation: `http://localhost:8000/docs`

## File Structure

```
dashboard/
├── backend/
│   ├── __init__.py
│   ├── api.py          # FastAPI application
│   ├── models.py       # Pydantic data models
│   ├── scanner.py      # Log directory scanner
│   └── runner.py       # Pipeline execution manager
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Main app with routing
│   │   ├── api.js             # API client
│   │   ├── hooks/
│   │   │   └── useWebSocket.js
│   │   └── components/
│   │       ├── RunsList.jsx
│   │       ├── RunDetail.jsx
│   │       ├── StepViewer.jsx
│   │       └── NewRunForm.jsx
│   └── package.json
├── requirements.txt
├── start.sh
├── README.md
└── USAGE.md
```

## Troubleshooting

### Backend won't start

**Issue:** `ModuleNotFoundError: No module named 'fastapi'`

**Solution:**
```bash
cd dashboard
pip install -r requirements.txt
```

### Frontend won't start

**Issue:** `Cannot find module...`

**Solution:**
```bash
cd dashboard/frontend
npm install
```

### Can't connect to backend

**Issue:** `Failed to fetch runs` or `Connection refused`

**Solution:** Ensure backend is running on port 8000
```bash
curl http://localhost:8000/
```

### WebSocket not connecting

**Issue:** Real-time updates don't work

**Solution:** 
1. Check browser console for errors
2. Ensure backend is running
3. Check firewall settings for localhost:8000

### Old runs not showing

**Issue:** Dashboard doesn't show pipeline runs

**Solution:** Ensure runs exist in `../output/logs/` directory

## Development

### Backend Development

The backend uses FastAPI with hot-reload enabled. Changes to Python files automatically restart the server.

### Frontend Development

The frontend uses Vite with hot-module replacement. Changes reflect immediately in the browser.

### Adding New Features

1. **Backend:** Add endpoints to `api.py`, models to `models.py`
2. **Frontend:** Create components in `components/`, add routes to `App.jsx`
3. **API Client:** Update `api.js` with new API calls

## Cleanup

To completely remove the dashboard:

```bash
rm -rf dashboard/
```

This will not affect your research pipeline in `src/`.

