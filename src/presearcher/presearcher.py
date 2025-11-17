import dspy
from tqdm.asyncio import tqdm

from outline_generation import OutlineGenerationAgent
from presearcher.purpose_generation import PurposeGenerationAgent, IsAnswerableResearchNeed
from presearcher.report_generation import ReportCombiner, ReportGenerationAgent
from presearcher.subtask_generation import SubtaskGenerationAgent
from utils.dataclass import (
    LiteratureSearchAgentRequest,
    PresearcherAgentRequest,
    PresearcherAgentResponse,
    ReportGenerationRequest,
)
from utils.literature_search import LiteratureSearchAgent
from utils.logger import get_logger


class PresearcherAgent:
    """Enhanced deep research pipeline that include deeper preplanning."""

    def __init__(self,
     purpose_generation_agent: PurposeGenerationAgent,
     outline_generation_agent: OutlineGenerationAgent,
     literature_search_agent: LiteratureSearchAgent,
     report_generation_agent: ReportGenerationAgent,
     lm: dspy.LM):
        self.is_answerable = dspy.Predict(IsAnswerableResearchNeed)
        self.subtask_generation_agent = dspy.Predict(SubtaskGenerationAgent)
        self.purpose_generation_agent = purpose_generation_agent
        self.outline_generation_agent = outline_generation_agent
        self.literature_search_agent = literature_search_agent
        self.report_generation_agent = report_generation_agent
        self.lm = lm
        self.logger = get_logger()

    async def aforward(self, request: PresearcherAgentRequest) -> PresearcherAgentResponse:
        self.logger.info(f"Starting presearcher pipeline for topic: {request.topic}")
        
        # Step 1: Do a literature search on this task and see if it is answerable without decomposing it into research needs
        literature_search_request = LiteratureSearchAgentRequest(
            topic=request.topic,
            max_retriever_calls=1,
            guideline="Conduct a survey. Stop when information gain is low or hit the budget",
            with_synthesis=True
        )

        literature_search_results = await self.literature_search_agent.aforward(literature_search_request)

        self.logger.save_intermediate_result(
            "00_literature_search",
            {"topic": request.topic, "writeup": literature_search_results.writeup},
        )

        # Step 2: Decide if the research tasks is answerable using only the information in the literature search results
        is_answerable = await self.is_answerable.aforward(research_need=request.topic, writeup=literature_search_results.writeup, lm=self.lm)

        self.logger.save_intermediate_result(
            "01_is_answerable",
            {"topic": request.topic, "is_answerable": is_answerable},
        )

        if is_answerable:
            return PresearcherAgentResponse(
                topic=request.topic,
                guideline=request.guideline,
                writeup=literature_search_results.writeup,
                cited_documents=literature_search_results.cited_documents,
            )
    
        # Step 3: Decompose the research task into research needs
        subtask_generation_response = await self.subtask_generation_agent.aforward(research_task=request.topic, max_subtasks=10, lm=self.lm)


        self.logger.save_intermediate_result(
            "02_subtask_generation",
            {"topic": request.topic, "subtasks": subtask_generation_response.subtasks},
            {"subtasks_count": len(subtask_generation_response.subtasks)}
        )

        return PresearcherAgentResponse(
            topic=request.topic,
            guideline=request.guideline,
            writeup=literature_search_results.writeup,
            cited_documents=literature_search_results.cited_documents,
        )

        # Step 1: Purpose Generation Agent generates personas and their research needs
        self.logger.info("Step 1/5: Generating research purposes and needs...")
        purposes = await self.purpose_generation_agent.aforward(request.topic)
        self.logger.info(f"Generated {len(purposes)} research needs")
        self.logger.save_intermediate_result(
            "01_purpose_generation",
            {"topic": request.topic, "research_needs": purposes},
            {"count": len(purposes)}
        )

        # Step 2: Outline Generation Agent generates an outline for the report
        self.logger.info("Step 2/5: Generating report outline...")
        outline = await self.outline_generation_agent.aforward(request.topic, purposes)
        self.logger.info("Report outline generated")
        self.logger.save_intermediate_result(
            "02_outline_generation",
            {"topic": request.topic, "outline": outline},
            {"purposes_count": len(purposes)}
        )

        # Step 3: Conduct a literature search and generate a report for each research need
        self.logger.info(f"Step 3/5: Conducting literature search for {len(purposes)} research needs...")
        report_generation_results_list = []

        for research_need in tqdm(purposes, desc="Literature search", ncols=80):
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
        
        self.logger.info(f"Completed literature search for {len(purposes)} research needs")
        self.logger.save_intermediate_result(
            "03_literature_search",
            {
                "research_needs": purposes,
                "results_count": len(report_generation_results_list),
                "total_cited_documents": sum(len(r["cited_documents"]) for r in report_generation_results_list)
            },
            {"research_needs_count": len(purposes)}
        )

        # Step 4: Combine the report generation results into a single report
        self.logger.info("Step 4/5: Generating individual reports...")
        # Note: Reports were already generated in the loop above, this step is for logging
        self.logger.info(f"Generated {len(report_generation_results_list)} individual reports")
        self.logger.save_intermediate_result(
            "04_report_generation",
            [
                {
                    "research_need": r["research_need"],
                    "report": r["report_generation"].report,
                    "cited_documents_count": len(r["cited_documents"])
                }
                for r in report_generation_results_list
            ],
            {"reports_count": len(report_generation_results_list)}
        )
        
        # Step 5: Combine the report generation results into a single report
        self.logger.info("Step 5/5: Combining reports into final output...")
        report_combiner_predictor = dspy.Predict(ReportCombiner)
        report_combiner_response = await report_combiner_predictor.aforward(
            report_generation_results_list=report_generation_results_list,
            lm=self.lm
        )

        # Step 6: Return the final report
        final_report = report_combiner_response.final_report
        # final_cited_documents = report_combiner_response.cited_documents
        
        self.logger.info("Pipeline completed successfully!")
        self.logger.save_intermediate_result(
            "05_final_report",
            {
                "topic": request.topic,
                "final_report": final_report,
                "total_research_needs": len(purposes),
                "total_reports": len(report_generation_results_list)
            },
            {"report_length": len(final_report)}
        )

        return PresearcherAgentResponse(
            topic=request.topic,
            guideline=request.guideline,
            writeup=final_report,
            cited_documents=[],
        )
