# 224v-final-project

Deep Research Pipeline for CS224V Final Project - An advanced research assistant powered by retrieval-augmented generation and language models.

## 🚀 Features

- **Literature Search Agent**: Intelligent search and retrieval of academic papers and research documents
- **RAG (Retrieval-Augmented Generation)**: Context-aware response generation using retrieved documents
- **Web Scraping**: Automated content extraction from web sources using Crawl4AI
- **Multi-Provider LM Support**: Flexible language model integration (Azure OpenAI, OpenAI)
- **Document Embeddings**: High-quality semantic embeddings using OpenAI's text-embedding-3-large
- **Internet Retrieval**: Search and retrieve relevant information from the web using Serper API

## 📋 Prerequisites

- Python 3.13 or higher
- [uv](https://github.com/astral-sh/uv) package manager (recommended) or pip
- API keys for:
  - Azure OpenAI (or OpenAI)
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
# Clone the repository
git clone https://github.com/your-username/224v-final-project.git
cd 224v-final-project

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

## ⚙️ Configuration

Create a `.env` file in the project root with your API credentials:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_BASE=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-01

# Serper API Key (for web search)
SERPER_API_KEY=your_serper_api_key
```

## 🚦 Usage

### Running the Pipeline

```bash
# Using uv
uv run python -m src.presearcher.main

# Using standard Python
python -m src.presearcher.main
```

### Example Code

```python
import asyncio
from src.encoder import Encoder
from src.retriever_agent.serper_rm import SerperRM
from src.rag import RagAgent

async def main():
    # Initialize encoder
    encoder = Encoder(
        model_name="text-embedding-3-large",
        api_key="your_api_key",
        api_base="your_api_base",
        api_version="2024-02-01"
    )

    # Initialize retriever
    retriever = SerperRM(
        api_key="your_serper_api_key",
        encoder=encoder
    )

    # Retrieve documents
    documents = await retriever.aretrieve("your search query")

    # Use documents with RAG agent
    # ... your implementation

if __name__ == "__main__":
    asyncio.run(main())
```

## 📁 Project Structure

```
224v-final-project/
├── src/
│   ├── __init__.py
│   ├── pipeline/
│   │   ├── __init__.py
│   │   └── main.py              # Main pipeline execution
│   └── utils/
│       ├── __init__.py
│       ├── dataclass.py          # Data structures and models
│       ├── encoder.py            # Text embedding utilities
│       ├── literature_search.py  # Literature search agent
│       ├── lm.py                 # Language model initialization
│       ├── rag.py                # RAG agent implementation
│       ├── render_output.py      # Output rendering utilities
│       ├── utils.py              # General utilities
│       └── retriever_agent/
│           ├── __init__.py
│           ├── internet_retriever.py
│           ├── retriever.py
│           ├── serper_rm.py      # Serper API integration
│           └── web_scraper_agent.py
├── tests/
│   ├── __init__.py
│   └── test_example.py           # Example tests
├── .gitignore
├── pyproject.toml                # Project configuration
├── uv.lock                       # Dependency lock file
└── README.md
```

## 🧪 Testing

```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/test_example.py
```

## 🔧 Development

### Code Formatting

```bash
# Format code with Black
uv run black src tests

# Lint with Ruff
uv run ruff check src tests

# Type check with mypy
uv run mypy src
```

### Pre-commit Setup (Optional)

Install development dependencies and set up pre-commit hooks:

```bash
uv sync --extra dev
```

## 📚 Key Dependencies

- **dspy-ai** (3.0.3): Framework for programming with language models
- **crawl4ai** (0.7.4): Web scraping and content extraction
- **langchain-text-splitters** (0.3.11): Text chunking utilities
- **openai** (>=1.0.0): OpenAI API client
- **tiktoken** (>=0.5.0): Token counting and encoding

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

[Add your license here]

## 👥 Authors

CS224V Final Project Team

## 🙏 Acknowledgments

- Stanford CS224V Course
- OpenAI for language model APIs
- Serper API for web search capabilities
