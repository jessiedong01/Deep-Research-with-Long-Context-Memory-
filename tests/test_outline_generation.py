"""Test suite for Outline Generation Agent.

Tests the outline generation process for creating structured report outlines.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
import dspy

from outline_generation import OutlineGenerationAgent, OutlineGenerationResponse


class TestOutlineGenerationAgent:
    """Tests for the OutlineGenerationAgent."""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test that the agent can be initialized properly."""
        mock_lm = Mock(spec=dspy.LM)
        agent = OutlineGenerationAgent(lm=mock_lm)
        
        assert agent.lm is mock_lm
    
    @pytest.mark.asyncio
    async def test_aforward_returns_correct_structure(self):
        """Test that aforward returns the correct response structure."""
        mock_lm = Mock(spec=dspy.LM)
        mock_lm.aforward = AsyncMock(return_value="# Outline\n## Section 1\n## Section 2")
        
        agent = OutlineGenerationAgent(lm=mock_lm)
        
        purposes = [
            "Understand AI safety in healthcare",
            "Determine regulatory requirements"
        ]
        
        result = await agent.aforward(
            question="What is the current state of AI in healthcare?",
            purposes=purposes
        )
        
        assert isinstance(result, dict)
        assert "markdown" in result
        assert "parsed_outline" in result
        assert isinstance(result["markdown"], str)
        assert isinstance(result["parsed_outline"], dict)
    
    @pytest.mark.asyncio
    async def test_aforward_generates_markdown_outline(self):
        """Test that the outline is generated as markdown."""
        mock_lm = Mock(spec=dspy.LM)
        expected_outline = "# Main Topic\n## Subtopic 1\n### Detail 1\n## Subtopic 2"
        mock_lm.aforward = AsyncMock(return_value=expected_outline)
        
        agent = OutlineGenerationAgent(lm=mock_lm)
        
        result = await agent.aforward(
            question="Test question",
            purposes=["Purpose 1"]
        )
        
        assert result["markdown"] == expected_outline
        assert "#" in result["markdown"]  # Contains markdown headers
    
    @pytest.mark.asyncio
    async def test_aforward_with_empty_purposes(self):
        """Test outline generation with empty purposes list."""
        mock_lm = Mock(spec=dspy.LM)
        mock_lm.aforward = AsyncMock(return_value="# Basic Outline")
        
        agent = OutlineGenerationAgent(lm=mock_lm)
        
        result = await agent.aforward(
            question="Test question",
            purposes=[]
        )
        
        assert isinstance(result, dict)
        assert result["markdown"] is not None
    
    @pytest.mark.asyncio
    async def test_aforward_with_multiple_purposes(self):
        """Test outline generation with multiple purposes."""
        mock_lm = Mock(spec=dspy.LM)
        mock_lm.aforward = AsyncMock(return_value="# Comprehensive Outline\n## Section for Purpose 1\n## Section for Purpose 2\n## Section for Purpose 3")
        
        agent = OutlineGenerationAgent(lm=mock_lm)
        
        purposes = [
            "Purpose 1: Technical analysis",
            "Purpose 2: Market research",
            "Purpose 3: Regulatory compliance"
        ]
        
        result = await agent.aforward(
            question="Complex research question",
            purposes=purposes
        )
        
        assert result["markdown"] is not None
        assert len(result["markdown"]) > 0
    
    @pytest.mark.asyncio
    async def test_parsed_outline_is_dict(self):
        """Test that parsed_outline is always a dictionary."""
        mock_lm = Mock(spec=dspy.LM)
        mock_lm.aforward = AsyncMock(return_value="# Outline")
        
        agent = OutlineGenerationAgent(lm=mock_lm)
        
        result = await agent.aforward(
            question="Test",
            purposes=["Purpose"]
        )
        
        assert isinstance(result["parsed_outline"], dict)


class TestOutlineGenerationResponse:
    """Tests for the OutlineGenerationResponse dataclass."""
    
    def test_response_structure(self):
        """Test that OutlineGenerationResponse has the correct structure."""
        # This is a type annotation class with __annotations__
        # Just verify it exists and has the expected type annotations
        assert hasattr(OutlineGenerationResponse, '__annotations__')
        annotations = OutlineGenerationResponse.__annotations__
        assert 'markdown' in annotations
        assert 'parsed_outline' in annotations


class TestOutlineGenerationEdgeCases:
    """Tests for edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_long_question(self):
        """Test outline generation with a very long question."""
        mock_lm = Mock(spec=dspy.LM)
        mock_lm.aforward = AsyncMock(return_value="# Detailed Outline")
        
        agent = OutlineGenerationAgent(lm=mock_lm)
        
        long_question = "What are the implications of " + "AI " * 100 + "in healthcare?"
        
        result = await agent.aforward(
            question=long_question,
            purposes=["Purpose 1"]
        )
        
        assert result["markdown"] is not None
        # Verify the LM was called with the long question
        mock_lm.aforward.assert_called_once_with(long_question)
    
    @pytest.mark.asyncio
    async def test_special_characters_in_question(self):
        """Test outline generation with special characters."""
        mock_lm = Mock(spec=dspy.LM)
        mock_lm.aforward = AsyncMock(return_value="# Outline")
        
        agent = OutlineGenerationAgent(lm=mock_lm)
        
        special_question = "What is AI's impact on healthcare? (2024 & beyond)"
        
        result = await agent.aforward(
            question=special_question,
            purposes=["Purpose 1"]
        )
        
        assert result["markdown"] is not None
    
    @pytest.mark.asyncio
    async def test_unicode_in_purposes(self):
        """Test outline generation with unicode characters in purposes."""
        mock_lm = Mock(spec=dspy.LM)
        mock_lm.aforward = AsyncMock(return_value="# Outline 概要")
        
        agent = OutlineGenerationAgent(lm=mock_lm)
        
        purposes = [
            "研究目的: Technical analysis",
            "Propósito: Market research"
        ]
        
        result = await agent.aforward(
            question="Test question",
            purposes=purposes
        )
        
        assert result["markdown"] is not None


class TestOutlineGenerationIntegration:
    """Integration tests for outline generation with the pipeline."""
    
    @pytest.mark.asyncio
    async def test_outline_integrates_with_purposes(self):
        """Test that outline generation can work with purpose generation output."""
        mock_lm = Mock(spec=dspy.LM)
        mock_lm.aforward = AsyncMock(return_value="# Healthcare AI Report\n## Safety Analysis\n## Regulatory Framework\n## Market Trends")
        
        agent = OutlineGenerationAgent(lm=mock_lm)
        
        # Simulated output from purpose generation
        purposes = [
            "A healthcare researcher interested in AI safety",
            "A policy maker creating AI regulations",
            "A hedge fund manager researching healthcare AI investments"
        ]
        
        result = await agent.aforward(
            question="What is the current state of AI in healthcare?",
            purposes=purposes
        )
        
        assert "markdown" in result
        assert len(result["markdown"]) > 0
        # Check that outline contains relevant sections
        outline_lower = result["markdown"].lower()
        assert any(term in outline_lower for term in ["section", "chapter", "##", "#"])

