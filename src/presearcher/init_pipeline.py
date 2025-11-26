import os

from dotenv import load_dotenv

from presearcher.presearcher import PresearcherAgent
from utils.encoder import Encoder
from utils.literature_search import LiteratureSearchAgent
from utils.lm import AzureOpenAIConfig, LanguageModelProvider, LanguageModelProviderConfig, init_lm
from utils.rag import RagAgent
from utils.retriever_agent.serper_rm import SerperRM

load_dotenv()


def _get_temperature(env_var: str, default: float = 1.0) -> float:
    """Get temperature from environment variable with a default.
    
    OpenAI reasoning models (o1, gpt-5, etc.) require temperature=1.0.
    For other models, this allows customization via environment variables.
    
    Args:
        env_var: The environment variable name to check
        default: Default temperature if env var not set (default: 1.0)
    
    Returns:
        Temperature value as a float
    """
    value = os.environ.get(env_var)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_max_tokens(env_var: str, default: int) -> int:
    """Get max_tokens from environment variable with a default.
    
    OpenAI reasoning models (o1, gpt-5, etc.) require max_tokens >= 16000.
    """
    value = os.environ.get(env_var)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


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
        model_name=os.environ.get("AZURE_RAG_MODEL_NAME", "gpt-4.1-mini"),
        temperature=_get_temperature("RAG_LM_TEMPERATURE", 1.0),
        max_tokens=_get_max_tokens("RAG_LM_MAX_TOKENS", 10000),
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
        temperature=_get_temperature("REPORT_LM_TEMPERATURE", 1.0),
        max_tokens=_get_max_tokens("REPORT_LM_MAX_TOKENS", 16000),
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
    """Initialize the Presearcher Agent with the new three-phase architecture."""
    
    # Initialize the RAG agent for literature search
    rag_agent = init_rag_agent()
    
    # Initialize the Literature Search Agent for planning (completeness checking, question generation)
    # Uses a faster/cheaper model since these are simpler classification and generation tasks
    literature_search_planning_lm = init_lm(
        LanguageModelProviderConfig(
            provider=LanguageModelProvider.LANGUAGE_MODEL_PROVIDER_AZURE_OPENAI,
            model_name=os.environ.get("AZURE_PLANNING_MODEL_NAME", "gpt-4.1-mini"),
            temperature=_get_temperature("PLANNING_LM_TEMPERATURE", 1.0),
            max_tokens=_get_max_tokens("PLANNING_LM_MAX_TOKENS", 10000),
            azure_openai_config=AzureOpenAIConfig(
                api_key=os.environ["AZURE_OPENAI_API_KEY"],
                api_base=os.environ["AZURE_OPENAI_BASE"],
                api_version=os.environ["AZURE_OPENAI_API_VERSION"],
            ),
        )
    )

    # Note: Synthesis LM often uses reasoning models (gpt-5, o1, etc.) which
    # require temperature=1.0. Use SYNTHESIS_LM_TEMPERATURE only for non-reasoning models.
    answer_synthesis_lm = init_lm(
        LanguageModelProviderConfig(
            provider=LanguageModelProvider.LANGUAGE_MODEL_PROVIDER_AZURE_OPENAI,
            model_name=os.environ.get("AZURE_SYNTHESIS_MODEL_NAME", "gpt-5-chat"),
            temperature=_get_temperature("SYNTHESIS_LM_TEMPERATURE", 1.0),
            max_tokens=_get_max_tokens("SYNTHESIS_LM_MAX_TOKENS", 16000),
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
    
    # Initialize PresearcherAgent with the new simplified architecture
    # It only needs the literature search agent and LM - it creates its own
    # DAGGenerationAgent, DAGProcessor, and FinalReportGenerator internally
    presearcher_agent = PresearcherAgent(
        literature_search_agent=literature_search_agent,
        lm=answer_synthesis_lm,
    )

    return presearcher_agent
