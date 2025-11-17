# Presearcher

**Presearcher** is an AI-powered research agent that conducts deep, structured research on complex topics by generating research personas, identifying key research needs, and synthesizing comprehensive reports from web sources.

## 🎯 Overview

Given a research topic, Presearcher:

1. **Generates diverse personas** who might need answers to this research question
2. **Identifies key research needs** specific to each persona's goals
3. **Conducts targeted literature searches** using RAG (Retrieval-Augmented Generation)
4. **Synthesizes findings** into comprehensive, evidence-based reports with citations

This approach ensures research reports address multiple perspectives and provide actionable insights rather than surface-level information.

## 🏗️ Architecture

Presearcher is built using a multi-agent pipeline powered by [DSPy](https://github.com/stanfordnlp/dspy):

### Core Agents

- **Ansatz Agent**: Generates research personas and identifies specific research needs using a three-step process:

  - Persona generation (who would ask this question and why?)
  - Research needs identification (what information does each persona need?)
  - Research needs reranking (prioritize most impactful and actionable needs)

- **Literature Search Agent**: Conducts iterative web searches using RAG to gather relevant information for each research need

- **Report Generation Agent**: Synthesizes literature search results into cohesive, well-cited reports

- **Presearcher Agent**: Orchestrates the entire pipeline and combines individual reports into a final comprehensive document

### Supporting Components

- **RAG Agent**: Retrieval-augmented generation using web search results
- **Serper RM**: Google search integration via Serper API
- **Web Scraper**: Content extraction using Crawl4AI
- **Encoder**: Semantic embeddings using OpenAI's text-embedding-3-large

## 📋 Prerequisites

- Python 3.13 or higher
- [uv](https://github.com/astral-sh/uv) package manager (recommended)
- API keys for:
  - Azure OpenAI (for GPT models and embeddings)
  - Serper API (for web search)

## 🛠️ Installation

### Using uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-username/224v-final-project.git
cd 224v-final-project

# Install dependencies
uv sync

# Install with development dependencies
uv sync --extra dev
```

### Using pip

```bash
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

## ⚙️ Configuration

Create a `.env` file in the project root:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_BASE=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-01

# Serper API Key (for web search)
SERPER_API_KEY=your_serper_api_key
```

## 🚀 Usage

### Running the Interactive Pipeline

```bash
# Using uv
uv run python -m presearcher.main

# Using standard Python
python -m presearcher.main
```

You'll be prompted to enter a research topic. Example:

```
Please enter your research task or topic: What are the most effective policy interventions for addressing global warming?
```

### Output

Results are saved to the `output/` directory:

- `results.json` - Full results including all intermediate steps
- `report.md` - Final synthesized report in Markdown
- `report.html` - Final report as HTML
- `presearcher.jsonl` - Execution logs

### Example Output

For the prompt "What are the most effective policy interventions for addressing global warming?", Presearcher generates a comprehensive report covering:

- Proven policy interventions (carbon pricing, regulations, sector-specific packages)
- Adaptation and behavior change strategies
- Feasibility analysis and implementation barriers
- Evidence-based recommendations with citations

See `output/report.md` for a complete example.

## 📁 Project Structure

```
224v-final-project/
├── src/
│   ├── presearcher/
│   │   ├── __init__.py
│   │   ├── main.py                  # Entry point
│   │   ├── presearcher.py           # Main orchestration agent
│   │   ├── ansatz.py                # Persona & research needs generation
│   │   ├── report_generation.py     # Report synthesis
│   │   └── init_pipeline.py         # Agent initialization
│   └── utils/
│       ├── dataclass.py             # Data structures
│       ├── encoder.py               # Text embeddings
│       ├── literature_search.py     # Literature search agent
│       ├── lm.py                    # Language model setup
│       ├── rag.py                   # RAG implementation
│       ├── render_output.py         # Report rendering
│       └── retriever_agent/
│           ├── internet_retriever.py
│           ├── retriever.py         # Base retriever
│           ├── serper_rm.py         # Serper API integration
│           └── web_scraper_agent.py # Web scraping
├── scripts/
│   └── render_markdown.py           # Markdown to HTML conversion
├── output/                          # Generated reports and results
├── tests/
├── pyproject.toml
└── README.md
```

## 🔬 How It Works

### Research Pipeline

1. **Topic Input**: User provides a research question or topic

2. **Ansatz Generation** (Hypothesis Formation):

   - Generate diverse personas who might ask this question
   - For each persona, identify specific information needs
   - Rerank research needs by impact and actionability

3. **Literature Search**:

   - For each research need, conduct targeted web searches
   - Use RAG to extract and synthesize relevant information
   - Track cited documents for attribution

4. **Report Generation**:

   - Generate focused reports for each research need
   - Combine individual reports into a comprehensive final report
   - Include bibliography with source citations

5. **Output Rendering**:
   - Save results as JSON, Markdown, and HTML
   - Provide structured data for further analysis

### Key Features

- **Multi-perspective analysis**: Generates diverse personas to ensure comprehensive coverage
- **Actionable insights**: Prioritizes research needs that provide utility beyond surface-level information
- **Evidence-based**: All claims are backed by web sources with proper citations
- **Iterative refinement**: Uses DSPy for structured LM programming with potential for optimization

## 🧪 Testing

Presearcher includes a comprehensive test suite covering all pipeline components with **129+ test cases** across 7 test files.

### Quick Start

```bash
# Run all tests
pytest tests/

# Run with verbose output and coverage
python tests/run_tests.py --verbose --coverage

# Run specific component tests
python tests/run_tests.py --component rag
python tests/run_tests.py --component literature
python tests/run_tests.py --component report
```

### Test Coverage by Component

| Component | Test File | Coverage |
|-----------|-----------|----------|
| Purpose Generation | `test_purpose_generation.py` | 17 tests |
| Outline Generation | `test_outline_generation.py` | 12 tests |
| RAG Agent | `test_rag_agent.py` | 18 tests |
| Literature Search | `test_literature_search.py` | 16 tests |
| Report Generation | `test_report_generation.py` | 18 tests |
| Presearcher Agent | `test_presearcher_agent.py` | 14 tests |
| Data Classes | `test_dataclasses.py` | 34 tests |

### Test Documentation

- **`tests/README.md`**: Detailed testing documentation and guidelines
- **`TESTING_SUMMARY.md`**: Complete overview of pipeline steps and test coverage
- **`tests/run_tests.py`**: Convenient test runner script

For more details, see the [Testing Summary](TESTING_SUMMARY.md) and [Test Documentation](tests/README.md).

## 🔧 Development

### Code Quality

```bash
# Format code
uv run black src tests

# Lint
uv run ruff check src tests

# Type check
uv run mypy src
```

## 📚 Key Dependencies

- **dspy-ai** (3.0.3): Language model programming framework
- **crawl4ai** (0.7.4): Web scraping and content extraction
- **langchain-text-splitters** (0.3.11): Text chunking utilities
- **openai** (>=1.0.0): OpenAI/Azure OpenAI API client
- **tiktoken** (>=0.5.0): Token counting and text encoding

## 🎓 Background

This project is part of the Stanford CS224V (Conversational Virtual Assistants with Deep Learning) final project. It demonstrates how structured multi-agent systems can perform complex research tasks by breaking them down into manageable subtasks with clear objectives.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

[Add your license here]

## 👥 Authors

CS224V Final Project Team

## 🙏 Acknowledgments

- Stanford CS224V Course and Teaching Staff
- [DSPy](https://github.com/stanfordnlp/dspy) for the LM programming framework
- OpenAI for language model APIs
- Serper API for web search capabilities
