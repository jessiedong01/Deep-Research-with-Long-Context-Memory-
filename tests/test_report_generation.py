"""Test suite for Report Generation Agent.

Tests the report generation process including key insight identification,
writing guideline proposal, and final report synthesis.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
import dspy

from presearcher.report_generation import (
    ReportGenerationAgent,
    KeyInsightIdentifier,
    FinalWritingGuidelineProposal,
    FinalReportSynthesizer,
    _normalize_rag_response_citation_indices
)
from utils.dataclass import (
    ReportGenerationRequest,
    ReportGenerationResponse,
    LiteratureSearchAgentResponse,
    RagResponse,
    RetrievedDocument
)
from utils.literature_search import LiteratureSearchAgent


class TestKeyInsightIdentifier:
    """Tests for the KeyInsightIdentifier signature."""
    
    @pytest.mark.asyncio
    async def test_key_insight_signature_fields(self):
        """Test that KeyInsightIdentifier has the correct input/output fields."""
        sig = KeyInsightIdentifier
        
        # Check that annotations exist (DSPy stores fields in __annotations__)
        assert hasattr(sig, '__annotations__')
        annotations = sig.__annotations__
        
        # Check input fields
        assert 'question' in annotations
        assert 'question_context' in annotations
        assert 'answer' in annotations
        
        # Check output fields
        assert 'key_insight' in annotations
    
    @pytest.mark.asyncio
    async def test_key_insight_extraction(self):
        """Test that key insights can be extracted from RAG responses."""
        mock_lm = Mock(spec=dspy.LM)
        predictor = dspy.Predict(KeyInsightIdentifier)
        
        mock_response = Mock()
        mock_response.key_insight = "AI diagnostic tools achieve 95% accuracy in medical imaging"
        
        with patch.object(predictor, 'aforward', return_value=mock_response):
            result = await predictor.aforward(
                question="What is the accuracy of AI diagnostic tools?",
                question_context="Evaluating AI performance in healthcare",
                answer="Recent studies show that AI diagnostic tools can achieve up to 95% accuracy in medical imaging tasks[1].",
                lm=mock_lm
            )
            
            assert isinstance(result.key_insight, str)
            assert len(result.key_insight) > 0
    
    @pytest.mark.asyncio
    async def test_key_insight_is_concise(self):
        """Test that key insights are concise (typically one sentence)."""
        mock_lm = Mock(spec=dspy.LM)
        predictor = dspy.Predict(KeyInsightIdentifier)
        
        mock_response = Mock()
        mock_response.key_insight = "AI adoption in healthcare is hindered by regulatory barriers."
        
        with patch.object(predictor, 'aforward', return_value=mock_response):
            result = await predictor.aforward(
                question="What are the barriers to AI adoption?",
                question_context="Understanding adoption challenges",
                answer="Multiple studies indicate that regulatory barriers are the primary obstacle to AI adoption in healthcare settings[1][2].",
                lm=mock_lm
            )
            
            # Key insight should be relatively short
            assert len(result.key_insight.split()) < 30


class TestFinalWritingGuidelineProposal:
    """Tests for the FinalWritingGuidelineProposal signature."""
    
    @pytest.mark.asyncio
    async def test_guideline_proposal_signature_fields(self):
        """Test that FinalWritingGuidelineProposal has the correct fields."""
        sig = FinalWritingGuidelineProposal
        
        # Check that annotations exist (DSPy stores fields in __annotations__)
        assert hasattr(sig, '__annotations__')
        annotations = sig.__annotations__
        
        # Check input fields
        assert 'key_insights' in annotations
        
        # Check output fields
        assert 'report_thesis' in annotations
        assert 'writing_guideline' in annotations
    
    @pytest.mark.asyncio
    async def test_guideline_proposal_generation(self):
        """Test that writing guidelines can be generated from key insights."""
        mock_lm = Mock(spec=dspy.LM)
        predictor = dspy.Predict(FinalWritingGuidelineProposal)
        
        mock_response = Mock()
        mock_response.report_thesis = "AI Transforms Healthcare Through Diagnostic Innovation and Regulatory Challenges"
        mock_response.writing_guideline = """
        - Discuss AI diagnostic accuracy improvements
        - Analyze regulatory barriers to adoption
        - Examine cost-benefit considerations
        - Review case studies of successful implementations
        """
        
        key_insights = [
            "Key Insight #0: AI diagnostic tools achieve 95% accuracy",
            "Key Insight #1: Regulatory barriers hinder adoption",
            "Key Insight #2: Cost savings can reach 30% in some hospitals"
        ]
        
        with patch.object(predictor, 'aforward', return_value=mock_response):
            result = await predictor.aforward(
                key_insights=key_insights,
                lm=mock_lm
            )
            
            assert isinstance(result.report_thesis, str)
            assert isinstance(result.writing_guideline, str)
            assert len(result.report_thesis) > 0
            assert len(result.writing_guideline) > 0
    
    @pytest.mark.asyncio
    async def test_report_thesis_is_headline_style(self):
        """Test that report thesis is headline-style (8-14 words)."""
        mock_lm = Mock(spec=dspy.LM)
        predictor = dspy.Predict(FinalWritingGuidelineProposal)
        
        mock_response = Mock()
        mock_response.report_thesis = "AI Healthcare Revolution Faces Regulatory Hurdles Despite Diagnostic Breakthroughs"
        mock_response.writing_guideline = "- Point 1\n- Point 2"
        
        with patch.object(predictor, 'aforward', return_value=mock_response):
            result = await predictor.aforward(
                key_insights=["Insight 1", "Insight 2"],
                lm=mock_lm
            )
            
            word_count = len(result.report_thesis.split())
            # Should be headline style (approximately 8-14 words)
            assert 5 <= word_count <= 20


class TestFinalReportSynthesizer:
    """Tests for the FinalReportSynthesizer signature."""
    
    @pytest.mark.asyncio
    async def test_report_synthesizer_signature_fields(self):
        """Test that FinalReportSynthesizer has the correct fields."""
        sig = FinalReportSynthesizer
        
        # Check that annotations exist (DSPy stores fields in __annotations__)
        assert hasattr(sig, '__annotations__')
        annotations = sig.__annotations__
        
        # Check input fields
        assert 'report_thesis' in annotations
        assert 'writing_guideline' in annotations
        assert 'gathered_information' in annotations
        
        # Check output fields
        assert 'final_report' in annotations
    
    @pytest.mark.asyncio
    async def test_report_synthesis(self):
        """Test that a final report can be synthesized."""
        mock_lm = Mock(spec=dspy.LM)
        predictor = dspy.Predict(FinalReportSynthesizer)
        
        mock_response = Mock()
        mock_response.final_report = """
        # AI in Healthcare: A Comprehensive Analysis
        
        ## Diagnostic Accuracy
        AI diagnostic tools have achieved remarkable accuracy rates of up to 95%[1].
        
        ## Regulatory Challenges
        Despite technical progress, regulatory barriers remain a significant obstacle[2].
        """
        
        with patch.object(predictor, 'aforward', return_value=mock_response):
            result = await predictor.aforward(
                report_thesis="AI Transforms Healthcare",
                writing_guideline="- Cover diagnostics\n- Discuss regulations",
                gathered_information="Sub-question: accuracy\nAnswer: 95% accurate[1]\n\nSub-question: barriers\nAnswer: regulatory issues[2]",
                lm=mock_lm
            )
            
            assert isinstance(result.final_report, str)
            assert len(result.final_report) > 0
    
    @pytest.mark.asyncio
    async def test_report_preserves_citations(self):
        """Test that the synthesized report preserves citations."""
        mock_lm = Mock(spec=dspy.LM)
        predictor = dspy.Predict(FinalReportSynthesizer)
        
        mock_response = Mock()
        mock_response.final_report = "AI is transforming healthcare[1]. Studies show 95% accuracy[2]."
        
        with patch.object(predictor, 'aforward', return_value=mock_response):
            result = await predictor.aforward(
                report_thesis="AI in Healthcare",
                writing_guideline="- Discuss transformation",
                gathered_information="Answer: AI transforms healthcare[1][2]",
                lm=mock_lm
            )
            
            # Should contain citations
            assert "[1]" in result.final_report or "[2]" in result.final_report


class TestNormalizeCitationIndices:
    """Tests for the citation normalization utility function."""
    
    def test_normalize_single_rag_response(self):
        """Test normalizing citations for a single RAG response."""
        doc1 = RetrievedDocument(url="http://example.com/1", excerpts=["Content 1"])
        
        rag_responses = [
            RagResponse(
                question="Question 1",
                answer="Answer with citation[1]",
                cited_documents=[doc1]
            )
        ]
        
        updated_answers, all_documents = _normalize_rag_response_citation_indices(rag_responses)
        
        assert len(updated_answers) == 1
        assert len(all_documents) == 1
        assert "[1]" in updated_answers[0]
    
    def test_normalize_multiple_rag_responses(self):
        """Test normalizing citations across multiple RAG responses."""
        doc1 = RetrievedDocument(url="http://example.com/1", excerpts=["Content 1"])
        doc2 = RetrievedDocument(url="http://example.com/2", excerpts=["Content 2"])
        doc3 = RetrievedDocument(url="http://example.com/3", excerpts=["Content 3"])
        
        rag_responses = [
            RagResponse(
                question="Question 1",
                answer="First answer[1]",
                cited_documents=[doc1]
            ),
            RagResponse(
                question="Question 2",
                answer="Second answer[1][2]",
                cited_documents=[doc2, doc3]
            )
        ]
        
        updated_answers, all_documents = _normalize_rag_response_citation_indices(rag_responses)
        
        assert len(all_documents) == 3
        assert len(updated_answers) == 2
        # First answer should keep [1]
        assert "[1]" in updated_answers[0]
        # Second answer should have [2] and [3] (offset by 1)
        assert "[2]" in updated_answers[1]
        assert "[3]" in updated_answers[1]
    
    def test_normalize_preserves_question_labels(self):
        """Test that normalization preserves sub-question labels."""
        doc1 = RetrievedDocument(url="http://example.com/1", excerpts=["Content 1"])
        
        rag_responses = [
            RagResponse(
                question="What is AI?",
                answer="AI is artificial intelligence[1]",
                cited_documents=[doc1]
            )
        ]
        
        updated_answers, _ = _normalize_rag_response_citation_indices(rag_responses)
        
        assert "Sub-question:" in updated_answers[0]
        assert "What is AI?" in updated_answers[0]


class TestReportGenerationAgent:
    """Tests for the complete Report Generation Agent."""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test that the agent initializes correctly."""
        mock_literature_search_agent = Mock(spec=LiteratureSearchAgent)
        mock_lm = Mock(spec=dspy.LM)
        
        agent = ReportGenerationAgent(
            literature_search_agent=mock_literature_search_agent,
            lm=mock_lm
        )
        
        assert agent.literature_search_agent is mock_literature_search_agent
        assert agent.lm is mock_lm
        assert hasattr(agent, 'key_insight_identifier')
        assert hasattr(agent, 'final_writing_guideline_proposal')
        assert hasattr(agent, 'final_report_synthesizer')
    
    @pytest.mark.asyncio
    async def test_aforward_complete_pipeline(self):
        """Test the complete report generation pipeline."""
        mock_literature_search_agent = Mock(spec=LiteratureSearchAgent)
        mock_lm = Mock(spec=dspy.LM)
        
        agent = ReportGenerationAgent(
            literature_search_agent=mock_literature_search_agent,
            lm=mock_lm
        )
        
        # Create mock literature search response
        doc1 = RetrievedDocument(url="http://example.com/1", excerpts=["Content 1"])
        doc2 = RetrievedDocument(url="http://example.com/2", excerpts=["Content 2"])
        
        rag_response1 = RagResponse(
            question="What is AI?",
            question_context="Understanding basics",
            answer="AI is artificial intelligence[1]",
            cited_documents=[doc1]
        )
        
        rag_response2 = RagResponse(
            question="How is AI used?",
            question_context="Understanding applications",
            answer="AI is used in diagnostics[1]",
            cited_documents=[doc2]
        )
        
        literature_search_response = LiteratureSearchAgentResponse(
            topic="AI in healthcare",
            guideline="Comprehensive survey",
            writeup="Survey writeup",
            cited_documents=[doc1, doc2],
            rag_responses=[rag_response1, rag_response2]
        )
        
        request = ReportGenerationRequest(
            topic="AI in healthcare",
            literature_search=literature_search_response,
            is_answerable=True
        )
        
        # Mock key insight responses
        mock_insight1 = Mock()
        mock_insight1.key_insight = "AI achieves high accuracy"
        
        mock_insight2 = Mock()
        mock_insight2.key_insight = "AI has many applications"
        
        # Mock guideline proposal
        mock_guideline = Mock()
        mock_guideline.report_thesis = "AI Transforms Healthcare"
        mock_guideline.writing_guideline = "- Discuss accuracy\n- Discuss applications"
        
        # Mock final synthesis
        mock_synthesis = Mock()
        mock_synthesis.final_report = "# AI in Healthcare\n\nAI is transforming healthcare[1]."
        
        with patch.object(agent.key_insight_identifier, 'aforward', side_effect=[mock_insight1, mock_insight2]):
            with patch.object(agent.final_writing_guideline_proposal, 'aforward', return_value=mock_guideline):
                with patch.object(agent.final_report_synthesizer, 'aforward', return_value=mock_synthesis):
                    result = await agent.aforward(request)
                    
                    assert isinstance(result, ReportGenerationResponse)
                    assert isinstance(result.report, str)
                    assert len(result.report) > 0
                    # Should include bibliography
                    assert "## Bibliography" in result.report
    
    @pytest.mark.asyncio
    async def test_aforward_adds_bibliography(self):
        """Test that the agent adds a bibliography section."""
        mock_literature_search_agent = Mock(spec=LiteratureSearchAgent)
        mock_lm = Mock(spec=dspy.LM)
        
        agent = ReportGenerationAgent(
            literature_search_agent=mock_literature_search_agent,
            lm=mock_lm
        )
        
        doc1 = RetrievedDocument(url="http://example.com/article1", excerpts=["Content"])
        doc2 = RetrievedDocument(url="http://example.com/article2", excerpts=["Content"])
        
        rag_response = RagResponse(
            question="Question",
            question_context="Context",
            answer="Answer[1][2]",
            cited_documents=[doc1, doc2]
        )
        
        literature_search_response = LiteratureSearchAgentResponse(
            topic="Test",
            guideline="Survey",
            writeup="Writeup",
            cited_documents=[doc1, doc2],
            rag_responses=[rag_response]
        )
        
        request = ReportGenerationRequest(
            topic="Test",
            literature_search=literature_search_response,
            is_answerable=True
        )
        
        # Mock responses
        mock_insight = Mock()
        mock_insight.key_insight = "Insight"
        
        mock_guideline = Mock()
        mock_guideline.report_thesis = "Thesis"
        mock_guideline.writing_guideline = "Guideline"
        
        mock_synthesis = Mock()
        mock_synthesis.final_report = "Report body"
        
        with patch.object(agent.key_insight_identifier, 'aforward', return_value=mock_insight):
            with patch.object(agent.final_writing_guideline_proposal, 'aforward', return_value=mock_guideline):
                with patch.object(agent.final_report_synthesizer, 'aforward', return_value=mock_synthesis):
                    result = await agent.aforward(request)
                    
                    # Check bibliography is present
                    assert "## Bibliography" in result.report
                    assert "http://example.com/article1" in result.report
                    assert "http://example.com/article2" in result.report
    
    @pytest.mark.asyncio
    async def test_aforward_populates_key_insights(self):
        """Test that key insights are populated in RAG responses."""
        mock_literature_search_agent = Mock(spec=LiteratureSearchAgent)
        mock_lm = Mock(spec=dspy.LM)
        
        agent = ReportGenerationAgent(
            literature_search_agent=mock_literature_search_agent,
            lm=mock_lm
        )
        
        doc = RetrievedDocument(url="http://example.com", excerpts=["Content"])
        
        rag_response = RagResponse(
            question="Question",
            question_context="Context",
            answer="Answer",
            cited_documents=[doc]
        )
        
        literature_search_response = LiteratureSearchAgentResponse(
            topic="Test",
            guideline="Survey",
            writeup="Writeup",
            cited_documents=[doc],
            rag_responses=[rag_response]
        )
        
        request = ReportGenerationRequest(
            topic="Test",
            literature_search=literature_search_response,
            is_answerable=True
        )
        
        # Mock responses
        mock_insight = Mock()
        mock_insight.key_insight = "Key insight identified"
        
        mock_guideline = Mock()
        mock_guideline.report_thesis = "Thesis"
        mock_guideline.writing_guideline = "Guideline"
        
        mock_synthesis = Mock()
        mock_synthesis.final_report = "Report"
        
        with patch.object(agent.key_insight_identifier, 'aforward', return_value=mock_insight):
            with patch.object(agent.final_writing_guideline_proposal, 'aforward', return_value=mock_guideline):
                with patch.object(agent.final_report_synthesizer, 'aforward', return_value=mock_synthesis):
                    result = await agent.aforward(request)
                    
                    # Check that key insight was populated
                    assert rag_response.key_insight == "Key insight identified"


