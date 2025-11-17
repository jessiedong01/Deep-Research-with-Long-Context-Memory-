import dspy

class IsAnswerableResearchNeed(dspy.Signature):
    """Decide whether a research need is **fully and convincingly answerable** using only the provided
    literature search results.

    You must be **extremely conservative** in saying that the research need is answerable.
    - Treat the default as **not answerable (False)**.
    - Only return **True** if the literature search results together form an *exceptionally strong,
      specific, and actionable* answer to the research need.

    The research need is answerable (True) **only if all** of the following are clearly satisfied:
    1. The core question and all of its key sub-parts are **directly and explicitly addressed**
       in the literature search results (not just tangentially related).
    2. The results provide **clear, concrete, and actionable** guidance (e.g., specific methods,
       procedures, parameters, interventions, or recommendations) that a domain expert could
       realistically implement without needing substantial additional research.
    3. There are **no major gaps, ambiguities, or unresolved uncertainties** in the answer with
       respect to what the research need is asking.

    In **any** of the following situations, you **must return False**:
    - The literature only partially addresses the research need, or only at a high level.
    - Evidence is weak, speculative, outdated, or clearly insufficient to act on.
    - Important aspects of the research need are missing, unclear, or only indirectly discussed.
    - The results mainly suggest that more research is needed, or highlight open questions.

    If you are unsure, if the answer feels borderline, or if the evidence is anything less than
    clearly strong, specific, and actionable, you **must output False**.
    """
    research_need: str = dspy.InputField(
        description="A research need to determine if it is answerable using only the information in the literature search results."
    )

    literature_search: str = dspy.InputField(
        description="The results of a literature search on the research need."
    )

    is_answerable: bool = dspy.OutputField(
        description="Whether the research need is answerable using only the information in the literature search results."
    )