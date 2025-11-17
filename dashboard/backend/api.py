"""
FastAPI application for the dashboard backend.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import Optional

from .models import (
    RunListResponse,
    RunDetailResponse,
    StepDetailResponse,
    StartRunRequest,
    StartRunResponse,
    RunStatus,
    GraphResponse,
)
from .scanner import LogScanner
from .runner import get_runner


# Create FastAPI app
app = FastAPI(
    title="Research Pipeline Dashboard API",
    description="API for monitoring and controlling the research pipeline",
    version="1.0.0"
)

# Add CORS middleware for localhost development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",  # Vite default port
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize scanner and runner
scanner = LogScanner()
runner = get_runner()


def _get_current_node_id(run_id: str) -> Optional[str]:
    """Return the id of the node that is currently being explored, if available."""
    # Reconstruct the run directory in the logs folder.
    run_dir = scanner.logs_dir / run_id  # type: ignore[attr-defined]
    current_file = run_dir / "current_node.json"

    if not current_file.exists():
        return None

    try:
        import json

        with current_file.open("r") as f:
            payload = json.load(f)
    except Exception:
        return None

    # Handle both bare and logger-wrapped formats.
    if isinstance(payload, dict):
        data = payload.get("data", payload)
        node_id = data.get("current_node_id")
        if isinstance(node_id, str):
            return node_id

    return None


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Research Pipeline Dashboard API",
        "version": "1.0.0",
        "endpoints": {
            "runs": "/api/runs",
            "run_detail": "/api/runs/{run_id}",
            "step_detail": "/api/runs/{run_id}/step/{step_name}",
            "start_run": "/api/runs/start",
            "run_status": "/api/runs/{run_id}/status",
            "websocket": "/ws/{run_id}"
        }
    }


@app.get("/api/runs", response_model=RunListResponse)
async def list_runs():
    """List all pipeline runs."""
    runs = scanner.get_all_runs()
    return RunListResponse(runs=runs, total=len(runs))


@app.get("/api/runs/{run_id}", response_model=RunDetailResponse)
async def get_run_detail(run_id: str):
    """Get detailed information about a specific run."""
    metadata = scanner.get_run(run_id)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    return RunDetailResponse(metadata=metadata, steps=metadata.steps)


@app.get("/api/runs/{run_id}/step/{step_name}", response_model=StepDetailResponse)
async def get_step_detail(run_id: str, step_name: str):
    """Get detailed data for a specific step in a run."""
    # Get run metadata
    metadata = scanner.get_run(run_id)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    # Find the step
    step_info = None
    for step in metadata.steps:
        if step.step_name == step_name:
            step_info = step
            break
    
    if not step_info:
        raise HTTPException(status_code=404, detail=f"Step {step_name} not found")
    
    # Get step data
    step_data = scanner.get_step_data(run_id, step_name)
    if not step_data:
        step_data = {}
    
    return StepDetailResponse(step_info=step_info, data=step_data)


@app.get("/api/runs/{run_id}/graph", response_model=GraphResponse)
async def get_run_graph(run_id: str):
    """Get the recursive research graph for a specific run."""
    # Load the saved recursive_graph intermediate result
    step_data = scanner.get_step_data(run_id, "recursive_graph")
    if not step_data:
        raise HTTPException(
            status_code=404,
            detail=f"Recursive graph not found for run {run_id}. "
            "Make sure the run completed with collect_graph enabled.",
        )

    data = step_data.get("data") or {}
    root_id = data.get("root_id")
    nodes = data.get("nodes")

    if not isinstance(root_id, str) or not isinstance(nodes, dict):
        raise HTTPException(
            status_code=500,
            detail=f"Malformed recursive graph data for run {run_id}",
        )

    # Start with any metadata saved alongside the graph
    metadata = step_data.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}

    # Enrich metadata with the current node id if available
    current_node_id = _get_current_node_id(run_id)
    if current_node_id:
        metadata = {**metadata, "current_node_id": current_node_id}

    return GraphResponse(
        graph={"root_id": root_id, "nodes": nodes},
        metadata=metadata or None,
    )


@app.post("/api/runs/start", response_model=StartRunResponse)
async def start_run(request: StartRunRequest):
    """Start a new pipeline run."""
    try:
        run_id = await runner.start_run(
            topic=request.topic,
            max_retriever_calls=request.max_retriever_calls,
            max_depth=request.max_depth,
            max_nodes=request.max_nodes,
        )
        
        return StartRunResponse(
            run_id=run_id,
            status=RunStatus.RUNNING,
            message=f"Pipeline started successfully. Run ID: {run_id}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start pipeline: {str(e)}")


@app.get("/api/runs/{run_id}/status")
async def get_run_status(run_id: str):
    """Get the current status of a running pipeline."""
    # First check active runs
    status = runner.get_run_status(run_id)
    if status:
        return status
    
    # If not active, check completed runs
    metadata = scanner.get_run(run_id)
    if metadata:
        return {
            "status": metadata.status,
            "topic": metadata.topic,
            "started_at": metadata.started_at,
            "completed_at": metadata.completed_at,
            "current_step": metadata.current_step
        }
    
    raise HTTPException(status_code=404, detail=f"Run {run_id} not found")


@app.websocket("/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    """WebSocket endpoint for real-time pipeline updates."""
    await websocket.accept()
    
    # Register the connection
    runner.register_websocket(run_id, websocket)
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connection",
            "timestamp": str(datetime.now()),
            "data": {"message": f"Connected to run {run_id}"}
        })
        
        # Keep connection alive and listen for messages
        while True:
            # We just need to keep the connection open
            # The runner will broadcast messages to this websocket
            data = await websocket.receive_text()
            # Echo back for heartbeat
            await websocket.send_json({
                "type": "heartbeat",
                "timestamp": str(datetime.now()),
                "data": {"received": data}
            })
            
    except WebSocketDisconnect:
        runner.unregister_websocket(run_id, websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        runner.unregister_websocket(run_id, websocket)


# Import datetime for websocket endpoint
from datetime import datetime

