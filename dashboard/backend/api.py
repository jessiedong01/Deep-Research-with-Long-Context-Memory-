"""
FastAPI application for the dashboard backend.
"""
import json
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware

current_file = Path(__file__).resolve()
repo_root = current_file.parent.parent.parent
src_path = repo_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from presearcher.init_pipeline import init_presearcher_agent
from presearcher.presearcher import PresearcherAgent
from utils.dataclass import PresearcherAgentRequest

from .models import (
    RunListResponse,
    RunDetailResponse,
    StepDetailResponse,
    StartRunRequest,
    StartRunResponse,
    GenerateDAGRequest,
    SavedDAGListResponse,
    SavedDAGInfo,
    RunStatus,
    GraphResponse,
    PhaseStatusResponse,
    PhaseInfo,
    PipelinePhase,
    StepStatus,
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
# Initialize scanner and runner
scanner = LogScanner()
runner = get_runner()
_test_presearcher_agent: PresearcherAgent | None = None
test_dag_dir = repo_root / "output" / "test_dags"


def _get_test_presearcher_agent() -> PresearcherAgent:
    """Return a cached PresearcherAgent instance for DAG test generation."""
    global _test_presearcher_agent
    if _test_presearcher_agent is None:
        _test_presearcher_agent = init_presearcher_agent()
    return _test_presearcher_agent


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
            "graph": "/api/runs/{run_id}/graph",
            "phases": "/api/runs/{run_id}/phases",
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
    """Get the freshest research graph snapshot for a specific run."""
    run_metadata = scanner.get_run(run_id)
    run_status = run_metadata.status if run_metadata else None

    snapshot_data = scanner.get_step_data(run_id, "dag_processing_snapshot")
    final_data = scanner.get_step_data(run_id, "recursive_graph")

    selected = None
    source = "final"

    if snapshot_data and run_status == RunStatus.RUNNING:
        selected = snapshot_data
        source = "snapshot"
    elif final_data:
        selected = final_data
        source = "final"
    elif snapshot_data:
        # Fallback to snapshot even if run finished but final file missing
        selected = snapshot_data
        source = "snapshot"
    else:
        raise HTTPException(
            status_code=404,
            detail=f"No graph snapshots found for run {run_id}.",
        )

    data = selected.get("data") or {}
    root_id = data.get("root_id")
    nodes = data.get("nodes")

    if not isinstance(root_id, str) or not isinstance(nodes, dict):
        raise HTTPException(
            status_code=500,
            detail=f"Malformed graph data for run {run_id}",
        )

    metadata = selected.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}

    metadata = {**metadata, "graph_source": source}

    current_node_id = _get_current_node_id(run_id)
    if current_node_id:
        metadata["current_node_id"] = current_node_id

    return GraphResponse(
        graph={"root_id": root_id, "nodes": nodes},
        metadata=metadata or None,
    )


@app.post("/api/runs/start", response_model=StartRunResponse)
async def start_run(request: StartRunRequest):
    """Start a new pipeline run."""
    normalized_path: str | None = None
    if request.test_dag_path:
        candidate = Path(request.test_dag_path).expanduser()
        if not candidate.is_absolute():
            candidate = (test_dag_dir / candidate).resolve()
        candidate = candidate.resolve()
        if not candidate.exists():
            raise HTTPException(status_code=400, detail="Saved DAG not found on disk.")
        try:
            candidate.relative_to(test_dag_dir.resolve())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Saved DAG must reside inside the test_dags folder.",
            )
        normalized_path = str(candidate)

    try:
        run_id = await runner.start_run(
            topic=request.topic,
            max_retriever_calls=request.max_retriever_calls,
            max_depth=request.max_depth,
            max_nodes=request.max_nodes,
            max_subtasks=request.max_subtasks,
            test_dag_path=normalized_path,
        )
        
        return StartRunResponse(
            run_id=run_id,
            status=RunStatus.RUNNING,
            message=f"Pipeline started successfully. Run ID: {run_id}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start pipeline: {str(e)}")


@app.post("/api/test/generate-dag", response_model=GraphResponse)
async def generate_test_dag(request: GenerateDAGRequest):
    """Generate a DAG preview without running the full pipeline."""
    import json as _json
    from datetime import datetime as _dt

    if not request.topic.strip():
        raise HTTPException(status_code=400, detail="Topic must not be empty.")

    try:
        presearcher_agent = _get_test_presearcher_agent()
        dag_request = PresearcherAgentRequest(
            topic=request.topic.strip(),
            max_depth=request.max_depth,
            max_nodes=request.max_nodes,
            max_subtasks=request.max_subtasks,
            collect_graph=True,
        )
        graph = await presearcher_agent.dag_generation_agent.generate_dag(dag_request)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate DAG: {exc}") from exc

    graph_dict = graph.to_dict()
    if not graph_dict.get("root_id"):
        raise HTTPException(status_code=500, detail="Generated DAG is missing a root node.")

    # Persist the test DAG to disk
    test_dag_dir.mkdir(parents=True, exist_ok=True)
    timestamp = _dt.now().strftime("%Y%m%d_%H%M%S")
    dag_file = test_dag_dir / f"{timestamp}.json"
    with open(dag_file, "w") as f:
        _json.dump(
            {
                "timestamp": timestamp,
                "topic": request.topic.strip(),
                "max_depth": request.max_depth,
                "max_nodes": request.max_nodes,
                "max_subtasks": request.max_subtasks,
                "graph": graph_dict,
            },
            f,
            indent=2,
        )

    metadata = {
        "total_nodes": len(graph.nodes),
        "max_depth_requested": request.max_depth,
        "max_nodes_requested": request.max_nodes,
        "graph_source": "dag_generation_test",
        "saved_to": str(dag_file),
    }

    return GraphResponse(
        graph=graph_dict,
        metadata=metadata,
    )


