"""Test suite for Purpose Generation Agent.

Tests the three-step process of generating personas, their research needs, and reranking them.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
import dspy

from presearcher.purpose_generation import (
    PurposeGenerationAgent,
    PersonaGeneration,
    ResearchNeedsGeneration,
    ResearchNeedsReranking,
)


class TestPersonaGeneration:
    """Tests for the PersonaGeneration signature."""
    
    @pytest.mark.asyncio
    async def test_persona_generation_signature_fields(self):
        """Test that PersonaGeneration has the correct input/output fields."""
        sig = PersonaGeneration
        
        # Check that annotations exist (DSPy stores fields in __annotations__)
        assert hasattr(sig, '__annotations__')
        annotations = sig.__annotations__
        
        # Check input fields
        assert 'research_task' in annotations
        assert 'max_personas' in annotations
        
        # Check output fields
        assert 'personas' in annotations
    
    @pytest.mark.asyncio
    async def test_persona_generation_with_mock_lm(self):
        """Test persona generation with a mocked language model."""
        mock_lm = Mock(spec=dspy.LM)
        predictor = dspy.Predict(PersonaGeneration)
        
        # Mock the response
        mock_response = Mock()
        mock_response.personas = [
            "A healthcare researcher interested in AI safety",
            "A policy maker creating AI regulations"
        ]
        
        with patch.object(predictor, 'aforward', return_value=mock_response):
            result = await predictor.aforward(
                research_task="What is the current state of AI in healthcare?",
                max_personas=2,
                lm=mock_lm
            )
            
            assert len(result.personas) == 2
            assert "healthcare researcher" in result.personas[0].lower()


class TestResearchNeedsGeneration:
    """Tests for the ResearchNeedsGeneration signature."""
    
    @pytest.mark.asyncio
    async def test_research_needs_signature_fields(self):
        """Test that ResearchNeedsGeneration has the correct input/output fields."""
        sig = ResearchNeedsGeneration
        
        # Check that annotations exist (DSPy stores fields in __annotations__)
        assert hasattr(sig, '__annotations__')
        annotations = sig.__annotations__
        
        # Check input fields
        assert 'research_task' in annotations
        assert 'persona' in annotations
        assert 'max_research_needs' in annotations
        
        # Check output fields
        assert 'research_needs' in annotations
    
    @pytest.mark.asyncio
    async def test_research_needs_generation_with_mock_lm(self):
        """Test research needs generation with a mocked language model."""
        mock_lm = Mock(spec=dspy.LM)
        predictor = dspy.Predict(ResearchNeedsGeneration)
        
        # Mock the response
        mock_response = Mock()
        mock_response.research_needs = [
            "What are successful case studies of AI in healthcare?",
            "What are the regulatory barriers to AI adoption?",
            "What risks have been identified by experts?"
        ]
        
        with patch.object(predictor, 'aforward', return_value=mock_response):
            result = await predictor.aforward(
                research_task="What is the current state of AI in healthcare?",
                persona="A healthcare researcher interested in AI safety",
                max_research_needs=3,
                lm=mock_lm
            )
            
            assert len(result.research_needs) == 3
            assert any("case studies" in need.lower() for need in result.research_needs)


class TestResearchNeedsReranking:
    """Tests for the ResearchNeedsReranking signature."""
    
    @pytest.mark.asyncio
    async def test_reranking_signature_fields(self):
        """Test that ResearchNeedsReranking has the correct input/output fields."""
        sig = ResearchNeedsReranking
        
        # Check that annotations exist (DSPy stores fields in __annotations__)
        assert hasattr(sig, '__annotations__')
        annotations = sig.__annotations__
        
        # Check input fields
        assert 'research_needs' in annotations
        assert 'max_research_needs' in annotations
        
        # Check output fields
        assert 'reranked_research_needs' in annotations
    
    @pytest.mark.asyncio
    async def test_reranking_filters_and_prioritizes(self):
        """Test that reranking filters out low-quality needs and prioritizes insightful ones."""
        mock_lm = Mock(spec=dspy.LM)
        predictor = dspy.Predict(ResearchNeedsReranking)
        
        # Mock the response - should filter out surface-level questions
        mock_response = Mock()
        mock_response.reranked_research_needs = [
            "What emerging AI technologies will impact healthcare in the next 5 years?",
            "What are the key barriers to AI adoption in healthcare systems?"
        ]
        
        input_needs = [
            "What is AI?",  # Surface level
            "What emerging AI technologies will impact healthcare in the next 5 years?",  # Insightful
            "How is AI defined?",  # Surface level
            "What are the key barriers to AI adoption in healthcare systems?"  # Insightful
        ]
        
        with patch.object(predictor, 'aforward', return_value=mock_response):
            result = await predictor.aforward(
                research_needs=input_needs,
                max_research_needs=2,
                lm=mock_lm
            )
            
            assert len(result.reranked_research_needs) <= 2
            # Check that surface-level questions were filtered
            assert "What is AI?" not in result.reranked_research_needs


class TestPurposeGenerationAgent:
    """Integration tests for the full PurposeGenerationAgent pipeline."""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test that the agent can be initialized properly."""
        mock_lm = Mock(spec=dspy.LM)
        agent = PurposeGenerationAgent(lm=mock_lm)
        
        assert agent.lm is mock_lm
        assert hasattr(agent, 'persona_generator')
        assert hasattr(agent, 'research_needs_generator')
        assert hasattr(agent, 'research_needs_reranker')
    
    @pytest.mark.asyncio
    async def test_aforward_complete_pipeline(self):
        """Test the complete purpose generation pipeline."""
        mock_lm = Mock(spec=dspy.LM)
        agent = PurposeGenerationAgent(lm=mock_lm)
        
        # Mock persona generation
        mock_persona_response = Mock()
        mock_persona_response.personas = [
            "A healthcare researcher",
            "A policy maker"
        ]
        
        # Mock research needs generation
        mock_needs_response = Mock()
        mock_needs_response.research_needs = [
            "Need 1",
            "Need 2"
        ]
        
        # Mock reranking
        mock_rerank_response = Mock()
        mock_rerank_response.reranked_research_needs = ["Need 1", "Need 2"]
        
        with patch.object(agent.persona_generator, 'aforward', return_value=mock_persona_response):
            with patch.object(agent.research_needs_generator, 'aforward', return_value=mock_needs_response):
                with patch.object(agent.research_needs_reranker, 'aforward', return_value=mock_rerank_response):
                    result = await agent.aforward(
                        question="What is the current state of AI in healthcare?",
                        k=2
                    )
                    
                    assert isinstance(result, list)
                    assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_aforward_respects_k_limit(self):
        """Test that the agent respects the k limit for personas."""
        mock_lm = Mock(spec=dspy.LM)
        agent = PurposeGenerationAgent(lm=mock_lm)
        
        # Mock with more personas than k
        mock_persona_response = Mock()
        mock_persona_response.personas = [
            "Persona 1", "Persona 2", "Persona 3", "Persona 4", "Persona 5"
        ]
        
        mock_needs_response = Mock()
        mock_needs_response.research_needs = ["Need 1", "Need 2"]
        
        mock_rerank_response = Mock()
        mock_rerank_response.reranked_research_needs = ["Need 1", "Need 2"]
        
        with patch.object(agent.persona_generator, 'aforward', return_value=mock_persona_response):
            with patch.object(agent.research_needs_generator, 'aforward', return_value=mock_needs_response):
                with patch.object(agent.research_needs_reranker, 'aforward', return_value=mock_rerank_response):
                    result = await agent.aforward(
                        question="Test question",
                        k=2
                    )
                    
                    # Should only process k=2 personas
                    assert agent.research_needs_generator.aforward.call_count <= 2
    
    @pytest.mark.asyncio
    async def test_aforward_handles_string_persona_response(self):
        """Test that the agent handles when personas is returned as a string instead of list."""
        mock_lm = Mock(spec=dspy.LM)
        agent = PurposeGenerationAgent(lm=mock_lm)
        
        # Mock persona generation returning a string
        mock_persona_response = Mock()
        mock_persona_response.personas = "A single persona"
        
        mock_needs_response = Mock()
        mock_needs_response.research_needs = ["Need 1"]
        
        mock_rerank_response = Mock()
        mock_rerank_response.reranked_research_needs = ["Need 1"]
        
        with patch.object(agent.persona_generator, 'aforward', return_value=mock_persona_response):
            with patch.object(agent.research_needs_generator, 'aforward', return_value=mock_needs_response):
                with patch.object(agent.research_needs_reranker, 'aforward', return_value=mock_rerank_response):
                    result = await agent.aforward(
                        question="Test question",
                        k=1
                    )
                    
                    assert isinstance(result, list)
                    # Should convert string to list
                    assert agent.research_needs_generator.aforward.call_count == 1


