import os

from dotenv import load_dotenv

from presearcher.ansatz import AnsatzAgent
from presearcher.presearcher import PresearcherAgent
from utils.encoder import Encoder
from utils.literature_search import LiteratureSearchAgent
from utils.lm import AzureOpenAIConfig, LanguageModelProvider, LanguageModelProviderConfig, init_lm
from utils.rag import RagAgent
from utils.retriever_agent.serper_rm import SerperRM

load_dotenv()

async def init_presearcher_agent():
    # Step 1: Initialize the Serper Retriever for Google Search

    # The serper retriever needs an embedding model to do similarity search
    encoder = Encoder(
        model_name="text-embedding-3-large",
        api_key=os.getenv("AZURE_OPENAI_API_KEY") or "",
        api_base=os.getenv("AZURE_OPENAI_BASE") or "",
        api_version=os.getenv("AZURE_OPENAI_API_VERSION") or "",
    )

    serper_retriever = SerperRM(api_key=os.getenv("SERPER_API_KEY") or "", encoder=encoder)

    # Step 2: Initialize the RAG Agent for information retrieval
    rag_lm_config = LanguageModelProviderConfig(
        provider=LanguageModelProvider.LANGUAGE_MODEL_PROVIDER_AZURE_OPENAI,
        model_name="gpt-4.1",
        temperature=1.0,
        max_tokens=10000,
        azure_openai_config=AzureOpenAIConfig(
            api_key=os.getenv("AZURE_OPENAI_API_KEY") or "",
            api_base=os.getenv("AZURE_OPENAI_BASE") or "",
            api_version=os.getenv("AZURE_OPENAI_API_VERSION") or "",
        )
    )

    rag_lm = init_lm(rag_lm_config)

    # Step 3: Initialize the RAG Agent, passing in the retriever and the RAG Language Model
    rag = RagAgent(
        retriever=serper_retriever,
        rag_lm=rag_lm,
    )

    # Step 4: Initialize the Literature Search Agent for planning and answer synthesis
    literature_search_planning_lm = init_lm(
        LanguageModelProviderConfig(
            provider=LanguageModelProvider.LANGUAGE_MODEL_PROVIDER_AZURE_OPENAI,
            model_name="gpt-4.1",
            temperature=1.0,
            max_tokens=10000,
            azure_openai_config=AzureOpenAIConfig(
                api_key=os.getenv("AZURE_OPENAI_API_KEY") or "",
                api_base=os.getenv("AZURE_OPENAI_BASE") or "",
                api_version=os.getenv("AZURE_OPENAI_API_VERSION") or "",
            ),
        )
    )

    answer_synthesis_lm = init_lm(
        LanguageModelProviderConfig(
            provider=LanguageModelProvider.LANGUAGE_MODEL_PROVIDER_AZURE_OPENAI,
            model_name="gpt-5-chat",
            temperature=1.0,
            max_tokens=16000,
            azure_openai_config=AzureOpenAIConfig(
                api_key=os.getenv("AZURE_OPENAI_API_KEY") or "",
                api_base=os.getenv("AZURE_OPENAI_BASE") or "",
                api_version=os.getenv("AZURE_OPENAI_API_VERSION") or "",
            ),
        )
    )

    literature_search_agent = LiteratureSearchAgent(
        rag_agent=rag,
        literature_search_lm=literature_search_planning_lm,
        answer_synthesis_lm=answer_synthesis_lm,
    )

    weak_lm = init_lm(
        LanguageModelProviderConfig(
            provider=LanguageModelProvider.LANGUAGE_MODEL_PROVIDER_AZURE_OPENAI,
            model_name="gpt-4.1",
            temperature=1.0,
            max_tokens=10000,
            azure_openai_config=AzureOpenAIConfig(
                api_key=os.getenv("AZURE_OPENAI_API_KEY") or "",
                api_base=os.getenv("AZURE_OPENAI_BASE") or "",
                api_version=os.getenv("AZURE_OPENAI_API_VERSION") or "",
            ),
        )
    )
    strong_lm = init_lm(
        LanguageModelProviderConfig(
            provider=LanguageModelProvider.LANGUAGE_MODEL_PROVIDER_AZURE_OPENAI,
            model_name="gpt-4.1",
            temperature=1.0,
            max_tokens=16000,
            azure_openai_config=AzureOpenAIConfig(
                api_key=os.getenv("AZURE_OPENAI_API_KEY") or "",
                api_base=os.getenv("AZURE_OPENAI_BASE") or "",
                api_version=os.getenv("AZURE_OPENAI_API_VERSION") or "",
            ),
        )
    )

    ansatz_agent = AnsatzAgent(
        weak_lm=weak_lm,
        strong_lm=strong_lm,
        literature_search_agent=literature_search_agent,
    )

    presearcher_agent = PresearcherAgent(
        literature_search_agent=literature_search_agent,
        ansatz_agent=ansatz_agent,
        strong_lm=strong_lm,
    )

    return presearcher_agent
