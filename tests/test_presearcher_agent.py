"""Test suite for the recursive PresearcherAgent and its request/response types."""

from types import SimpleNamespace

import pytest
from unittest.mock import Mock

from outline_generation import OutlineGenerationAgent
from presearcher.presearcher import PresearcherAgent
from presearcher.purpose_generation import PurposeGenerationAgent
from presearcher.report_generation import ReportGenerationAgent
from utils.dataclass import (
    LiteratureSearchAgentRequest,
    LiteratureSearchAgentResponse,
    PresearcherAgentRequest,
    PresearcherAgentResponse,
    ReportGenerationRequest,
    ReportGenerationResponse,
    RetrievedDocument,
    _normalize_question,
)
from utils.literature_search import LiteratureSearchAgent


class DummyLiteratureSearchAgent:
    """Deterministic literature search agent for testing."""

    async def aforward(self, literature_search_request: LiteratureSearchAgentRequest):
        doc = RetrievedDocument(
            url=f"http://example.com/{literature_search_request.topic}",
            excerpts=["Content"],
        )
        return LiteratureSearchAgentResponse(
            topic=literature_search_request.topic,
            guideline=literature_search_request.guideline,
            writeup=f"Writeup for {literature_search_request.topic}",
            cited_documents=[doc],
            rag_responses=[],
        )


class DummyReportGenerationAgent:
    """Deterministic report generation agent for testing."""

    async def aforward(self, request: ReportGenerationRequest) -> ReportGenerationResponse:
        return ReportGenerationResponse(
            report=f"Report for {request.topic}",
            cited_documents=list(request.literature_search.cited_documents),
        )