@app.get("/api/test/dags", response_model=SavedDAGListResponse)
async def list_saved_dags():
    """List saved test DAGs."""
    dags: list[SavedDAGInfo] = []

    if not test_dag_dir.exists():
        return SavedDAGListResponse(dags=[])

    for dag_path in sorted(test_dag_dir.glob("*.json"), reverse=True):
        topic = None
        timestamp = None
        total_nodes: int | None = None
        try:
            with dag_path.open("r") as f:
                payload = json.load(f)
            if isinstance(payload, dict):
                topic = payload.get("topic")
                timestamp = payload.get("timestamp")
                graph_payload = payload.get("graph") or {}
                nodes = graph_payload.get("nodes")
                if isinstance(nodes, dict):
                    total_nodes = len(nodes)
        except Exception:
            pass

        dags.append(
            SavedDAGInfo(
                filename=dag_path.name,
                path=str(dag_path),
                topic=topic,
                timestamp=timestamp,
                total_nodes=total_nodes,
            )
        )

    return SavedDAGListResponse(dags=dags)


@app.get("/api/test/dags/{filename}", response_model=GraphResponse)
async def get_saved_dag(filename: str):
    """Return the graph data for a saved DAG."""
    dag_path = (test_dag_dir / filename).resolve()
    try:
        dag_path.relative_to(test_dag_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid DAG filename.")

    if not dag_path.exists():
        raise HTTPException(status_code=404, detail="DAG file not found.")

    try:
        with dag_path.open("r") as f:
            payload = json.load(f)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read DAG: {exc}") from exc

    graph_payload = payload.get("graph")
    if not graph_payload:
        raise HTTPException(status_code=500, detail="Saved DAG missing graph payload.")

    metadata = {
        "topic": payload.get("topic"),
        "timestamp": payload.get("timestamp"),
        "saved_path": str(dag_path),
        "total_nodes": len(graph_payload.get("nodes", {})) if isinstance(graph_payload, dict) else None,
    }

    return GraphResponse(graph=graph_payload, metadata=metadata)


@app.get("/api/runs/{run_id}/phases", response_model=PhaseStatusResponse)
async def get_phase_status(run_id: str):
    """Get phase status for a three-phase pipeline run."""
    metadata = scanner.get_run(run_id)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    if not metadata.is_three_phase:
        # For legacy runs, return empty phase info
        return PhaseStatusResponse(
            current_phase=None,
            phases=[],
            is_three_phase=False
        )
    
    # Build phase info from steps and metadata
    phases_info = []
    run_dir = scanner.logs_dir / run_id
    
    # Phase 1: DAG Generation
    phase1_file = run_dir / "00_dag_generation.json"
    if phase1_file.exists():
        try:
            import json
            with open(phase1_file, 'r') as f:
                phase1_data = json.load(f)
            timestamp = datetime.fromisoformat(phase1_data.get('timestamp', ''))
            metrics = phase1_data.get('metadata', {})
            phases_info.append(PhaseInfo(
                phase=PipelinePhase.DAG_GENERATION,
                status=StepStatus.COMPLETED,
                started_at=timestamp,
                completed_at=timestamp,
                metrics=metrics
            ))
        except Exception as e:
            print(f"Error reading phase 1 data: {e}")
    
    # Phase 2: DAG Processing
    phase2_file = run_dir / "01_dag_processed.json"
    if phase2_file.exists():
        try:
            import json
            with open(phase2_file, 'r') as f:
                phase2_data = json.load(f)
            timestamp = datetime.fromisoformat(phase2_data.get('timestamp', ''))
            metrics = phase2_data.get('metadata', {})
            phases_info.append(PhaseInfo(
                phase=PipelinePhase.DAG_PROCESSING,
                status=StepStatus.COMPLETED,
                started_at=timestamp,
                completed_at=timestamp,
                metrics=metrics
            ))
        except Exception as e:
            print(f"Error reading phase 2 data: {e}")
    
    # Phase 3: Report Generation
    phase3_file = run_dir / "02_final_report.json"
    if phase3_file.exists():
        try:
            import json
            with open(phase3_file, 'r') as f:
                phase3_data = json.load(f)
            timestamp = datetime.fromisoformat(phase3_data.get('timestamp', ''))
            metrics = phase3_data.get('metadata', {})
            phases_info.append(PhaseInfo(
                phase=PipelinePhase.REPORT_GENERATION,
                status=StepStatus.COMPLETED,
                started_at=timestamp,
                completed_at=timestamp,
                metrics=metrics
            ))
        except Exception as e:
            print(f"Error reading phase 3 data: {e}")
    
    return PhaseStatusResponse(
        current_phase=metadata.current_phase,
        phases=phases_info,
        is_three_phase=True
    )


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
        response = {
            "status": metadata.status,
            "topic": metadata.topic,
            "started_at": metadata.started_at,
            "completed_at": metadata.completed_at,
            "current_step": metadata.current_step
        }
        # Add phase info for three-phase runs
        if metadata.is_three_phase:
            response["is_three_phase"] = True
            response["current_phase"] = metadata.current_phase
            response["phases_complete"] = metadata.phases_complete
        
        return response
    
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

