
import dspy

from utils.dataclass import (
    RagResponse,
    ReportGenerationRequest,
    ReportGenerationResponse,
    RetrievedDocument,
)
from utils.literature_search import LiteratureSearchAgent
from utils.logger import get_logger


class KeyInsightIdentifier(dspy.Signature):
    """
    You are a key insights identifier. You will be given a question, the context surrounding that question, and the answer a RAG pipeline gave to that question.
    Your job is to analyze that given question, context, and answer, and generate a one sentence 'key insight' representing the most important information
    Learned from the RAG response.
    """
    question: str = dspy.InputField(
        desc="The question that was asked"
    )
    question_context: str = dspy.InputField(
        desc="The context of the question"
    )
    answer: str = dspy.InputField(
        desc="The answer to the question aggregating information from external sources"
    )
    key_insight: str = dspy.OutputField(
        desc="One sentence key insight."
    )

class FinalWritingGuidelineProposal(dspy.Signature):
    """
    You are an experienced Wikipedia writer and researcher. Your research partner has done a ton of research,
    gathered lots of interesting and relevant information, and synthesized it into key insights and claims. Now,
    write a guideline for your partner with bullet points outling the key points that should be included in the report.
    """
    key_insights: list[str] = dspy.InputField(
        desc="A list of key insights generated from a wealth of research done on the topic"
    )
    report_thesis: str = dspy.OutputField(
        desc="Exactly one headline-style line (8-14 words). This headline is the thesis of your report.")
    writing_guideline: str = dspy.OutputField(
        desc="The proposed writing guideline for the final report in bullet point format. The guideline should outline the key points that should be included in the report." # TODO: add/improve instructions
    )

def _normalize_rag_response_citation_indices(rag_responses: list[RagResponse]) -> tuple[list[str], list[RetrievedDocument]]:
        """
        Normalize citation indices across multiple RAG (retrieval-augmented generation) responses.

        Each `RagResponse` contains:
        - `answer`: a string with inline citations like [1], [2], ...
        - `cited_documents`: the list of documents those citations refer to

        Problem:
        Citation indices restart at [1] for every response, but when combining answers,
        we want all citations to point to a single global list of retrieved documents.

        What this function does:
        1. Iterates over all RAG responses in order.
        2. Shifts the local citation indices in each answer so that they correctly map
            into the combined list of all retrieved documents.
            - For example, if the first response cited 3 docs ([1], [2], [3]),
            then the second response’s citations start at [4], not [1].
        3. Prefixes each updated answer with its corresponding sub-question for clarity.
        4. Returns:
            - A list of normalized answers (with corrected citation indices).
            - The flattened list of all retrieved documents in the proper order.

        Example:
            Input (two RAG responses):
                R1: "Paris is in France [1].", docs=[docA]
                R2: "Berlin is in Germany [1].", docs=[docB]

            Output:
                answers = [
                "Sub-question: ...\nAnswer: Paris is in France [1].",
                "Sub-question: ...\nAnswer: Berlin is in Germany [2]."
                ]
                documents = [docA, docB]
        """
        all_documents: list[RetrievedDocument] = []
        all_updated_answers: list[str] = []
        for idx, rag_response in enumerate(rag_responses):
            citation_offset = len(all_documents)
            updated_answer = rag_response.answer
            for i in range(len(rag_response.cited_documents)):
                updated_answer = updated_answer.replace(f"[{i+1}]", f"[tmp_{citation_offset+i+1}]")
            for i in range(len(rag_response.cited_documents)):
                updated_answer = updated_answer.replace(f"[tmp_{citation_offset+i+1}]", f"[{citation_offset+i+1}]")

            all_updated_answers.append(
                f"Sub-question: {rag_response.question}\nAnswer: {updated_answer}\n")
            all_documents.extend(rag_response.cited_documents)
        return all_updated_answers, all_documents