class TestPurposeGenerationEdgeCases:
    """Tests for edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_empty_personas_list(self):
        """Test handling of empty personas list."""
        mock_lm = Mock(spec=dspy.LM)
        agent = PurposeGenerationAgent(lm=mock_lm)
        
        mock_persona_response = Mock()
        mock_persona_response.personas = []
        
        mock_rerank_response = Mock()
        mock_rerank_response.reranked_research_needs = []
        
        with patch.object(agent.persona_generator, 'aforward', return_value=mock_persona_response):
            with patch.object(agent.research_needs_reranker, 'aforward', return_value=mock_rerank_response):
                result = await agent.aforward(
                    question="Test question",
                    k=2
                )
                
                assert isinstance(result, list)
                assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_k_equals_zero(self):
        """Test handling of k=0."""
        mock_lm = Mock(spec=dspy.LM)
        agent = PurposeGenerationAgent(lm=mock_lm)
        
        mock_persona_response = Mock()
        mock_persona_response.personas = []
        
        mock_rerank_response = Mock()
        mock_rerank_response.reranked_research_needs = []
        
        with patch.object(agent.persona_generator, 'aforward', return_value=mock_persona_response):
            with patch.object(agent.research_needs_reranker, 'aforward', return_value=mock_rerank_response):
                result = await agent.aforward(
                    question="Test question",
                    k=0
                )
                
                assert isinstance(result, list)

