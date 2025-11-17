import dspy

from utils.literature_search import LiteratureSearchAgent
from utils.logger import get_logger


class PersonaGeneration(dspy.Signature):
    """When answering a complex research task, its important to understand the context and purpose behind that question and the person who is asking it.
    Given a research task, identify a wide variety of personas of people who would request such a report.
    For each persona, identify the higher level goal that solving this research task would solve.

    Here's an example:
    
    Research Task: "What is the current state of AI in the healthcare industry?"
    Personas:
    - A healthcare researcher interested in the latest advancements in AI for healthcare with the goal of determining whether AI is a safe and viable tool for healthcare right now.
    - A hedge fund manager conducting market research on the healthcare industry with the goal of determining whether to invest in the industry.
    - A healthcare policy maker conducting research to help inform legislation and regulations around the use of AI in healthcare.
    
    Be creative and think of personas that are not obvious.

    This signature helps understand the context and purpose behind a research request by identifying:
    - The type of researcher, organization, or stakeholder who would need this information
    - The broader research goals or objectives this report would support
    - How the findings would be integrated into their larger research agenda
    """

    research_task: str = dspy.InputField(
        description="The user's research task or query that describes what they want to investigate"
    )

    max_personas: int = dspy.InputField(
        description="The maximum number of personas to generate. Generate exactly this many personas, or fewer if you cannot think of enough diverse personas."
    )

    personas: list[str] = dspy.OutputField(
        description="""A list of personas and the higher level goal that solving the research task would solve. Each persona should be a unique person with a unique goal.
        1. Who would ask for a report like this? (Identify the type of researcher, organization, stakeholder, or field)
        2. What purpose would the findings of this paper serve in their greater research goals? (Explain how the findings would be used, what problems they would solve, and how they fit into broader research objectives)
        
        The list must contain at most max_personas items. Ensure a concise, detailed, and thoughtful analysis that considers the research context, potential applications, and strategic value of the findings."""
    )


class ResearchNeedsGeneration(dspy.Signature):
    """Answering complex research questions insightfully requires a lot of understanding and context. Once you have identified who the researcher is
    and the higher level goal that is the reason they are asking this research question, we need to figure out what specific information they hope to gain
    by reading this report.

    Given a research task and a description of a persona and their higher goal, generate a list of specific information this persona would hope to gain by reading this report.

    Here's an example:

    Research Task: "What is the current state of AI in the healthcare industry?"
    Persona: "A healthcare researcher interested in the latest advancements in AI for healthcare with the following higher level question: Is AI is a safe and viable tool for healthcare right now."
    Research Needs:
    - Are there any case studies or examples of AI being used in healthcare successfully?
    - Are there any case studies or examples of harm caused by AI being used in the healthcare industry?
    - What is the current regulatory landscape for AI in healthcare?
    - What potential risks and benefits of AI have experts in the healthcare industry identified?
    - What are the key barriers to the adoption of AI in healthcare?
    - What kinds of new AI technologies are companies building today that are relevant to the healthcare industry?

    Be creative and think of research needs that are not obvious.
    """

    research_task: str = dspy.InputField(
        description="The user's research task or query that describes what the given wants answered"
    )

    persona: str = dspy.InputField(
        description="A description of a persona and their higher level goal that is the reason they are asking this research question."
    )

    max_research_needs: int = dspy.InputField(
        description="The maximum number of research needs to generate. Generate exactly this many research needs, or fewer if you cannot think of enough diverse research needs."
    )

    research_needs: list[str] = dspy.OutputField(
        description="""A list of specific information this persona would hope to gain by reading this report. Each research need should be a unique question that is specific to the research task and the persona's goal.
        These research needs should be framed as information needed to answer the higher level question that lead the persona to ask this research question.
        The list must contain at most max_research_needs items."""
    )

