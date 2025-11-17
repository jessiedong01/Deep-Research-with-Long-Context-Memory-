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
            
            # Check if pipeline completed successfully
            if any("Pipeline completed successfully" in log.get('message', '') for log in log_lines):
                status = RunStatus.COMPLETED
                completed_at = datetime.fromisoformat(last_log['timestamp'])
            # Check if there's an error
            elif any("error" in log.get('level', '').lower() for log in log_lines):
                status = RunStatus.FAILED
                completed_at = datetime.fromisoformat(last_log['timestamp'])
            # Check if final step exists - if so, likely completed even without the success message
            elif (run_dir / "05_final_report.json").exists():
                status = RunStatus.COMPLETED
                completed_at = datetime.fromisoformat(last_log['timestamp'])
            
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
            "05_final_report"
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
        
        steps = []
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
        
        return steps