class FinalReportSynthesizer(dspy.Signature):
    """
    You are an investigative journalist composing a report with given thesis, guideline, and useful information from previous literature search.

    CONTENT INTEGRATION RULES:
    - Merge all relevant sub-question answers into a logically coherent narrative
    - Create clear thematic sections with smooth transitions between topics. Use #, ##, ###, etc. to create title of sections and sub-sections.
    - Eliminate redundancy while preserving all unique factual content
    - Exclude sub-questions/answers that don't contribute meaningfully to the survey topic
    - Maintain completeness - no loss of relevant information from source material
    - No title, conclusion, summary, or reference at the end of the answer.

    CITATION PRESERVATION:
    - Preserve ALL original citations exactly as provided - no format modifications
    - Make sure each statement that cites a document actually keeps the [Document Number] inline citation

    CONTENT CONSTRAINTS:
    Constrain the content to provided information and do not add any external knowledge and do not speculate.
    """
    report_thesis: str = dspy.InputField(
        desc="The proposed thesis for the investigative journalism report"
    )
    writing_guideline: str = dspy.InputField(
        desc="The proposed writing guideline for the final report in bullet point format"
    )
    gathered_information: str = dspy.InputField(
        description="""Complete set of sub-question answers with their inline citations from previous research steps. 
        Format typically includes:
        - Sub-question: [question text]
        - Answer: [detailed response with inline citations [1], [2], etc.]
        - (Repeated for multiple sub-questions)"""
    )

    # TODO: optionally add other input fields

    quick_answer: str = dspy.OutputField(
        desc="A 1-2 sentence direct answer to the research question. If the question asks for a recommendation, provide a clear recommendation."
    )
    executive_summary: str = dspy.OutputField(
        desc="An expertly crafted summary (3-5 sentences) that clearly articulates the most important points and key findings of the report."
    )
    final_report: str = dspy.OutputField(
        desc="The final investigative report in markdown format"
    )

class ReportGenerationAgent(dspy.Module):
    def __init__(self, literature_search_agent: LiteratureSearchAgent, lm: dspy.LM):
        self.literature_search_agent = literature_search_agent
        self.lm = lm
        self.key_insight_identifier = dspy.Predict(KeyInsightIdentifier)
        self.final_writing_guideline_proposal = dspy.Predict(FinalWritingGuidelineProposal)
        self.final_report_synthesizer = dspy.Predict(FinalReportSynthesizer)
        self.logger = get_logger()

    async def aforward(self, request: ReportGenerationRequest) -> ReportGenerationResponse:
        self.logger.debug(f"Generating report for topic: {request.topic}")
        self.logger.debug(f"Processing {len(request.literature_search.rag_responses)} RAG responses")
        
        for rag_response in request.literature_search.rag_responses:
            key_insight_result = await self.key_insight_identifier.aforward(
                question=rag_response.question,
                question_context=rag_response.question_context,
                answer=rag_response.answer,
                lm=self.lm
            )
            rag_response.key_insight = key_insight_result.key_insight
        
        self.logger.debug(f"Extracted {len(request.literature_search.rag_responses)} key insights")

        final_writing_guideline_proposal_response = (await self.final_writing_guideline_proposal.aforward(
        key_insights=[f"Key Insight #{idx}: {response.key_insight}" for idx,response in enumerate(request.literature_search.rag_responses)],
        lm=self.lm
    ))

        final_writing_thesis = final_writing_guideline_proposal_response.report_thesis
        final_writing_guideline = final_writing_guideline_proposal_response.writing_guideline
        
        self.logger.debug(f"Report thesis: {final_writing_thesis}")

        all_updated_answers, all_documents = _normalize_rag_response_citation_indices(request.literature_search.rag_responses)
        
        self.logger.debug(f"Normalized citations for {len(all_documents)} documents")

        synthesizer_response = await self.final_report_synthesizer.aforward(
            report_thesis=final_writing_thesis,
            writing_guideline=final_writing_guideline,
            gathered_information=all_updated_answers,
            lm=self.lm,
            report_style="Comprehensive, highly accurate, and exhaustive; include every relevant detail and ensure no important information is omitted."
        )
        
        # Extract the three components from the synthesizer response
        quick_answer = synthesizer_response.quick_answer
        executive_summary = synthesizer_response.executive_summary
        final_report = synthesizer_response.final_report

        # Format the final report with Quick Answer and Executive Summary at the beginning
        formatted_report = f"## Quick Answer\n\n{quick_answer}\n\n## Executive Summary\n\n{executive_summary}\n\n{final_report}"
        
        # Add bibliography at the end
        final_report_with_bibliography = formatted_report + "\n\n## Bibliography\n" + "\n".join([f"[{idx}]. {document.url}" for idx,document in enumerate(all_documents)])
        
        self.logger.debug(f"Generated report with {len(final_report_with_bibliography)} characters, citing {len(all_documents)} documents")

        return ReportGenerationResponse(
            report=final_report_with_bibliography,
            cited_documents=all_documents
        )

class ReportCombiner(dspy.Signature):
    """
    You are a report combiner. You will be given a list of report generation responses.
    Your job is to combine the reports into a single report.
    """
    report_generation_results_list: list[ReportGenerationResponse] = dspy.InputField(
        desc="A list of report generation responses"
    )
    final_report: str = dspy.OutputField(
        desc="The final report in markdown format"
    )
