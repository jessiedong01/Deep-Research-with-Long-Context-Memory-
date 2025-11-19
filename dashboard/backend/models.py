"""
Pydantic models for the dashboard API.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    """Status of a pipeline run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StepStatus(str, Enum):
    """Status of a pipeline step."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelinePhase(str, Enum):
    """Phase of the three-phase pipeline."""
    DAG_GENERATION = "dag_generation"
    DAG_PROCESSING = "dag_processing"
    REPORT_GENERATION = "report_generation"


class StepInfo(BaseModel):
    """Information about a single pipeline step."""
    step_name: str
    step_number: int
    status: StepStatus
    timestamp: Optional[datetime] = None
    data: Optional[dict[str, Any] | list[Any]] = None  # Allow both dict and list
    metadata: Optional[dict[str, Any]] = None


class RunMetadata(BaseModel):
    """Metadata about a pipeline run."""
    run_id: str
    topic: str
    status: RunStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    current_step: Optional[str] = None
    max_retriever_calls: Optional[int] = None
    max_depth: Optional[int] = None
    max_nodes: Optional[int] = None
    max_subtasks: Optional[int] = None
    steps: list[StepInfo] = Field(default_factory=list)
    # Three-phase pipeline support
    current_phase: Optional[PipelinePhase] = None
    phases_complete: list[PipelinePhase] = Field(default_factory=list)
    is_three_phase: bool = False  # Flag to indicate new vs legacy runs


class RunListResponse(BaseModel):
    """Response for listing all runs."""
    runs: list[RunMetadata]
    total: int


class RunDetailResponse(BaseModel):
    """Response for a single run's details."""
    metadata: RunMetadata
    steps: list[StepInfo]


class StepDetailResponse(BaseModel):
    """Response for a single step's details."""
    step_info: StepInfo
    data: dict[str, Any]


class GraphData(BaseModel):
    """Serialized recursive research graph for a run."""

    root_id: str
    nodes: dict[str, dict[str, Any]]


class GraphResponse(BaseModel):
    """Response for a run's recursive research graph."""

    graph: GraphData
    # Free-form metadata (e.g., total_nodes, max_depth, max_nodes, current_node_id, etc.)
    metadata: Optional[dict[str, Any]] = None


class StartRunRequest(BaseModel):
    """Request to start a new pipeline run."""
    topic: str
    max_retriever_calls: int = 1
    max_depth: int = 2
    max_nodes: int = 50
    max_subtasks: int = 10


class StartRunResponse(BaseModel):
    """Response when starting a new run."""
    run_id: str
    status: RunStatus
    message: str


class PhaseInfo(BaseModel):
    """Information about a single pipeline phase."""
    phase: PipelinePhase
    status: StepStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    metrics: Optional[dict[str, Any]] = None  # Phase-specific metrics


class PhaseStatusResponse(BaseModel):
    """Response for phase status."""
    current_phase: Optional[PipelinePhase] = None
    phases: list[PhaseInfo]
    is_three_phase: bool


class WebSocketMessage(BaseModel):
    """Message sent via WebSocket during pipeline execution."""
    type: str  # "log", "step_update", "status_change", "error", "phase_transition"
    timestamp: datetime
    data: dict[str, Any]

