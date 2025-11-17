# Test Suite Documentation

This directory contains comprehensive test suites for the presearcher pipeline. Each test file covers a specific component of the pipeline.

## Pipeline Steps Overview

The presearcher pipeline consists of the following steps:

### 1. Purpose Generation (`test_purpose_generation.py`)
- **1a. Persona Generation**: Generate personas of people who would request the research
- **1b. Research Needs Generation**: Generate specific research needs for each persona
- **1c. Research Needs Reranking**: Filter and prioritize the most insightful research needs

### 2. Outline Generation (`test_outline_generation.py`)
- **2a. Outline Generation**: Create a structured outline for the final report based on the research question and purposes

### 3. Literature Search (`test_literature_search.py`)
- **3a. Completeness Checking**: Determine if sufficient information has been gathered
- **3b. Next Question Planning**: Generate strategic next questions to explore
- **3c. Parallel RAG Execution**: Execute multiple RAG calls in parallel
- **3d. Answer Synthesis**: Synthesize answers from multiple RAG responses

### 4. RAG Agent (`test_rag_agent.py`)
- **4a. Question to Query Conversion**: Convert questions to search queries
- **4b. Document Retrieval**: Retrieve relevant documents from the internet
- **4c. Answer Generation**: Generate answers with inline citations

### 5. Report Generation (`test_report_generation.py`)
- **5a. Key Insight Identification**: Extract key insights from RAG responses
- **5b. Writing Guideline Proposal**: Propose thesis and writing guidelines
- **5c. Final Report Synthesis**: Synthesize a comprehensive report

### 6. Report Combination (`test_presearcher_agent.py`)
- **6a. Report Combiner**: Combine multiple reports into a single comprehensive document

### 7. Data Classes (`test_dataclasses.py`)
- Serialization and deserialization tests for all data structures

## Test Files

### `test_purpose_generation.py`
Tests for the Purpose Generation Agent including:
- `TestPersonaGeneration`: Tests for persona generation signature
- `TestResearchNeedsGeneration`: Tests for research needs generation
- `TestResearchNeedsReranking`: Tests for reranking logic
- `TestPurposeGenerationAgent`: Integration tests for the full agent
- `TestPurposeGenerationEdgeCases`: Edge case handling

### `test_outline_generation.py`
Tests for the Outline Generation Agent including:
- `TestOutlineGenerationAgent`: Basic functionality tests
- `TestOutlineGenerationResponse`: Response structure tests
- `TestOutlineGenerationEdgeCases`: Edge cases with special characters
- `TestOutlineGenerationIntegration`: Integration with purpose generation

### `test_rag_agent.py`
Tests for the RAG Agent including:
- `TestQuestionToQuery`: Query conversion tests
- `TestRAGAnswerGeneration`: Answer generation with citations
- `TestRagAgent`: Complete RAG pipeline tests
- `TestRagAgentEdgeCases`: Error handling and edge cases
- `TestRagResponse`: Response serialization tests

### `test_literature_search.py`
Tests for the Literature Search Agent including:
- `TestNextStepPlanner`: Completeness checking and planning
- `TestLiteratureSearchAnswerGeneration`: Answer synthesis tests
- `TestLiteratureSearchAnswerGenerationModule`: Citation normalization
- `TestLiteratureSearchAgent`: Complete agent pipeline tests
- `TestLiteratureSearchEdgeCases`: Edge case handling

### `test_report_generation.py`
Tests for the Report Generation Agent including:
- `TestKeyInsightIdentifier`: Key insight extraction tests
- `TestFinalWritingGuidelineProposal`: Guideline generation tests
- `TestFinalReportSynthesizer`: Report synthesis tests
- `TestNormalizeCitationIndices`: Citation normalization utility
- `TestReportGenerationAgent`: Complete agent pipeline tests
- `TestReportGenerationEdgeCases`: Edge case handling

### `test_presearcher_agent.py`
Tests for the main Presearcher Agent including:
- `TestPresearcherAgent`: End-to-end pipeline tests
- `TestPresearcherAgentRequest`: Request dataclass tests
- `TestPresearcherAgentResponse`: Response dataclass tests
- `TestPresearcherAgentEdgeCases`: Edge cases and error handling

### `test_dataclasses.py`
Tests for all data classes including:
- `TestDocumentType`: Enum tests
- `TestRetrievedDocument`: Document dataclass tests
- `TestRagRequest` and `TestRagResponse`: RAG dataclass tests
- `TestLiteratureSearchAgentRequest` and `TestLiteratureSearchAgentResponse`: Literature search dataclass tests
- `TestPresearcherAgentRequest` and `TestPresearcherAgentResponse`: Presearcher dataclass tests
- `TestReportGenerationRequest` and `TestReportGenerationResponse`: Report generation dataclass tests
- `TestDataclassEdgeCases`: Edge cases for all dataclasses

## Running Tests

### Run all tests
```bash
pytest tests/
```

### Run a specific test file
```bash
pytest tests/test_purpose_generation.py
```

### Run a specific test class
```bash
pytest tests/test_purpose_generation.py::TestPersonaGeneration
```

### Run a specific test
```bash
pytest tests/test_purpose_generation.py::TestPersonaGeneration::test_persona_generation_signature_fields
```

### Run with verbose output
```bash
pytest tests/ -v
```

### Run with coverage report
```bash
pytest tests/ --cov=src --cov-report=html
```

### Run only async tests
```bash
pytest tests/ -m asyncio
```

## Test Coverage

The test suite covers:

1. **Unit Tests**: Individual functions and methods
2. **Integration Tests**: Component interactions
3. **Edge Cases**: Boundary conditions and error handling
4. **Serialization Tests**: Data persistence and transfer
5. **Mock Tests**: External dependencies mocked for isolation

## Key Testing Patterns

### Mocking Language Models
```python
mock_lm = Mock(spec=dspy.LM)
predictor = dspy.Predict(Signature)

with patch.object(predictor, 'aforward', return_value=mock_response):
    result = await predictor.aforward(...)
```

### Testing Async Functions
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### Testing Data Serialization
```python
original = DataClass(...)
serialized = original.to_dict()
deserialized = DataClass.from_dict(serialized)
assert deserialized.field == original.field
```

## Adding New Tests

When adding new features to the pipeline:

1. Create corresponding test methods in the appropriate test file
2. Follow the existing naming convention: `test_<feature_description>`
3. Include docstrings explaining what is being tested
4. Add both positive and negative test cases
5. Test edge cases and error conditions
6. Update this README if adding new test files

## Dependencies

The test suite requires:
- `pytest>=7.0.0`
- `pytest-asyncio>=0.21.0`
- `pytest-cov>=4.0.0` (for coverage reports)

Install test dependencies:
```bash
pip install pytest pytest-asyncio pytest-cov
```

## Continuous Integration

These tests should be run in CI/CD pipelines before merging any changes to ensure:
- All existing functionality continues to work
- New features are properly tested
- Code quality standards are maintained