class ResearchNeedsReranking(dspy.Signature):
    """Answering complex research questions insightfully requires a lot of understanding and context. Once we have identified the personas of researchers who would ask this question
    and the specific research needs they hope to gain from reading this report, we need to focus in the most insightful and generally applicable reasearch needs that would maximize the impact of this research for a variety of different researchers.
    
    Given a list of personas and their research needs, indentify a list of the most insightful and generally applicable research needs, focusing on needs that are actionable and provide the most utility to the researcher, rather than needs that provide only surface level or background information.
    
    Here's an example:
    
    Personas:
    - A healthcare researcher interested in the latest advancements in AI for healthcare with the goal of determining whether AI is a safe and viable tool for healthcare right now.
    - A hedge fund manager conducting market research on the healthcare industry with the goal of determining whether to invest in the industry.
    - A healthcare policy maker conducting research to help inform legislation and regulations around the use of AI in healthcare.
    
    Research Needs:
    Need 1: How is AI being used in healthcare today?
    Need 2: What kinds of new AI technologies are companies building today that are most likely to make an impact in the next 5 years in the healthcare industry?
    
    Between these two research needs, Need 2 is more insightful and generally applicable because many people would benefit from knowing about up and coming technology in this industry and there are actionble steps that can leverage this information such as investing in the companies or writing legislation in response to this kind of technology use. Question 1 is just a google search that isn't actionable or insightful.
    
    Return a list of research needs with amaximum of `max_research_needs` items.
    """

    research_needs: list[str] = dspy.InputField(
        description="A list of research needs to rerank."
    )

    max_research_needs: int = dspy.InputField(
        description="The maximum number of research needs to return. Return exactly this many research needs, or fewer if you cannot think of enough insightful and generally applicable research needs."
    )

    reranked_research_needs: list[str] = dspy.OutputField(
        description="A list of reranked research needs with a maximum of `max_research_needs` items."
    )

class IsAnswerableResearchNeed(dspy.Signature):
    """Given a research need and the results of a literature search on that topic, determine if it is answerable using only
    the information in the literature search results.
    """
    research_need: str = dspy.InputField(
        description="A research need to determine if it is answerable using only the information in the literature search results."
    )

    writeup: str = dspy.InputField(
        description="The results of a literature search on the research need."
    )

    is_answerable: bool = dspy.OutputField(
        description="Whether the research need is answerable using only the information in the literature search results."
    )

    reasoning: str = dspy.OutputField(
        description="The reasoning process for determining if the research need is answerable using only the information in the literature search results."
    )

class PurposeGenerationAgent:
    def __init__(self, lm: dspy.LM):
        self.lm = lm
        self.persona_generator = dspy.Predict(PersonaGeneration)
        self.research_needs_generator = dspy.Predict(ResearchNeedsGeneration)
        self.research_needs_reranker = dspy.Predict(ResearchNeedsReranking)
        self.logger = get_logger()

    async def aforward(self, question: str, k: int = 1) -> list[str]:
        """Generate personas and their research needs for a given research question.
        
        Args:
            question: The research task or query
            k: Maximum number of personas to generate and maximum research needs per persona (default: 5)
            
        Returns:
            A list of dictionaries, each containing a persona and their research needs
        """
        self.logger.debug(f"Generating personas and research needs for: {question}")
        
        # Step 1: Generate personas (limited to k)
        self.logger.debug(f"Generating up to {k} personas...")
        persona_result = await self.persona_generator.aforward(
            research_task=question,
            max_personas=k,
            lm=self.lm
        )
        personas = persona_result.personas

        # Step 2: For each persona, generate their research needs
        # Handle both str and list[str] returns for personas
        if isinstance(personas, str):
            persona_list = [personas]
        else:
            persona_list = list(personas)

        # Safety limit: ensure we don't process more than k personas
        persona_list = persona_list[:k]
        self.logger.debug(f"Generated {len(persona_list)} personas")

        reasearch_needs_list = []
        for persona in persona_list:
            research_needs_result = await self.research_needs_generator.aforward(
                research_task=question,
                persona=persona,
                max_research_needs=k,
                lm=self.lm
            )
            research_needs = research_needs_result.research_needs
            # Safety limit: ensure we don't return more than k research needs per persona
            if isinstance(research_needs, list):
                research_needs = research_needs[:k]
            reasearch_needs_list.append({
                "persona": persona,
                "research_needs": research_needs
            })
        
        self.logger.debug(f"Generated research needs for {len(persona_list)} personas")

        reasearch_needs_reranker_result = await self.research_needs_reranker.aforward(
            research_needs=reasearch_needs_list,
            max_research_needs=k,
            lm=self.lm
        )

        reranked_research_needs = reasearch_needs_reranker_result.reranked_research_needs
        self.logger.debug(f"Reranked to {len(reranked_research_needs)} final research needs")

        return reranked_research_needs
