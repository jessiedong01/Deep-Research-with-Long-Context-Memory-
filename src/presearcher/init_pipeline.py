import os

from dotenv import load_dotenv

from outline_generation import OutlineGenerationAgent
from presearcher.purpose_generation import PurposeGenerationAgent
from presearcher.presearcher import PresearcherAgent
from utils.encoder import Encoder
from utils.literature_search import LiteratureSearchAgent
from utils.lm import AzureOpenAIConfig, LanguageModelProvider, LanguageModelProviderConfig, init_lm
from utils.rag import RagAgent
from utils.retriever_agent.serper_rm import SerperRM

load_dotenv()

def init_outline_generation_agent() -> OutlineGenerationAgent:
    lm_config = LanguageModelProviderConfig(
        provider=LanguageModelProvider.LANGUAGE_MODEL_PROVIDER_AZURE_OPENAI,
        model_name=os.environ["AZURE_OPENAI_MODEL_NAME"],
        temperature=1.0,
        max_tokens=16000,
        azure_openai_config=AzureOpenAIConfig(
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_base=os.environ["AZURE_OPENAI_BASE"],
            api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        )
    )

    lm = init_lm(lm_config)

    outline_generation_agent = OutlineGenerationAgent(
        lm=lm
    )

    return outline_generation_agent

def init_purpose_generation_agent() -> PurposeGenerationAgent:
    lm_config = LanguageModelProviderConfig(
        provider=LanguageModelProvider.LANGUAGE_MODEL_PROVIDER_AZURE_OPENAI,
        model_name=os.environ["AZURE_OPENAI_MODEL_NAME"],
        temperature=1.0,
        max_tokens=16000,
        azure_openai_config=AzureOpenAIConfig(
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_base=os.environ["AZURE_OPENAI_BASE"],
            api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        )
    )

    lm = init_lm(lm_config)
    
    purpose_generation_agent = PurposeGenerationAgent(
        lm=lm
    )

    return purpose_generation_agent

def init_rag_agent() -> RagAgent:
    # Step 1: Initialize the Serper Retriever for Google Search

    encoder = Encoder(
        model_name=os.environ["AZURE_EMBEDDING_MODEL_NAME"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_base=os.environ["AZURE_OPENAI_BASE"],
        api_version=os.environ["AZURE_OPENAI_API_VERSION"],
    )

    serper_retriever = SerperRM(api_key=os.environ["SERPER_API_KEY"], encoder=encoder)

    # Step 2: Initialize the RAG Agent for information retrieval
    rag_lm_config = LanguageModelProviderConfig(
        provider=LanguageModelProvider.LANGUAGE_MODEL_PROVIDER_AZURE_OPENAI,
        model_name="gpt-4.1-mini",
        temperature=1.0,
        max_tokens=10000,
        azure_openai_config=AzureOpenAIConfig(
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_base=os.environ["AZURE_OPENAI_BASE"],
            api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        )
    )

    rag_lm = init_lm(rag_lm_config)

    # Step 3: Initialize the RAG Agent, passing in the retriever and the RAG Language Model
    rag_agent = RagAgent(
        retriever=serper_retriever,
        rag_lm=rag_lm,
    )

    return rag_agent

def init_report_generation_agent(literature_search_agent: LiteratureSearchAgent):
    """Initialize the Report Generation Agent."""
    from presearcher.report_generation import ReportGenerationAgent
    
    # Initialize report generation LM
    report_lm_config = LanguageModelProviderConfig(
        provider=LanguageModelProvider.LANGUAGE_MODEL_PROVIDER_AZURE_OPENAI,
        model_name=os.environ.get("AZURE_OPENAI_MODEL_NAME", "gpt-4.1"),
        temperature=1.0,
        max_tokens=16000,
        azure_openai_config=AzureOpenAIConfig(
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_base=os.environ["AZURE_OPENAI_BASE"],
            api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        )
    )
    
    report_lm = init_lm(report_lm_config)
    
    report_generation_agent = ReportGenerationAgent(
        literature_search_agent=literature_search_agent,
        lm=report_lm
    )
    
    return report_generation_agent

def init_presearcher_agent():
    """Initialize the Presearcher Agent with all sub-agents."""
    from presearcher.report_generation import ReportCombiner
    
    # Initialize all sub-agents
    rag_agent = init_rag_agent()
    purpose_generation_agent = init_purpose_generation_agent()
    outline_generation_agent = init_outline_generation_agent()
    
    # Initialize the Literature Search Agent for planning and answer synthesis
    literature_search_planning_lm = init_lm(
        LanguageModelProviderConfig(
            provider=LanguageModelProvider.LANGUAGE_MODEL_PROVIDER_AZURE_OPENAI,
            model_name="gpt-4.1",
            temperature=1.0,
            max_tokens=10000,
            azure_openai_config=AzureOpenAIConfig(
                api_key=os.environ["AZURE_OPENAI_API_KEY"],
                api_base=os.environ["AZURE_OPENAI_BASE"],
                api_version=os.environ["AZURE_OPENAI_API_VERSION"],
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
                api_key=os.environ["AZURE_OPENAI_API_KEY"],
                api_base=os.environ["AZURE_OPENAI_BASE"],
                api_version=os.environ["AZURE_OPENAI_API_VERSION"],
            ),
        )
    )

    literature_search_agent = LiteratureSearchAgent(
        rag_agent=rag_agent,
        literature_search_lm=literature_search_planning_lm,
        answer_synthesis_lm=answer_synthesis_lm,
    )
    
    # Initialize report generation agent
    report_generation_agent = init_report_generation_agent(literature_search_agent)

    presearcher_agent = PresearcherAgent(
        purpose_generation_agent=purpose_generation_agent,
        outline_generation_agent=outline_generation_agent,
        literature_search_agent=literature_search_agent,
        report_generation_agent=report_generation_agent,
        lm=answer_synthesis_lm,
    )

    return presearcher_agent
