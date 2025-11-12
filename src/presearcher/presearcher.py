import dspy

from presearcher.ansatz import AnsatzAgent, IsAnswerableResearchNeed
from presearcher.report_generation import ReportCombiner, ReportGenerationAgent
from utils.dataclass import (
    LiteratureSearchAgentRequest,
    PresearcherAgentRequest,
    PresearcherAgentResponse,
    ReportGenerationRequest,
)
from utils.literature_search import LiteratureSearchAgent


class PresearcherAgent(dspy.Module):
    """Enhanced deep research pipeline that include deeper preplanning."""

    def __init__(self, ansatz_agent: AnsatzAgent, literature_search_agent: LiteratureSearchAgent, strong_lm: dspy.LM):
        self.ansatz_agent = ansatz_agent
        self.literature_search_agent = literature_search_agent
        self.strong_lm = strong_lm
        self.is_answerable = dspy.Predict(IsAnswerableResearchNeed)
        self.report_generation_agent = ReportGenerationAgent(literature_search_agent, strong_lm)
        self.report_combiner = dspy.Predict(ReportCombiner)

    async def aforward(self, request: PresearcherAgentRequest) -> PresearcherAgentResponse:
        # Step 1: Ansatz Agent hypothesizes on the needed information to answer the question effectively
        ansatz_agent_response = await self.ansatz_agent.aforward(request.topic)

        # Step 2: Conduct a literature search and generate a report for each research need
        report_generation_results_list = []

        for research_need in ansatz_agent_response:
            literature_search_request = LiteratureSearchAgentRequest(
                topic=research_need,
                max_retriever_calls=1,
                guideline="Conduct a survey. Stop when information gain is low or hit the budget",
                with_synthesis=False
            )
            literature_search_results = await self.literature_search_agent.aforward(
                literature_search_request=literature_search_request,
            )

            # is_answerable_result = await self.is_answerable.aforward(
            #     research_need=research_need,
            #     literature_search=literature_search_results,
            #     lm=self.strong_lm
            # )

            # literature_search_results_list.append({
            #     "research_need": research_need,
            #     "literature_search": literature_search_results,
            #     # "is_answerable": is_answerable_result.is_answerable
            # })

            report_generation_request = ReportGenerationRequest(
                topic=research_need,
                literature_search=literature_search_results,
                is_answerable=True, # TODO: add is_answerable logic
            )

            report_generation_response = await self.report_generation_agent.aforward(report_generation_request)

            report_generation_results_list.append({
                "research_need": research_need,
                "report_generation": report_generation_response,
                "cited_documents": report_generation_response.cited_documents
            })

        # Step 3: Combine the report generation results into a single report
        report_combiner_response = await self.report_combiner.aforward(
            report_generation_results_list=report_generation_results_list,
            lm=self.strong_lm
        )

        # Step 4: Return the final report
        final_report = report_combiner_response.final_report
        # final_cited_documents = report_combiner_response.cited_documents

        return PresearcherAgentResponse(
            topic=request.topic,
            guideline=request.guideline,
            writeup=final_report,
            cited_documents=[],
        )