class TestPresearcherAgent:
    """Tests for the recursive PresearcherAgent pipeline."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """PresearcherAgent initializes with the provided collaborators."""
        mock_purpose_agent = Mock(spec=PurposeGenerationAgent)
        mock_outline_agent = Mock(spec=OutlineGenerationAgent)
        mock_literature_agent = Mock(spec=LiteratureSearchAgent)
        mock_report_agent = Mock(spec=ReportGenerationAgent)
        mock_lm = Mock()

        agent = PresearcherAgent(
            purpose_generation_agent=mock_purpose_agent,
            outline_generation_agent=mock_outline_agent,
            literature_search_agent=mock_literature_agent,
            report_generation_agent=mock_report_agent,
            lm=mock_lm,
        )

        assert agent.purpose_generation_agent is mock_purpose_agent
        assert agent.outline_generation_agent is mock_outline_agent
        assert agent.literature_search_agent is mock_literature_agent

    @pytest.mark.asyncio
    async def test_recursive_graph_with_reuse_and_reports(self):
        """The agent builds a DAG with reused nodes and reports on each node."""
        # Use deterministic dummy agents for I/O-heavy components
        dummy_literature_agent = DummyLiteratureSearchAgent()
        dummy_report_agent = DummyReportGenerationAgent()

        mock_purpose_agent = Mock(spec=PurposeGenerationAgent)
        mock_outline_agent = Mock(spec=OutlineGenerationAgent)
        mock_lm = Mock()

        agent = PresearcherAgent(
            purpose_generation_agent=mock_purpose_agent,
            outline_generation_agent=mock_outline_agent,
            literature_search_agent=dummy_literature_agent,
            report_generation_agent=dummy_report_agent,
            lm=mock_lm,
        )

        # is_answerable: only the shared leaf node is answerable
        answerable_map = {
            "Root question": False,
            "Child A": False,
            "Child B": False,
            "Shared leaf": True,
        }

        async def fake_is_answerable_aforward(research_need: str, writeup: str, lm):
            return SimpleNamespace(is_answerable=answerable_map.get(research_need, False))

        agent.is_answerable = SimpleNamespace(aforward=fake_is_answerable_aforward)

        # subtask generation: root -> [Child A, Child B], both -> [Shared leaf]
        async def fake_subtask_aforward(research_task: str, max_subtasks: int, lm):
            if research_task == "Root question":
                return SimpleNamespace(
                    subtasks=["Child A", "Child B"],
                    composition_explanation="Decompose into A and B.",
                )
            if research_task in {"Child A", "Child B"}:
                return SimpleNamespace(
                    subtasks=["Shared leaf"],
                    composition_explanation="Both depend on same leaf.",
                )
            return SimpleNamespace(subtasks=[], composition_explanation="No subtasks.")

        agent.subtask_generation_agent = SimpleNamespace(aforward=fake_subtask_aforward)

        request = PresearcherAgentRequest(
            topic="Root question",
            max_depth=3,
            max_nodes=10,
        )

        result = await agent.aforward(request)

        assert isinstance(result, PresearcherAgentResponse)
        assert result.writeup.startswith("Report for Root question")
        assert result.graph is not None
        assert result.root_node_id is not None

        graph = result.graph
        assert graph is not None

        # DAG should contain exactly one node per normalized question
        normalized_questions = [
            _normalize_question(node.question) for node in graph.nodes.values()
        ]
        assert len(set(normalized_questions)) == len(graph.nodes)

        # We expect four logical nodes: root, two children, and one shared leaf
        assert len(graph.nodes) == 4

        # Find the shared leaf and ensure it has two parents (reused across branches)
        shared_nodes = [
            node for node in graph.nodes.values() if node.question == "Shared leaf"
        ]
        assert len(shared_nodes) == 1
        shared_node = shared_nodes[0]
        assert len(shared_node.parents) == 2

        # Every node should have a non-empty report
        for node in graph.nodes.values():
            assert node.report is not None
            assert node.report != ""

    @pytest.mark.asyncio
    async def test_respects_max_depth_and_max_nodes(self):
        """Recursion respects depth and node budget limits."""
        dummy_literature_agent = DummyLiteratureSearchAgent()
        dummy_report_agent = DummyReportGenerationAgent()

        mock_purpose_agent = Mock(spec=PurposeGenerationAgent)
        mock_outline_agent = Mock(spec=OutlineGenerationAgent)
        mock_lm = Mock()

        agent = PresearcherAgent(
            purpose_generation_agent=mock_purpose_agent,
            outline_generation_agent=mock_outline_agent,
            literature_search_agent=dummy_literature_agent,
            report_generation_agent=dummy_report_agent,
            lm=mock_lm,
        )

        # Never answerable so the agent would recurse if allowed
        async def fake_is_answerable_aforward(research_need: str, writeup: str, lm):
            return SimpleNamespace(is_answerable=False)

        agent.is_answerable = SimpleNamespace(aforward=fake_is_answerable_aforward)

        # Every node produces a single child "Next"
        async def fake_subtask_aforward(research_task: str, max_subtasks: int, lm):
            return SimpleNamespace(
                subtasks=[f"{research_task} -> Next"],
                composition_explanation="Chain to next node.",
            )

        agent.subtask_generation_agent = SimpleNamespace(aforward=fake_subtask_aforward)

        # Depth limit 0: no decomposition, only root node
        request_depth_0 = PresearcherAgentRequest(
            topic="Depth-limited root",
            max_depth=0,
            max_nodes=10,
        )
        result_depth_0 = await agent.aforward(request_depth_0)
        assert result_depth_0.graph is not None
        assert len(result_depth_0.graph.nodes) == 1

        # Depth limit 2, but node budget of 2 should cap expansion early
        request_budget = PresearcherAgentRequest(
            topic="Budget-limited root",
            max_depth=5,
            max_nodes=2,
        )
        result_budget = await agent.aforward(request_budget)
        assert result_budget.graph is not None
        assert len(result_budget.graph.nodes) == 2


class TestPresearcherAgentRequestAndResponse:
    """Tests for the PresearcherAgentRequest/Response dataclasses."""

    def test_request_initialization_with_defaults(self):
        """Request initializes with sensible defaults."""
        request = PresearcherAgentRequest(topic="Test topic")

        assert request.topic == "Test topic"
        assert request.max_retriever_calls == 15
        assert request.guideline is not None
        assert request.max_depth == 2
        assert request.max_nodes == 50
        assert request.collect_graph is True

    def test_response_to_dict_includes_graph_optional_fields(self):
        """Response serialization includes optional DAG fields."""
        doc = RetrievedDocument(url="http://example.com", excerpts=["Content"])

        response = PresearcherAgentResponse(
            topic="Test topic",
            guideline="Test guideline",
            writeup="Test writeup",
            cited_documents=[doc],
            rag_responses=[],
            misc={"key": "value"},
            root_node_id="node_1",
            graph=None,
        )

        result = response.to_dict()

        assert isinstance(result, dict)
        assert result["topic"] == "Test topic"
        assert result["guideline"] == "Test guideline"
        assert result["writeup"] == "Test writeup"
        assert len(result["cited_documents"]) == 1
        assert result["misc"]["key"] == "value"
        assert result["root_node_id"] == "node_1"