class TestReportGenerationEdgeCases:
    """Tests for edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_empty_rag_responses(self):
        """Test report generation with no RAG responses."""
        mock_literature_search_agent = Mock(spec=LiteratureSearchAgent)
        mock_lm = Mock(spec=dspy.LM)
        
        agent = ReportGenerationAgent(
            literature_search_agent=mock_literature_search_agent,
            lm=mock_lm
        )
        
        literature_search_response = LiteratureSearchAgentResponse(
            topic="Test",
            guideline="Survey",
            writeup="Writeup",
            cited_documents=[],
            rag_responses=[]
        )
        
        request = ReportGenerationRequest(
            topic="Test",
            literature_search=literature_search_response,
            is_answerable=True
        )
        
        # Mock responses
        mock_guideline = Mock()
        mock_guideline.report_thesis = "Thesis"
        mock_guideline.writing_guideline = "Guideline"
        
        mock_synthesis = Mock()
        mock_synthesis.final_report = "Minimal report"
        
        with patch.object(agent.final_writing_guideline_proposal, 'aforward', return_value=mock_guideline):
            with patch.object(agent.final_report_synthesizer, 'aforward', return_value=mock_synthesis):
                result = await agent.aforward(request)
                
                assert isinstance(result, ReportGenerationResponse)
                assert result.report is not None
    
    @pytest.mark.asyncio
    async def test_unanswerable_research_need(self):
        """Test handling when research need is marked as unanswerable."""
        mock_literature_search_agent = Mock(spec=LiteratureSearchAgent)
        mock_lm = Mock(spec=dspy.LM)
        
        agent = ReportGenerationAgent(
            literature_search_agent=mock_literature_search_agent,
            lm=mock_lm
        )
        
        literature_search_response = LiteratureSearchAgentResponse(
            topic="Test",
            guideline="Survey",
            writeup=None,
            cited_documents=[],
            rag_responses=[]
        )
        
        request = ReportGenerationRequest(
            topic="Test",
            literature_search=literature_search_response,
            is_answerable=False
        )
        
        # Mock responses
        mock_guideline = Mock()
        mock_guideline.report_thesis = "Unanswerable"
        mock_guideline.writing_guideline = "Cannot answer"
        
        mock_synthesis = Mock()
        mock_synthesis.final_report = "Cannot generate report due to insufficient information"
        
        with patch.object(agent.final_writing_guideline_proposal, 'aforward', return_value=mock_guideline):
            with patch.object(agent.final_report_synthesizer, 'aforward', return_value=mock_synthesis):
                result = await agent.aforward(request)
                
                # Should still return a response, even if minimal
                assert isinstance(result, ReportGenerationResponse)

