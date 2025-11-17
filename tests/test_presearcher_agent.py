"""Test suite for Presearcher Agent.

Tests the main pipeline that orchestrates purpose generation, outline generation,
literature search, report generation, and report combination.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
import dspy

from presearcher.presearcher import PresearcherAgent
from presearcher.purpose_generation import PurposeGenerationAgent
from outline_generation import OutlineGenerationAgent
from presearcher.report_generation import ReportGenerationAgent
from utils.literature_search import LiteratureSearchAgent
from utils.dataclass import (
    PresearcherAgentRequest,
    PresearcherAgentResponse,
    LiteratureSearchAgentResponse,
    ReportGenerationResponse,
    RagResponse,
    RetrievedDocument
)


class TestPresearcherAgent:
    """Tests for the main PresearcherAgent pipeline."""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test that the Presearcher agent initializes correctly."""
        mock_purpose_agent = Mock(spec=PurposeGenerationAgent)
        mock_outline_agent = Mock(spec=OutlineGenerationAgent)
        mock_literature_agent = Mock(spec=LiteratureSearchAgent)
        mock_report_agent = Mock(spec=ReportGenerationAgent)
        mock_lm = Mock(spec=dspy.LM)
        
        agent = PresearcherAgent(
            purpose_generation_agent=mock_purpose_agent,
            outline_generation_agent=mock_outline_agent,
            literature_search_agent=mock_literature_agent,
            report_generation_agent=mock_report_agent,
            lm=mock_lm
        )
        
        assert agent.purpose_generation_agent is mock_purpose_agent
        assert agent.outline_generation_agent is mock_outline_agent
        assert agent.literature_search_agent is mock_literature_agent
    
    @pytest.mark.asyncio
    @patch('dspy.Predict')
    async def test_aforward_complete_pipeline(self, mock_predict_class):
        """Test the complete presearcher pipeline from start to finish."""
        # Setup all mock agents
        mock_purpose_agent = Mock(spec=PurposeGenerationAgent)
        mock_outline_agent = Mock(spec=OutlineGenerationAgent)
        mock_literature_agent = Mock(spec=LiteratureSearchAgent)
        mock_report_agent = Mock(spec=ReportGenerationAgent)
        mock_lm = Mock(spec=dspy.LM)
        mock_lm.kwargs = {"temperature": 1.0}
        
        # Mock dspy.Predict to return a mock predictor with the expected response
        mock_predictor = Mock()
        mock_combiner_response = Mock()
        mock_combiner_response.final_report = "Combined final report"
        mock_predictor.aforward = AsyncMock(return_value=mock_combiner_response)
        mock_predict_class.return_value = mock_predictor
        
        agent = PresearcherAgent(
            purpose_generation_agent=mock_purpose_agent,
            outline_generation_agent=mock_outline_agent,
            literature_search_agent=mock_literature_agent,
            report_generation_agent=mock_report_agent,
            lm=mock_lm
        )
        
        # Mock purpose generation response
        mock_purpose_agent.aforward = AsyncMock(return_value=[
            "Research need 1: AI diagnostic accuracy",
            "Research need 2: AI adoption barriers"
        ])
        
        # Mock outline generation response
        mock_outline_agent.aforward = AsyncMock(return_value={
            "markdown": "# Outline\n## Section 1\n## Section 2",
            "parsed_outline": {}
        })
        
        # Mock literature search response
        doc = RetrievedDocument(url="http://example.com", excerpts=["Content"])
        literature_response = LiteratureSearchAgentResponse(
            topic="AI diagnostic accuracy",
            guideline="Survey",
            writeup="Literature writeup",
            cited_documents=[doc],
            rag_responses=[
                RagResponse(
                    question="Question",
                    answer="Answer[1]",
                    cited_documents=[doc]
                )
            ]
        )
        mock_literature_agent.aforward = AsyncMock(return_value=literature_response)
        
        # Mock report generation response
        report_response = ReportGenerationResponse(
            report="Generated report",
            cited_documents=[doc]
        )
        mock_report_agent.aforward = AsyncMock(return_value=report_response)
        
        # Create request
        request = PresearcherAgentRequest(
            topic="AI in healthcare",
            max_retriever_calls=10
        )
        
        # Execute pipeline
        result = await agent.aforward(request)
        
        # Verify result
        assert isinstance(result, PresearcherAgentResponse)
        assert result.topic == "AI in healthcare"
        assert result.writeup == "Combined final report"
        
        # Verify all agents were called
        mock_purpose_agent.aforward.assert_called_once()
        mock_outline_agent.aforward.assert_called_once()
        assert mock_literature_agent.aforward.call_count >= 1
        assert mock_report_agent.aforward.call_count >= 1
    
    @pytest.mark.asyncio
    @patch('dspy.Predict')
    async def test_pipeline_calls_purpose_generation_first(self, mock_predict_class):
        """Test that purpose generation is the first step."""
        mock_purpose_agent = Mock(spec=PurposeGenerationAgent)
        mock_outline_agent = Mock(spec=OutlineGenerationAgent)
        mock_literature_agent = Mock(spec=LiteratureSearchAgent)
        mock_report_agent = Mock(spec=ReportGenerationAgent)
        mock_lm = Mock(spec=dspy.LM)
        mock_lm.kwargs = {"temperature": 1.0}
        
        # Mock dspy.Predict for ReportCombiner
        mock_predictor = Mock()
        mock_combiner_response = Mock()
        mock_combiner_response.final_report = "Final report"
        mock_predictor.aforward = AsyncMock(return_value=mock_combiner_response)
        mock_predict_class.return_value = mock_predictor
        
        agent = PresearcherAgent(
            purpose_generation_agent=mock_purpose_agent,
            outline_generation_agent=mock_outline_agent,
            literature_search_agent=mock_literature_agent,
            report_generation_agent=mock_report_agent,
            lm=mock_lm
        )
        
        # Setup mocks
        purposes = ["Research need 1", "Research need 2"]
        mock_purpose_agent.aforward = AsyncMock(return_value=purposes)
        
        mock_outline_agent.aforward = AsyncMock(return_value={
            "markdown": "# Outline",
            "parsed_outline": {}
        })
        
        doc = RetrievedDocument(url="http://example.com", excerpts=["Content"])
        literature_response = LiteratureSearchAgentResponse(
            topic="Test",
            guideline="Survey",
            writeup="Writeup",
            cited_documents=[doc],
            rag_responses=[]
        )
        mock_literature_agent.aforward = AsyncMock(return_value=literature_response)
        
        report_response = ReportGenerationResponse(
            report="Report",
            cited_documents=[doc]
        )
        mock_report_agent.aforward = AsyncMock(return_value=report_response)
        
        request = PresearcherAgentRequest(
            topic="Test topic",
            max_retriever_calls=5
        )
        
        result = await agent.aforward(request)
        
        # Verify purpose generation was called with the topic
        mock_purpose_agent.aforward.assert_called_once_with("Test topic")
    
    @pytest.mark.asyncio
    @patch('dspy.Predict')
    async def test_pipeline_calls_outline_generation_second(self, mock_predict_class):
        """Test that outline generation is called after purpose generation."""
        mock_purpose_agent = Mock(spec=PurposeGenerationAgent)
        mock_outline_agent = Mock(spec=OutlineGenerationAgent)
        mock_literature_agent = Mock(spec=LiteratureSearchAgent)
        mock_report_agent = Mock(spec=ReportGenerationAgent)
        mock_lm = Mock(spec=dspy.LM)
        mock_lm.kwargs = {"temperature": 1.0}
        
        # Mock dspy.Predict for ReportCombiner
        mock_predictor = Mock()
        mock_combiner_response = Mock()
        mock_combiner_response.final_report = "Final report"
        mock_predictor.aforward = AsyncMock(return_value=mock_combiner_response)
        mock_predict_class.return_value = mock_predictor
        
        agent = PresearcherAgent(
            purpose_generation_agent=mock_purpose_agent,
            outline_generation_agent=mock_outline_agent,
            literature_search_agent=mock_literature_agent,
            report_generation_agent=mock_report_agent,
            lm=mock_lm
        )
        
        purposes = ["Research need 1", "Research need 2"]
        mock_purpose_agent.aforward = AsyncMock(return_value=purposes)
        
        mock_outline_agent.aforward = AsyncMock(return_value={
            "markdown": "# Outline",
            "parsed_outline": {}
        })
        
        doc = RetrievedDocument(url="http://example.com", excerpts=["Content"])
        literature_response = LiteratureSearchAgentResponse(
            topic="Test",
            guideline="Survey",
            writeup="Writeup",
            cited_documents=[doc],
            rag_responses=[]
        )
        mock_literature_agent.aforward = AsyncMock(return_value=literature_response)
        
        report_response = ReportGenerationResponse(
            report="Report",
            cited_documents=[doc]
        )
        mock_report_agent.aforward = AsyncMock(return_value=report_response)
        
        request = PresearcherAgentRequest(
            topic="Test topic",
            max_retriever_calls=5
        )
        
        await agent.aforward(request)
        
        # Verify outline generation was called with topic and purposes
        mock_outline_agent.aforward.assert_called_once_with("Test topic", purposes)
    
    @pytest.mark.asyncio
    @patch('dspy.Predict')
    async def test_pipeline_performs_literature_search_for_each_need(self, mock_predict_class):
        """Test that literature search is performed for each research need."""
        mock_purpose_agent = Mock(spec=PurposeGenerationAgent)
        mock_outline_agent = Mock(spec=OutlineGenerationAgent)
        mock_literature_agent = Mock(spec=LiteratureSearchAgent)
        mock_report_agent = Mock(spec=ReportGenerationAgent)
        mock_lm = Mock(spec=dspy.LM)
        mock_lm.kwargs = {"temperature": 1.0}
        
        # Mock dspy.Predict for ReportCombiner
        mock_predictor = Mock()
        mock_combiner_response = Mock()
        mock_combiner_response.final_report = "Final report"
        mock_predictor.aforward = AsyncMock(return_value=mock_combiner_response)
        mock_predict_class.return_value = mock_predictor
        
        agent = PresearcherAgent(
            purpose_generation_agent=mock_purpose_agent,
            outline_generation_agent=mock_outline_agent,
            literature_search_agent=mock_literature_agent,
            report_generation_agent=mock_report_agent,
            lm=mock_lm
        )
        
        # Three research needs
        purposes = [
            "Research need 1",
            "Research need 2",
            "Research need 3"
        ]
        mock_purpose_agent.aforward = AsyncMock(return_value=purposes)
        
        mock_outline_agent.aforward = AsyncMock(return_value={
            "markdown": "# Outline",
            "parsed_outline": {}
        })
        
        doc = RetrievedDocument(url="http://example.com", excerpts=["Content"])
        literature_response = LiteratureSearchAgentResponse(
            topic="Test",
            guideline="Survey",
            writeup="Writeup",
            cited_documents=[doc],
            rag_responses=[]
        )
        mock_literature_agent.aforward = AsyncMock(return_value=literature_response)
        
        report_response = ReportGenerationResponse(
            report="Report",
            cited_documents=[doc]
        )
        mock_report_agent.aforward = AsyncMock(return_value=report_response)
        request = PresearcherAgentRequest(
            topic="Test topic",
            max_retriever_calls=15
        )
        
        await agent.aforward(request)
        
        # Should call literature search 3 times (once per research need)
        assert mock_literature_agent.aforward.call_count == 3
    
    @pytest.mark.asyncio
    @patch('dspy.Predict')
    async def test_pipeline_generates_report_for_each_need(self, mock_predict_class):
        """Test that report generation is performed for each research need."""
        mock_purpose_agent = Mock(spec=PurposeGenerationAgent)
        mock_outline_agent = Mock(spec=OutlineGenerationAgent)
        mock_literature_agent = Mock(spec=LiteratureSearchAgent)
        mock_report_agent = Mock(spec=ReportGenerationAgent)
        mock_lm = Mock(spec=dspy.LM)
        mock_lm.kwargs = {"temperature": 1.0}
        
        # Mock dspy.Predict for ReportCombiner
        mock_predictor = Mock()
        mock_combiner_response = Mock()
        mock_combiner_response.final_report = "Final report"
        mock_predictor.aforward = AsyncMock(return_value=mock_combiner_response)
        mock_predict_class.return_value = mock_predictor
        
        agent = PresearcherAgent(
            purpose_generation_agent=mock_purpose_agent,
            outline_generation_agent=mock_outline_agent,
            literature_search_agent=mock_literature_agent,
            report_generation_agent=mock_report_agent,
            lm=mock_lm
        )
        
        purposes = ["Research need 1", "Research need 2"]
        mock_purpose_agent.aforward = AsyncMock(return_value=purposes)
        
        mock_outline_agent.aforward = AsyncMock(return_value={
            "markdown": "# Outline",
            "parsed_outline": {}
        })
        
        doc = RetrievedDocument(url="http://example.com", excerpts=["Content"])
        literature_response = LiteratureSearchAgentResponse(
            topic="Test",
            guideline="Survey",
            writeup="Writeup",
            cited_documents=[doc],
            rag_responses=[]
        )
        mock_literature_agent.aforward = AsyncMock(return_value=literature_response)
        
        report_response = ReportGenerationResponse(
            report="Report",
            cited_documents=[doc]
        )
        mock_report_agent.aforward = AsyncMock(return_value=report_response)
        request = PresearcherAgentRequest(
            topic="Test topic",
            max_retriever_calls=10
        )
        
        await agent.aforward(request)
        
        # Should call report generation 2 times
        assert mock_report_agent.aforward.call_count == 2
    
    @pytest.mark.asyncio
    @patch('dspy.Predict')
    async def test_pipeline_combines_reports_at_end(self, mock_predict_class):
        """Test that reports are combined at the end of the pipeline."""
        mock_purpose_agent = Mock(spec=PurposeGenerationAgent)
        mock_outline_agent = Mock(spec=OutlineGenerationAgent)
        mock_literature_agent = Mock(spec=LiteratureSearchAgent)
        mock_report_agent = Mock(spec=ReportGenerationAgent)
        mock_lm = Mock(spec=dspy.LM)
        mock_lm.kwargs = {"temperature": 1.0}
        
        # Mock dspy.Predict for ReportCombiner
        mock_predictor = Mock()
        mock_combiner_response = Mock()
        mock_combiner_response.final_report = "Combined final report"
        mock_predictor.aforward = AsyncMock(return_value=mock_combiner_response)
        mock_predict_class.return_value = mock_predictor
        
        agent = PresearcherAgent(
            purpose_generation_agent=mock_purpose_agent,
            outline_generation_agent=mock_outline_agent,
            literature_search_agent=mock_literature_agent,
            report_generation_agent=mock_report_agent,
            lm=mock_lm
        )
        
        purposes = ["Research need 1"]
        mock_purpose_agent.aforward = AsyncMock(return_value=purposes)
        
        mock_outline_agent.aforward = AsyncMock(return_value={
            "markdown": "# Outline",
            "parsed_outline": {}
        })
        
        doc = RetrievedDocument(url="http://example.com", excerpts=["Content"])
        literature_response = LiteratureSearchAgentResponse(
            topic="Test",
            guideline="Survey",
            writeup="Writeup",
            cited_documents=[doc],
            rag_responses=[]
        )
        mock_literature_agent.aforward = AsyncMock(return_value=literature_response)
        
        report_response = ReportGenerationResponse(
            report="Individual report",
            cited_documents=[doc]
        )
        mock_report_agent.aforward = AsyncMock(return_value=report_response)
        request = PresearcherAgentRequest(
            topic="Test topic",
            max_retriever_calls=5
        )
        
        result = await agent.aforward(request)
        
        # Verify the final report is from the combiner
        assert result.writeup == "Combined final report"
        # Verify that dspy.Predict was called to create the report combiner
        mock_predict_class.assert_called()


