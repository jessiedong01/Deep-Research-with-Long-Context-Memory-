import dspy

from outline_generation import OutlineGenerationAgent
from presearcher.purpose_generation import PurposeGenerationAgent, IsAnswerableResearchNeed
from presearcher.report_generation import ReportGenerationAgent
from presearcher.subtask_generation import SubtaskGenerationAgent
from utils.dataclass import (
    LiteratureSearchAgentRequest,
    PresearcherAgentRequest,
    PresearcherAgentResponse,
    ReportGenerationRequest,
    ResearchGraph,
    _normalize_question,
)
from utils.literature_search import LiteratureSearchAgent
from utils.logger import get_logger


class PresearcherAgent:
    """Recursive presearcher that builds a DAG of research tasks.

    Each node in the DAG represents a research task. For each node we:
    - Run a literature search
    - Decide if the task is answerable from the current writeup
    - Optionally decompose into subtasks and recurse
    - Generate a report using the literature search results
    """

    def __init__(
        self,
        purpose_generation_agent: PurposeGenerationAgent,
        outline_generation_agent: OutlineGenerationAgent,
        literature_search_agent: LiteratureSearchAgent,
        report_generation_agent: ReportGenerationAgent,
        lm: dspy.LM,
    ):
        # Keep these agents for potential higher-level planning or future use
        self.is_answerable = dspy.Predict(IsAnswerableResearchNeed)
        self.subtask_generation_agent = dspy.Predict(SubtaskGenerationAgent)
        self.purpose_generation_agent = purpose_generation_agent
        self.outline_generation_agent = outline_generation_agent
        self.literature_search_agent = literature_search_agent
        self.report_generation_agent = report_generation_agent
        self.lm = lm
        self.logger = get_logger()

    def _save_graph_snapshot(
        self,
        request: PresearcherAgentRequest,
        graph: ResearchGraph,
        current_node_id: str | None = None,
    ) -> None:
        """Save a snapshot of the research graph for real-time visualization.
        
        This is called after every significant graph state change to enable
        real-time monitoring in the dashboard.
        """
        if not request.collect_graph:
            return
            
        self.logger.save_intermediate_result(
            "recursive_graph",
            graph.to_dict(),
            {
                "root_node_id": graph.root_id or current_node_id,
                "total_nodes": len(graph.nodes),
                "max_depth": request.max_depth,
                "max_nodes": request.max_nodes,
            },
        )

    async def aforward(self, request: PresearcherAgentRequest) -> PresearcherAgentResponse:
        """Run the recursive presearcher and return the root report and DAG."""
        self.logger.info(f"Starting presearcher pipeline for topic: {request.topic}")

        # Log run configuration for this topic so the dashboard can surface it.
        self.logger.save_intermediate_result(
            "00_run_config",
            {
                "topic": request.topic,
                "guideline": request.guideline,
                "max_retriever_calls": request.max_retriever_calls,
                "max_depth": request.max_depth,
                "max_nodes": request.max_nodes,
                "max_subtasks": request.max_subtasks,
            },
        )

        graph = ResearchGraph()
        root_node = graph.get_or_create_node(question=request.topic, parent_id=None, depth=0)
        
        # Save initial graph with root node
        self._save_graph_snapshot(request, graph, root_node.id)

        await self._explore_node(
            request=request,
            graph=graph,
            node_id=root_node.id,
            depth=0,
            ancestor_questions=set(),
        )

        # Prefer the generated report; fall back to the literature writeup if needed.
        root_report = root_node.report or root_node.literature_writeup or ""
        root_cited_documents = list(root_node.cited_documents)

        # Save the full recursive graph for inspection and visualization.
        if request.collect_graph:
            self.logger.save_intermediate_result(
                "recursive_graph",
                graph.to_dict(),
                {
                    "root_node_id": root_node.id,
                    "total_nodes": len(graph.nodes),
                    "max_depth": request.max_depth,
                    "max_nodes": request.max_nodes,
                },
            )

        self.logger.info("Pipeline completed successfully!")

        root_node_id = root_node.id if request.collect_graph else None
        graph_output = graph if request.collect_graph else None

        # Use positional arguments to stay robust to dataclass field order.
        return PresearcherAgentResponse(
            request.topic,
            request.guideline,
            root_report,
            root_cited_documents,
            [],  # rag_responses
            {
                "max_depth": request.max_depth,
                "max_nodes": request.max_nodes,
            },
            root_node_id,
            graph_output,
        )

    async def _explore_node(
        self,
        request: PresearcherAgentRequest,
        graph: ResearchGraph,
        node_id: str,
        depth: int,
        ancestor_questions: set[str] | None = None,
    ) -> None:
        """Recursively explore a node: search, decide, decompose, and report."""
        node = graph.nodes[node_id]
        node.status = "in_progress"

        # Persist the currently active node so the dashboard can highlight it.
        self.logger.save_intermediate_result(
            "current_node",
            {"current_node_id": node.id},
        )
        
        # Save graph snapshot with node in_progress for real-time visualization
        self._save_graph_snapshot(request, graph, node_id)

        if ancestor_questions is None:
            ancestor_questions = set()

        normalized_self = node.normalized_question or _normalize_question(node.question)
        local_ancestors = set(ancestor_questions)
        local_ancestors.add(normalized_self)

        # 1) Literature search for this node's question
        literature_search_request = LiteratureSearchAgentRequest(
            topic=node.question,
            max_retriever_calls=1,
            guideline=request.guideline,
            with_synthesis=True,
        )
        literature_search_results = await self.literature_search_agent.aforward(
            literature_search_request
        )
        node.literature_writeup = literature_search_results.writeup
        node.cited_documents = list(literature_search_results.cited_documents)

        # Log a dedicated root-level literature search step for the dashboard.
        if depth == 0:
            self.logger.save_intermediate_result(
                "00_root_literature_search",
                {
                    "topic": node.question,
                    "writeup": node.literature_writeup,
                    "cited_documents": [
                        doc.to_dict() for doc in node.cited_documents
                    ],
                },
                {
                    "cited_documents_count": len(node.cited_documents),
                },
            )

        # 2) Decide if the task is answerable from the current literature
        reasoning: str | None = None
        try:
            is_answerable_pred = await self.is_answerable.aforward(
                research_need=node.question,
                writeup=literature_search_results.writeup,
                lm=self.lm,
            )
            is_answerable_flag = getattr(is_answerable_pred, "is_answerable", None)
            reasoning = getattr(is_answerable_pred, "reasoning", None)
            if is_answerable_flag is None:
                is_answerable_flag = bool(is_answerable_pred)
        except Exception:
            # Be conservative: if anything goes wrong, treat as not answerable
            is_answerable_flag = False

        node.is_answerable = bool(is_answerable_flag)

        if depth == 0:
            self.logger.save_intermediate_result(
                "01_root_is_answerable",
                {
                    "topic": node.question,
                    "is_answerable": node.is_answerable,
                    "reasoning": reasoning,
                },
            )

        # 3) Optionally decompose into subtasks if not answerable and within limits
        can_decompose = (
            not node.is_answerable
            and depth < request.max_depth
            and len(graph.nodes) < request.max_nodes
        )

        if can_decompose:
            try:
                subtask_generation_response = await self.subtask_generation_agent.aforward(
                    research_task=node.question,
                    max_subtasks=request.max_subtasks,
                    lm=self.lm,
                )
                subtasks = list(getattr(subtask_generation_response, "subtasks", []) or [])
                node.subtasks = subtasks
                node.composition_explanation = getattr(
                    subtask_generation_response, "composition_explanation", None
                )
            except Exception:
                node.subtasks = []
                node.composition_explanation = None

            if depth == 0:
                self.logger.save_intermediate_result(
                    "02_root_subtask_generation",
                    {
                        "topic": node.question,
                        "subtasks": node.subtasks,
                        "composition_explanation": node.composition_explanation,
                    },
                    {
                        "subtasks_count": len(node.subtasks),
                    },
                )

            # Phase 1: Create all child nodes at once (show full branching structure)
            child_node_ids = []
            for subtask in node.subtasks:
                if not subtask:
                    continue

                normalized_child = _normalize_question(subtask)

                # Prevent trivial cycles
                if normalized_child in local_ancestors:
                    continue

                if len(graph.nodes) >= request.max_nodes:
                    break

                child_node = graph.get_or_create_node(
                    question=subtask,
                    parent_id=node.id,
                    depth=depth + 1,
                )
                child_node_ids.append(child_node.id)
            
            # Save graph once with all children visible (as "pending/IDLE")
            if child_node_ids:
                self._save_graph_snapshot(request, graph, node_id)
            
            # Phase 2: Explore each child node sequentially
            for child_id in child_node_ids:
                await self._explore_node(
                    request=request,
                    graph=graph,
                    node_id=child_id,
                    depth=depth + 1,
                    ancestor_questions=local_ancestors,
                )

        # 4) Generate a report for this node using its literature search
        try:
            report_request = ReportGenerationRequest(
                topic=node.question,
                literature_search=literature_search_results,
                is_answerable=node.is_answerable if node.is_answerable is not None else False,
            )
            report_response = await self.report_generation_agent.aforward(report_request)
            node.report = report_response.report
            if report_response.cited_documents:
                node.cited_documents = list(report_response.cited_documents)
        except Exception:
            # Fall back to the literature writeup if report generation fails
            node.report = node.literature_writeup or ""

        node.status = "complete"

        # Save graph snapshot with node complete for real-time visualization
        self._save_graph_snapshot(request, graph, node_id)

        # Also record the most recently completed node as the "current" node.
        self.logger.save_intermediate_result(
            "current_node",
            {"current_node_id": node.id},
        )

