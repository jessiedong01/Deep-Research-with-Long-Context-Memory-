"""
Pipeline runner for executing research tasks in the background.
"""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add src to path for imports
current_file = Path(__file__).resolve()
repo_root = current_file.parent.parent.parent
src_path = repo_root / "src"
sys.path.insert(0, str(src_path))

from presearcher.init_pipeline import init_presearcher_agent
from utils.dataclass import PresearcherAgentRequest, PresearcherAgentResponse
from utils.logger import init_logger

from .models import RunStatus, WebSocketMessage


class PipelineRunner:
    """Manages pipeline execution with WebSocket updates."""
    
    def __init__(self):
        """Initialize the pipeline runner."""
        self.active_runs: dict[str, dict] = {}
        self.websocket_connections: dict[str, list] = {}
    
    def register_websocket(self, run_id: str, websocket):
        """Register a WebSocket connection for a run."""
        if run_id not in self.websocket_connections:
            self.websocket_connections[run_id] = []
        self.websocket_connections[run_id].append(websocket)
    
    def unregister_websocket(self, run_id: str, websocket):
        """Unregister a WebSocket connection."""
        if run_id in self.websocket_connections:
            if websocket in self.websocket_connections[run_id]:
                self.websocket_connections[run_id].remove(websocket)
    
    async def broadcast_message(self, run_id: str, message: WebSocketMessage):
        """Broadcast a message to all connected WebSockets for a run."""
        if run_id not in self.websocket_connections:
            return
        
        # Convert message to JSON
        message_json = message.model_dump_json()
        
        # Send to all connected clients
        dead_connections = []
        for ws in self.websocket_connections[run_id]:
            try:
                await ws.send_text(message_json)
            except Exception as e:
                print(f"Error sending WebSocket message: {e}")
                dead_connections.append(ws)
        
        # Clean up dead connections
        for ws in dead_connections:
            self.unregister_websocket(run_id, ws)
    
    async def start_run(
        self,
        topic: str,
        max_retriever_calls: int = 1,
        max_depth: int = 2,
        max_nodes: int = 50,
        max_subtasks: int = 10,
        max_refinements: int = 1,
        test_dag_path: str | None = None,
    ) -> str:
        """
        Start a new pipeline run.
        
        Args:
            topic: The research topic
            max_retriever_calls: Maximum number of retriever calls
            max_depth: Maximum recursion depth
            max_nodes: Maximum total nodes in the graph
            max_subtasks: Maximum subtasks per parent node
            
        Returns:
            run_id: The ID of the started run
        """
        # Create logger to get run_id
        logger = init_logger(name="presearcher", log_dir=str(repo_root / "output" / "logs"))
        run_id = logger.run_timestamp
        
        # Store run info
        self.active_runs[run_id] = {
            "status": RunStatus.RUNNING,
            "topic": topic,
            "started_at": datetime.now(),
            "logger": logger,
            "max_retriever_calls": max_retriever_calls,
            "max_depth": max_depth,
            "max_nodes": max_nodes,
            "max_subtasks": max_subtasks,
            "max_refinements": max_refinements,
            "test_dag_path": test_dag_path,
        }

        if test_dag_path:
            logger.info(f"Run configured to reuse prebuilt DAG: {test_dag_path}")
        
        # Start the pipeline in background
        asyncio.create_task(
            self._run_pipeline(
                run_id=run_id,
                topic=topic,
                max_retriever_calls=max_retriever_calls,
                max_depth=max_depth,
                max_nodes=max_nodes,
                max_subtasks=max_subtasks,
                max_refinements=max_refinements,
                test_dag_path=test_dag_path,
                logger=logger,
            )
        )
        
        return run_id
    
    async def _run_pipeline(
        self,
        run_id: str,
        topic: str,
        max_retriever_calls: int,
        max_depth: int,
        max_nodes: int,
        max_subtasks: int,
        max_refinements: int,
        test_dag_path: str | None,
        logger,
    ):
        """Execute the pipeline and broadcast updates."""
        try:
            # Send start message
            await self.broadcast_message(run_id, WebSocketMessage(
                type="status_change",
                timestamp=datetime.now(),
                data={"status": "running", "message": "Pipeline starting..."}
            ))
            
            # Initialize the presearcher agent
            logger.info("Initializing presearcher agent...")
            presearcher_agent = init_presearcher_agent()
            logger.info("Presearcher agent initialized successfully")
            
            await self.broadcast_message(run_id, WebSocketMessage(
                type="log",
                timestamp=datetime.now(),
                data={"level": "INFO", "message": "Presearcher agent initialized"}
            ))
            
            logger.info(f"User research task: {topic}")
            logger.info(
                f"Pipeline configuration: "
                f"max_retriever_calls={max_retriever_calls}, "
                f"max_depth={max_depth}, "
                f"max_nodes={max_nodes}, "
                f"max_subtasks={max_subtasks}, "
                f"max_refinements={max_refinements}"
            )
            if test_dag_path:
                logger.info(f"Prebuilt DAG path: {test_dag_path}")
            
            # Run the presearcher pipeline
            await self.broadcast_message(run_id, WebSocketMessage(
                type="step_update",
                timestamp=datetime.now(),
                data={"step": "01_purpose_generation", "status": "in_progress"}
            ))
            
            # Create callback to broadcast graph updates via WebSocket
            def on_graph_update(graph_dict: dict, metadata: dict):
                asyncio.create_task(
                    self.broadcast_message(run_id, WebSocketMessage(
                        type="graph_update",
                        timestamp=datetime.now(),
                        data={"graph": graph_dict, "metadata": metadata}
                    ))
                )
            
            presearcher_response: PresearcherAgentResponse = await presearcher_agent.aforward(
                PresearcherAgentRequest(
                    topic=topic,
                    max_retriever_calls=max_retriever_calls,
                    max_depth=max_depth,
                    max_nodes=max_nodes,
                    max_subtasks=max_subtasks,
                    max_refinements=max_refinements,
                    prebuilt_graph_path=test_dag_path,
                ),
                on_graph_update=on_graph_update,
            )
            
            # Save results
            output_dir = repo_root / "output"
            output_dir.mkdir(exist_ok=True)
            output_file = output_dir / "results.json"
            
            logger.info(f"Saving final results to {output_file}")
            with open(output_file, "w") as f:
                json.dump(presearcher_response.to_dict(), f, indent=2)
            
            # Update status
            self.active_runs[run_id]["status"] = RunStatus.COMPLETED
            self.active_runs[run_id]["completed_at"] = datetime.now()
            
            await self.broadcast_message(run_id, WebSocketMessage(
                type="status_change",
                timestamp=datetime.now(),
                data={"status": "completed", "message": "Pipeline completed successfully!"}
            ))
            
            logger.info("=" * 80)
            logger.info(f"Pipeline completed successfully! Results saved to {output_file}")
            logger.info(f"Intermediate results and logs saved to output/logs/")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"Pipeline failed with error: {e}")
            self.active_runs[run_id]["status"] = RunStatus.FAILED
            self.active_runs[run_id]["error"] = str(e)
            
            await self.broadcast_message(run_id, WebSocketMessage(
                type="error",
                timestamp=datetime.now(),
                data={"error": str(e), "message": "Pipeline failed"}
            ))
    
    def get_run_status(self, run_id: str) -> Optional[dict]:
        """Get the status of a run."""
        return self.active_runs.get(run_id)


# Global runner instance
_runner: Optional[PipelineRunner] = None


def get_runner() -> PipelineRunner:
    """Get or create the global runner instance."""
    global _runner
    if _runner is None:
        _runner = PipelineRunner()
    return _runner

