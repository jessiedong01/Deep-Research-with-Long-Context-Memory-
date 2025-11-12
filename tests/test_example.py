"""Example test file to verify test setup is working."""

import json
import os
from typing import List

import pytest
from dotenv import load_dotenv

from utils.dataclass import (
    RetrievedDocument,
    LiteratureSearchAgentResponse,
    LiteratureSearchAgentRequest,
    RagResponse,
    RagRequest,
)
from utils.encoder import Encoder
from utils.literature_search import LiteratureSearchAgent
from utils.lm import (
    init_lm,
    LanguageModelProviderConfig,
    LanguageModelProvider,
    AzureOpenAIConfig,
)
from utils.retriever_agent.serper_rm import SerperRM
from utils.rag import RagAgent

load_dotenv()


def test_basic_import():
    """Test that the main package can be imported."""
    import src
    
    assert src.__version__ == "0.1.0"


@pytest.mark.skipif(
    not os.getenv("AZURE_OPENAI_API_KEY"),
    reason="Azure OpenAI API key not configured"
)
def test_lm():
    """Test language model initialization and basic inference."""
    test_lm_config = LanguageModelProviderConfig(
        provider=LanguageModelProvider.LANGUAGE_MODEL_PROVIDER_AZURE_OPENAI,
        model_name="gpt-4.1",
        temperature=0.0,
        max_tokens=10,
        azure_openai_config=AzureOpenAIConfig(
            api_key=os.getenv("AZURE_OPENAI_API_KEY") or "",
            api_base=os.getenv("AZURE_OPENAI_BASE") or "",
            api_version=os.getenv("AZURE_OPENAI_API_VERSION") or "",
        )
    )
    test_lm = init_lm(test_lm_config)
    result = test_lm("say 'Hello!' as is")[0]
    assert result is not None
    print(f"✅ LM response: {result}")


@pytest.mark.skipif(
    not os.getenv("AZURE_OPENAI_API_KEY") or not os.getenv("SERPER_API_KEY"),
    reason="API keys not configured"
)
async def test_encoder():
    """Test encoder functionality."""
    encoder = Encoder(
        model_name="text-embedding-3-large",
        api_key=os.getenv("AZURE_OPENAI_API_KEY") or "",
        api_base=os.getenv("AZURE_OPENAI_BASE") or "",
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    )
    embedding = await encoder.aencode(["hello"])
    
    # text-embedding-3-large produces 3072-dimensional embeddings
    assert len(embedding[0]) == 3072
    print("✅ Encoder is working")


@pytest.mark.skipif(
    not os.getenv("AZURE_OPENAI_API_KEY") or not os.getenv("SERPER_API_KEY"),
    reason="API keys not configured"
)
async def test_retriever():
    """Test retriever with Serper API."""
    encoder = Encoder(
        model_name="text-embedding-3-large",
        api_key=os.getenv("AZURE_OPENAI_API_KEY") or "",
        api_base=os.getenv("AZURE_OPENAI_BASE") or "",
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    )
    
    serper_retriever = SerperRM(
        api_key=os.getenv("SERPER_API_KEY") or "",
        encoder=encoder
    )
    retrieved_documents: List[RetrievedDocument] = await serper_retriever.aretrieve(
        "stanford new AI research"
    )
    
    assert len(retrieved_documents) > 0
    print("✅ Retriever is working")
    print("Example output:")
    print(json.dumps(retrieved_documents[0].to_dict(), indent=2))