class TestPresearcherAgentRequest:
    """Tests for the PresearcherAgentRequest dataclass."""
    
    def test_request_initialization_with_defaults(self):
        """Test that request can be initialized with default values."""
        request = PresearcherAgentRequest(
            topic="Test topic"
        )
        
        assert request.topic == "Test topic"
        assert request.max_retriever_calls == 15  # Default value
        assert request.guideline is not None
    
    def test_request_initialization_with_custom_values(self):
        """Test that request can be initialized with custom values."""
        request = PresearcherAgentRequest(
            topic="Custom topic",
            max_retriever_calls=25,
            guideline="Custom guideline"
        )
        
        assert request.topic == "Custom topic"
        assert request.max_retriever_calls == 25
        assert request.guideline == "Custom guideline"


class TestPresearcherAgentResponse:
    """Tests for the PresearcherAgentResponse dataclass."""
    
    def test_response_to_dict(self):
        """Test that response can be serialized to dictionary."""
        doc = RetrievedDocument(url="http://example.com", excerpts=["Content"])
        
        response = PresearcherAgentResponse(
            topic="Test topic",
            guideline="Test guideline",
            writeup="Test writeup",
            cited_documents=[doc],
            rag_responses=[],
            misc={}
        )
        
        result = response.to_dict()
        
        assert isinstance(result, dict)
        assert result["topic"] == "Test topic"
        assert result["guideline"] == "Test guideline"
        assert result["writeup"] == "Test writeup"
        assert len(result["cited_documents"]) == 1


