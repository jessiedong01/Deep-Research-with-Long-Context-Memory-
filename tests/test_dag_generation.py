"""Tests for DAG Generation Module.

Tests the upfront DAG generation including:
- Output format determination
- Decomposition decisions
- Deterministic limit enforcement (max_depth, max_nodes)
- Quick literature searches
"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# Add src to path for imports
src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Make pytest optional for manual testing
try:
    import pytest
except ImportError:
    pytest = None
    # Create a dummy decorator for asyncio mark
    class DummyMark:
        def asyncio(self, func):
            return func
    
    class DummyPytest:
        mark = DummyMark()
    
    pytest = DummyPytest()

from presearcher.dag_generation import (
    DAGGenerationAgent,
    ExpectedOutputFormatSignature,
    DAGDecompositionSignature,
)
from utils.dataclass import (
    PresearcherAgentRequest,
    LiteratureSearchAgentResponse,
    ResearchGraph,
)


class TestExpectedOutputFormatSignature:
    """Tests for the ExpectedOutputFormatSignature."""
    
    def test_signature_has_required_fields(self):
        """Test that the signature has all required input and output fields."""
        sig = ExpectedOutputFormatSignature
        
        # Check input fields exist
        assert hasattr(sig, 'research_task')
        assert hasattr(sig, 'context_summary')
        
        # Check output fields exist
        assert hasattr(sig, 'format_type')
        assert hasattr(sig, 'format_details')


class TestDAGDecompositionSignature:
    """Tests for the DAGDecompositionSignature."""
    
    def test_signature_has_required_fields(self):
        """Test that the signature has all required input and output fields."""
        sig = DAGDecompositionSignature
        
        # Check input fields
        assert hasattr(sig, 'research_task')
        assert hasattr(sig, 'quick_search_summary')
        assert hasattr(sig, 'current_depth')
        assert hasattr(sig, 'max_depth')
        assert hasattr(sig, 'remaining_nodes')
        assert hasattr(sig, 'max_subtasks')
        
        # Check output fields
        assert hasattr(sig, 'should_decompose')
        assert hasattr(sig, 'subtasks')
        assert hasattr(sig, 'composition_instructions')


class TestDAGGenerationAgent:
    """Tests for the DAGGenerationAgent."""
    
    def _create_mock_literature_search_agent(self):
        """Create a mock literature search agent."""
        mock_agent = Mock()
        
        async def mock_aforward(request):
            return LiteratureSearchAgentResponse(
                topic=request.topic,
                guideline=request.guideline,
                writeup=f"Quick search results for: {request.topic}",
                cited_documents=[],
                rag_responses=[],
            )
        
        mock_agent.aforward = AsyncMock(side_effect=mock_aforward)
        return mock_agent
    
    def _create_mock_lm(self):
        """Create a mock language model."""
        return Mock()
    
    def test_agent_initialization(self):
        """Test that agent initializes correctly."""
        lit_agent = self._create_mock_literature_search_agent()
        lm = self._create_mock_lm()
        
        agent = DAGGenerationAgent(
            literature_search_agent=lit_agent,
            lm=lm,
        )
        
        assert agent.literature_search_agent is lit_agent
        assert agent.lm is lm
        assert hasattr(agent, 'format_predictor')
        assert hasattr(agent, 'decomposition_predictor')
    
    @pytest.mark.asyncio
    async def test_generate_dag_creates_root_node(self):
        """Test that DAG generation creates a root node."""
        lit_agent = self._create_mock_literature_search_agent()
        lm = self._create_mock_lm()
        agent = DAGGenerationAgent(literature_search_agent=lit_agent, lm=lm)
        
        # Mock the predictors to not decompose
        async def mock_format_predict(*args, **kwargs):
            result = Mock()
            result.format_type = "report"
            result.format_details = "A detailed report"
            return result
        
        async def mock_decomp_predict(*args, **kwargs):
            result = Mock()
            result.should_decompose = False
            result.subtasks = []
            result.composition_instructions = ""
            return result
        
        agent.format_predictor.aforward = AsyncMock(side_effect=mock_format_predict)
        agent.decomposition_predictor.aforward = AsyncMock(side_effect=mock_decomp_predict)
        
        request = PresearcherAgentRequest(
            topic="Test research question",
            max_depth=1,
            max_nodes=10,
            max_subtasks=5,
        )
        
        graph = await agent.generate_dag(request)
        
        assert graph.root_id is not None
        assert len(graph.nodes) == 1
        root = graph.nodes[graph.root_id]
        assert root.question == "Test research question"
        assert root.depth == 0
        assert root.expected_output_format == "report"
    
    @pytest.mark.asyncio
    async def test_max_depth_limit_enforced(self):
        """Test that max_depth limit is strictly enforced."""
        lit_agent = self._create_mock_literature_search_agent()
        lm = self._create_mock_lm()
        agent = DAGGenerationAgent(literature_search_agent=lit_agent, lm=lm)
        
        # Mock predictors to always decompose with one subtask
        async def mock_format_predict(*args, **kwargs):
            result = Mock()
            result.format_type = "report"
            result.format_details = "A detailed report"
            return result
        
        decompose_count = [0]
        
        async def mock_decomp_predict(*args, **kwargs):
            decompose_count[0] += 1
            current_depth = kwargs.get('current_depth', 0)
            max_depth = kwargs.get('max_depth', 2)
            
            result = Mock()
            # Only decompose if we have room
            should_decompose = current_depth < max_depth - 1
            result.should_decompose = should_decompose
            result.subtasks = [f"Subtask at depth {current_depth + 1}"] if should_decompose else []
            result.composition_instructions = "Combine results" if should_decompose else ""
            return result
        
        agent.format_predictor.aforward = AsyncMock(side_effect=mock_format_predict)
        agent.decomposition_predictor.aforward = AsyncMock(side_effect=mock_decomp_predict)
        
        request = PresearcherAgentRequest(
            topic="Root question",
            max_depth=2,  # Only allow depth 0 and 1
            max_nodes=100,  # High enough to not be a constraint
            max_subtasks=1,
        )
        
        graph = await agent.generate_dag(request)
        
        # Should have root at depth 0 and one child at depth 1
        # Child at depth 1 should NOT decompose (since that would create depth 2)
        max_depth_in_graph = max(node.depth for node in graph.nodes.values())
        assert max_depth_in_graph < request.max_depth, f"Max depth {max_depth_in_graph} should be < {request.max_depth}"
        
        # Verify no node at depth >= max_depth
        for node in graph.nodes.values():
            assert node.depth < request.max_depth
    
    @pytest.mark.asyncio
    async def test_max_nodes_limit_enforced(self):
        """Test that max_nodes limit is strictly enforced."""
        lit_agent = self._create_mock_literature_search_agent()
        lm = self._create_mock_lm()
        agent = DAGGenerationAgent(literature_search_agent=lit_agent, lm=lm)
        
        # Mock predictors to always decompose with multiple subtasks
        async def mock_format_predict(*args, **kwargs):
            result = Mock()
            result.format_type = "report"
            result.format_details = "A detailed report"
            return result
        
        async def mock_decomp_predict(*args, **kwargs):
            result = Mock()
            result.should_decompose = True
            # Try to create 3 subtasks each time
            result.subtasks = ["Subtask 1", "Subtask 2", "Subtask 3"]
            result.composition_instructions = "Combine all results"
            return result
        
        agent.format_predictor.aforward = AsyncMock(side_effect=mock_format_predict)
        agent.decomposition_predictor.aforward = AsyncMock(side_effect=mock_decomp_predict)
        
        request = PresearcherAgentRequest(
            topic="Root question",
            max_depth=10,  # High enough to not be a constraint
            max_nodes=5,   # Strict limit
            max_subtasks=10,
        )
        
        graph = await agent.generate_dag(request)
        
        # Should not exceed max_nodes
        assert len(graph.nodes) <= request.max_nodes
    
    @pytest.mark.asyncio
    async def test_all_nodes_have_expected_output_format(self):
        """Test that all nodes get an expected_output_format assigned."""
        lit_agent = self._create_mock_literature_search_agent()
        lm = self._create_mock_lm()
        agent = DAGGenerationAgent(literature_search_agent=lit_agent, lm=lm)
        
        format_types = ["boolean", "short_answer", "list", "table_csv", "report"]
        format_index = [0]
        
        async def mock_format_predict(*args, **kwargs):
            result = Mock()
            result.format_type = format_types[format_index[0] % len(format_types)]
            result.format_details = f"Details for {result.format_type}"
            format_index[0] += 1
            return result
        
        async def mock_decomp_predict(*args, **kwargs):
            current_depth = kwargs.get('current_depth', 0)
            result = Mock()
            # Decompose only at depth 0
            result.should_decompose = (current_depth == 0)
            result.subtasks = ["Subtask 1", "Subtask 2"] if current_depth == 0 else []
            result.composition_instructions = "Combine" if current_depth == 0 else ""
            return result
        
        agent.format_predictor.aforward = AsyncMock(side_effect=mock_format_predict)
        agent.decomposition_predictor.aforward = AsyncMock(side_effect=mock_decomp_predict)
        
        request = PresearcherAgentRequest(
            topic="Root question",
            max_depth=3,
            max_nodes=10,
            max_subtasks=5,
        )
        
        graph = await agent.generate_dag(request)
        
        # Every node should have an expected_output_format
        for node in graph.nodes.values():
            assert node.expected_output_format is not None
            assert node.expected_output_format in format_types
    
    @pytest.mark.asyncio
    async def test_parent_nodes_have_composition_instructions(self):
        """Test that parent nodes have composition_instructions."""
        lit_agent = self._create_mock_literature_search_agent()
        lm = self._create_mock_lm()
        agent = DAGGenerationAgent(literature_search_agent=lit_agent, lm=lm)
        
        async def mock_format_predict(*args, **kwargs):
            result = Mock()
            result.format_type = "report"
            result.format_details = "A report"
            return result
        
        async def mock_decomp_predict(*args, **kwargs):
            current_depth = kwargs.get('current_depth', 0)
            result = Mock()
            result.should_decompose = (current_depth == 0)
            result.subtasks = ["Subtask 1", "Subtask 2"] if current_depth == 0 else []
            result.composition_instructions = "Combine subtask results" if current_depth == 0 else ""
            return result
        
        agent.format_predictor.aforward = AsyncMock(side_effect=mock_format_predict)
        agent.decomposition_predictor.aforward = AsyncMock(side_effect=mock_decomp_predict)
        
        request = PresearcherAgentRequest(
            topic="Root question",
            max_depth=2,
            max_nodes=10,
            max_subtasks=5,
        )
        
        graph = await agent.generate_dag(request)
        
        # Root node should have children and composition instructions
        root = graph.nodes[graph.root_id]
        if root.children:
            assert root.composition_instructions is not None
            assert len(root.composition_instructions) > 0
        
        # Leaf nodes should not have composition instructions
        for node in graph.nodes.values():
            if not node.children:
                # Leaf nodes might have empty or None composition_instructions
                assert node.composition_instructions is None or node.composition_instructions == ""
    
    @pytest.mark.asyncio
    async def test_quick_literature_searches_performed(self):
        """Test that quick literature searches are performed for each node."""
        lit_agent = self._create_mock_literature_search_agent()
        lm = self._create_mock_lm()
        agent = DAGGenerationAgent(literature_search_agent=lit_agent, lm=lm)
        
        async def mock_format_predict(*args, **kwargs):
            result = Mock()
            result.format_type = "report"
            result.format_details = "A report"
            return result
        
        async def mock_decomp_predict(*args, **kwargs):
            result = Mock()
            result.should_decompose = False
            result.subtasks = []
            result.composition_instructions = ""
            return result
        
        agent.format_predictor.aforward = AsyncMock(side_effect=mock_format_predict)
        agent.decomposition_predictor.aforward = AsyncMock(side_effect=mock_decomp_predict)
        
        request = PresearcherAgentRequest(
            topic="Test question",
            max_depth=1,
            max_nodes=5,
            max_subtasks=3,
        )
        
        graph = await agent.generate_dag(request)
        
        # Literature search agent should have been called for each node
        assert lit_agent.aforward.call_count == len(graph.nodes)
        
        # Each call should have max_retriever_calls=1 (quick search)
        for call in lit_agent.aforward.call_args_list:
            request_arg = call[0][0]
            assert request_arg.max_retriever_calls == 1


# Simple synchronous test runner for manual testing
def run_tests_manually():
    """Run async tests manually without pytest."""
    import sys
    import traceback
    
    test_class = TestDAGGenerationAgent()
    
    tests = [
        ("test_agent_initialization", test_class.test_agent_initialization),
        ("test_generate_dag_creates_root_node", test_class.test_generate_dag_creates_root_node),
        ("test_max_depth_limit_enforced", test_class.test_max_depth_limit_enforced),
        ("test_max_nodes_limit_enforced", test_class.test_max_nodes_limit_enforced),
        ("test_all_nodes_have_expected_output_format", test_class.test_all_nodes_have_expected_output_format),
        ("test_parent_nodes_have_composition_instructions", test_class.test_parent_nodes_have_composition_instructions),
        ("test_quick_literature_searches_performed", test_class.test_quick_literature_searches_performed),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"Running {test_name}...", end=" ")
            if asyncio.iscoroutinefunction(test_func):
                asyncio.run(test_func())
            else:
                test_func()
            print("✓ PASSED")
            passed += 1
        except Exception as e:
            print(f"✗ FAILED")
            print(f"  Error: {e}")
            traceback.print_exc()
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")
    
    return failed == 0


if __name__ == "__main__":
    import sys
    success = run_tests_manually()
    sys.exit(0 if success else 1)

