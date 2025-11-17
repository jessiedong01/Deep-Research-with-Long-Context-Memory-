"""
Log directory scanner to read existing pipeline runs.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import RunMetadata, RunStatus, StepInfo, StepStatus


class LogScanner:
    """Scans the output/logs directory for pipeline runs."""
    
    def __init__(self, logs_dir: str = "../output/logs"):
        """Initialize the scanner with the logs directory path."""
        # Get absolute path relative to this file
        current_file = Path(__file__).resolve()
        # dashboard/backend/scanner.py -> dashboard -> repo_root
        repo_root = current_file.parent.parent.parent
        self.logs_dir = repo_root / "output" / "logs"
        
    def get_all_runs(self) -> list[RunMetadata]:
        """Get metadata for all pipeline runs."""
        if not self.logs_dir.exists():
            return []
        
        runs = []
        for run_dir in sorted(self.logs_dir.iterdir(), reverse=True):
            if run_dir.is_dir():
                metadata = self._parse_run_directory(run_dir)
                if metadata:
                    runs.append(metadata)
        
        return runs
    
    def get_run(self, run_id: str) -> Optional[RunMetadata]:
        """Get metadata for a specific run."""
        run_dir = self.logs_dir / run_id
        if not run_dir.exists():
            return None
        
        return self._parse_run_directory(run_dir)
    
    def get_step_data(self, run_id: str, step_name: str) -> Optional[dict]:
        """Get data for a specific step in a run."""
        run_dir = self.logs_dir / run_id
        step_file = run_dir / f"{step_name}.json"
        
        if not step_file.exists():
            return None
        
        try:
            with open(step_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading step file {step_file}: {e}")
            return None
    
    def _is_root_node_completed(self, run_dir: Path) -> bool:
        """Check if the root node in recursive_graph.json is completed.
        
        Returns True if the root node has status 'complete' or 'completed'.
        Returns False if the file doesn't exist, can't be parsed, or root is not complete.
        """
        graph_file = run_dir / "recursive_graph.json"
        if not graph_file.exists():
            return False
        
        try:
            with open(graph_file, 'r') as f:
                graph_data = json.load(f)
            
            # Extract the graph structure
            data = graph_data.get('data', {})
            root_id = data.get('root_id')
            nodes = data.get('nodes', {})
            
            if not root_id or not nodes:
                return False
            
            # Get the root node
            root_node = nodes.get(root_id)
            if not root_node:
                return False
            
            # Check if root node status is complete
            root_status = root_node.get('status', '').lower()
            return root_status in ('complete', 'completed')
            
        except Exception as e:
            print(f"Error reading recursive graph from {graph_file}: {e}")
            return False
    
    def _parse_run_directory(self, run_dir: Path) -> Optional[RunMetadata]:
        """Parse a run directory to extract metadata."""
        run_id = run_dir.name
        
        # Read pipeline.jsonl to get logs and timing
        pipeline_log = run_dir / "pipeline.jsonl"
        if not pipeline_log.exists():
            return None
        
        try:
            # Read all log lines
            log_lines = []
            with open(pipeline_log, 'r') as f:
                for line in f:
                    log_lines.append(json.loads(line))
            
            if not log_lines:
                return None
            
            # Extract basic info
            first_log = log_lines[0]
            last_log = log_lines[-1]
            
            created_at = datetime.fromisoformat(first_log['timestamp'])
            
            # Determine status
            status = RunStatus.RUNNING
            completed_at = None
            last_update = datetime.fromisoformat(last_log['timestamp'])
            time_since_update = datetime.now() - last_update
            
            # Check if pipeline completed successfully (most reliable indicator)
            if any("Pipeline completed successfully" in log.get('message', '') for log in log_lines):
                status = RunStatus.COMPLETED
                completed_at = datetime.fromisoformat(last_log['timestamp'])
            # Check if there's an error
            elif any("error" in log.get('level', '').lower() for log in log_lines):
                status = RunStatus.FAILED
                completed_at = datetime.fromisoformat(last_log['timestamp'])
            # Check if run is stale (no updates in last 10 minutes) - mark as failed
            elif time_since_update.total_seconds() > 600:  # 10 minutes
                status = RunStatus.FAILED
                completed_at = last_update
            # For older runs (>2 minutes since last update), check if root node is completed
            # This handles cases where completion message was missed but run finished
            elif time_since_update.total_seconds() > 120:  # 2 minutes
                # Check if the root node in recursive_graph.json is completed
                if self._is_root_node_completed(run_dir):
                    status = RunStatus.COMPLETED
                    completed_at = last_update
            # Otherwise, keep as RUNNING (recursive_graph.json is created at start for real-time updates)
            
            # Extract topic from logs or step files
            topic = "Unknown"
            for log in log_lines:
                if "User research task:" in log.get('message', ''):
                    topic = log['message'].split("User research task: ", 1)[1]
                    break
            
            # If topic not in logs, try to get from purpose generation step
            if topic == "Unknown":
                purpose_file = run_dir / "01_purpose_generation.json"
                if purpose_file.exists():
                    with open(purpose_file, 'r') as f:
                        purpose_data = json.load(f)
                        topic = purpose_data.get('data', {}).get('topic', 'Unknown')
            
            # Parse steps
            steps = self._parse_steps(run_dir, log_lines)

            # Attempt to read run configuration (recursive hyperparameters)
            max_retriever_calls = None
            max_depth = None
            max_nodes = None
            max_subtasks = None
            run_config_file = run_dir / "00_run_config.json"
            if run_config_file.exists():
                try:
                    with open(run_config_file, "r") as f:
                        run_config = json.load(f)
                    cfg = run_config.get("data", {})
                    max_retriever_calls = cfg.get("max_retriever_calls")
                    max_depth = cfg.get("max_depth")
                    max_nodes = cfg.get("max_nodes")
                    max_subtasks = cfg.get("max_subtasks")
                except Exception as e:
                    print(f"Error reading run config from {run_config_file}: {e}")
            
            # Calculate duration
            duration_seconds = None
            if completed_at:
                duration_seconds = (completed_at - created_at).total_seconds()
            
            # Determine current step
            current_step = None
            if status == RunStatus.COMPLETED:
                current_step = "05_final_report"
            else:
                for step in reversed(steps):
                    if step.status == StepStatus.COMPLETED:
                        current_step = step.step_name
                        break
            
            return RunMetadata(
                run_id=run_id,
                topic=topic,
                status=status,
                created_at=created_at,
                started_at=created_at,
                completed_at=completed_at,
                duration_seconds=duration_seconds,
                current_step=current_step,
                max_retriever_calls=max_retriever_calls,
                max_depth=max_depth,
                max_nodes=max_nodes,
                max_subtasks=max_subtasks,
                steps=steps
            )
            
        except Exception as e:
            print(f"Error parsing run directory {run_dir}: {e}")
            return None
    
    def _parse_steps(self, run_dir: Path, log_lines: list[dict]) -> list[StepInfo]:
        """Parse step information from log files."""
        step_names = [
            "01_purpose_generation",
            "02_outline_generation",
            "03_literature_search",
            "04_report_generation",
            "05_final_report",
        ]
        
        # Determine which step is currently in progress by checking logs
        current_step_in_progress = None
        for log in reversed(log_lines):
            message = log.get('message', '')
            if 'Step 1/5: Generating research purposes' in message:
                current_step_in_progress = "01_purpose_generation"
                break
            elif 'Step 2/5: Generating report outline' in message:
                current_step_in_progress = "02_outline_generation"
                break
            elif 'Step 3/5: Conducting literature search' in message:
                current_step_in_progress = "03_literature_search"
                break
            elif 'Step 4/5: Generating individual reports' in message:
                current_step_in_progress = "04_report_generation"
                break
            elif 'Step 5/5: Combining reports' in message:
                current_step_in_progress = "05_final_report"
                break
        
        steps: list[StepInfo] = []
        for i, step_name in enumerate(step_names, 1):
            step_file = run_dir / f"{step_name}.json"
            
            if step_file.exists():
                try:
                    with open(step_file, 'r') as f:
                        step_data = json.load(f)
                    
                    timestamp = datetime.fromisoformat(step_data['timestamp'])
                    
                    steps.append(StepInfo(
                        step_name=step_name,
                        step_number=i,
                        status=StepStatus.COMPLETED,
                        timestamp=timestamp,
                        data=step_data.get('data'),
                        metadata=step_data.get('metadata')
                    ))
                except Exception as e:
                    print(f"Error reading step file {step_file}: {e}")
                    steps.append(StepInfo(
                        step_name=step_name,
                        step_number=i,
                        status=StepStatus.FAILED
                    ))
            else:
                # Step file doesn't exist - check if it's in progress
                if step_name == current_step_in_progress:
                    steps.append(StepInfo(
                        step_name=step_name,
                        step_number=i,
                        status=StepStatus.IN_PROGRESS
                    ))
                else:
                    steps.append(StepInfo(
                        step_name=step_name,
                        step_number=i,
                        status=StepStatus.PENDING
                    ))

        # Add any additional step JSON files (e.g., recursive_graph) that
        # aren't part of the legacy fixed step list.
        existing_names = {step.step_name for step in steps}
        for step_file in sorted(run_dir.glob("*.json")):
            stem = step_file.stem
            if stem in existing_names or stem == "pipeline":
                continue

            try:
                with open(step_file, 'r') as f:
                    step_data = json.load(f)

                timestamp_str = step_data.get("timestamp")
                timestamp = (
                    datetime.fromisoformat(timestamp_str)
                    if isinstance(timestamp_str, str)
                    else None
                )

                steps.append(StepInfo(
                    step_name=stem,
                    step_number=len(steps) + 1,
                    status=StepStatus.COMPLETED,
                    timestamp=timestamp,
                    data=step_data.get("data"),
                    metadata=step_data.get("metadata"),
                ))
            except Exception as e:
                print(f"Error reading additional step file {step_file}: {e}")
                steps.append(StepInfo(
                    step_name=stem,
                    step_number=len(steps) + 1,
                    status=StepStatus.FAILED
                ))

        return steps