class TestPresearcherAgentEdgeCases:
    """Tests for edge cases and error handling."""
    
    @pytest.mark.asyncio
    @patch('dspy.Predict')
    async def test_empty_purposes_list(self, mock_predict_class):
        """Test pipeline behavior when no research needs are generated."""
        mock_purpose_agent = Mock(spec=PurposeGenerationAgent)
        mock_outline_agent = Mock(spec=OutlineGenerationAgent)
        mock_literature_agent = Mock(spec=LiteratureSearchAgent)
        mock_report_agent = Mock(spec=ReportGenerationAgent)
        mock_lm = Mock(spec=dspy.LM)
        mock_lm.kwargs = {"temperature": 1.0}
        
        # Mock dspy.Predict for ReportCombiner
        mock_predictor = Mock()
        mock_combiner_response = Mock()
        mock_combiner_response.final_report = "Empty report"
        mock_predictor.aforward = AsyncMock(return_value=mock_combiner_response)
        mock_predict_class.return_value = mock_predictor
        
        agent = PresearcherAgent(
            purpose_generation_agent=mock_purpose_agent,
            outline_generation_agent=mock_outline_agent,
            literature_search_agent=mock_literature_agent,
            report_generation_agent=mock_report_agent,
            lm=mock_lm
        )
        
        # No research needs
        mock_purpose_agent.aforward = AsyncMock(return_value=[])
        
        mock_outline_agent.aforward = AsyncMock(return_value={
            "markdown": "# Outline",
            "parsed_outline": {}
        })
        request = PresearcherAgentRequest(
            topic="Test topic",
            max_retriever_calls=5
        )
        
        result = await agent.aforward(request)
        
        # Should not call literature search or report generation
        assert mock_literature_agent.aforward.call_count == 0
        assert mock_report_agent.aforward.call_count == 0
        
        # Should still return a response
        assert isinstance(result, PresearcherAgentResponse)
    
    @pytest.mark.asyncio
    @patch('dspy.Predict')
    async def test_single_research_need(self, mock_predict_class):
        """Test pipeline with only one research need."""
        mock_purpose_agent = Mock(spec=PurposeGenerationAgent)
        mock_outline_agent = Mock(spec=OutlineGenerationAgent)
        mock_literature_agent = Mock(spec=LiteratureSearchAgent)
        mock_report_agent = Mock(spec=ReportGenerationAgent)
        mock_lm = Mock(spec=dspy.LM)
        mock_lm.kwargs = {"temperature": 1.0}
        
        # Mock dspy.Predict for ReportCombiner
        mock_predictor = Mock()
        mock_combiner_response = Mock()
        mock_combiner_response.final_report = "Final single report"
        mock_predictor.aforward = AsyncMock(return_value=mock_combiner_response)
        mock_predict_class.return_value = mock_predictor
        
        agent = PresearcherAgent(
            purpose_generation_agent=mock_purpose_agent,
            outline_generation_agent=mock_outline_agent,
            literature_search_agent=mock_literature_agent,
            report_generation_agent=mock_report_agent,
            lm=mock_lm
        )
        
        purposes = ["Single research need"]
        mock_purpose_agent.aforward = AsyncMock(return_value=purposes)
        
        mock_outline_agent.aforward = AsyncMock(return_value={
            "markdown": "# Outline",
            "parsed_outline": {}
        })
        
        doc = RetrievedDocument(url="http://example.com", excerpts=["Content"])
        literature_response = LiteratureSearchAgentResponse(
            topic="Test",
            guideline="Survey",
            writeup="Writeup",
            cited_documents=[doc],
            rag_responses=[]
        )
        mock_literature_agent.aforward = AsyncMock(return_value=literature_response)
        
        report_response = ReportGenerationResponse(
            report="Single report",
            cited_documents=[doc]
        )
        mock_report_agent.aforward = AsyncMock(return_value=report_response)
        request = PresearcherAgentRequest(
            topic="Test topic",
            max_retriever_calls=5
        )
        
        result = await agent.aforward(request)
        
        # Should process the single need
        assert mock_literature_agent.aforward.call_count == 1
        assert mock_report_agent.aforward.call_count == 1
        assert isinstance(result, PresearcherAgentResponse)
    
    @pytest.mark.asyncio
    @patch('dspy.Predict')
    async def test_low_max_retriever_calls(self, mock_predict_class):
        """Test pipeline with very low retriever call budget."""
        mock_purpose_agent = Mock(spec=PurposeGenerationAgent)
        mock_outline_agent = Mock(spec=OutlineGenerationAgent)
        mock_literature_agent = Mock(spec=LiteratureSearchAgent)
        mock_report_agent = Mock(spec=ReportGenerationAgent)
        mock_lm = Mock(spec=dspy.LM)
        mock_lm.kwargs = {"temperature": 1.0}
        
        # Mock dspy.Predict for ReportCombiner
        mock_predictor = Mock()
        mock_combiner_response = Mock()
        mock_combiner_response.final_report = "Final report"
        mock_predictor.aforward = AsyncMock(return_value=mock_combiner_response)
        mock_predict_class.return_value = mock_predictor
        
        agent = PresearcherAgent(
            purpose_generation_agent=mock_purpose_agent,
            outline_generation_agent=mock_outline_agent,
            literature_search_agent=mock_literature_agent,
            report_generation_agent=mock_report_agent,
            lm=mock_lm
        )
        
        purposes = ["Research need 1"]
        mock_purpose_agent.aforward = AsyncMock(return_value=purposes)
        
        mock_outline_agent.aforward = AsyncMock(return_value={
            "markdown": "# Outline",
            "parsed_outline": {}
        })
        
        doc = RetrievedDocument(url="http://example.com", excerpts=["Content"])
        literature_response = LiteratureSearchAgentResponse(
            topic="Test",
            guideline="Survey",
            writeup="Writeup",
            cited_documents=[doc],
            rag_responses=[]
        )
        mock_literature_agent.aforward = AsyncMock(return_value=literature_response)
        
        report_response = ReportGenerationResponse(
            report="Report",
            cited_documents=[doc]
        )
        mock_report_agent.aforward = AsyncMock(return_value=report_response)
        request = PresearcherAgentRequest(
            topic="Test topic",
            max_retriever_calls=1  # Very low budget
        )
        
        result = await agent.aforward(request)
        
        # Should still complete
        assert isinstance(result, PresearcherAgentResponse)

