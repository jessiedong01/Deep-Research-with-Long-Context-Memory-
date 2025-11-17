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
    steps: list[StepInfo] = Field(default_factory=list)


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


class StartRunRequest(BaseModel):
    """Request to start a new pipeline run."""
    topic: str
    max_retriever_calls: int = 1


class StartRunResponse(BaseModel):
    """Response when starting a new run."""
    run_id: str
    status: RunStatus
    message: str


class WebSocketMessage(BaseModel):
    """Message sent via WebSocket during pipeline execution."""
    type: str  # "log", "step_update", "status_change", "error"
    timestamp: datetime
    data: dict[str, Any]

