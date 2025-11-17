from typing import Any
import dspy

from utils.logger import get_logger

class OutlineGenerationResponse:
    markdown: str
    parsed_outline: dict[str, Any]

class OutlineGenerationAgent:
    def __init__(self, lm: dspy.LM):
        self.lm = lm
        self.logger = get_logger()

    async def aforward(self, question: str, purposes: list[str]) -> OutlineGenerationResponse:
        """Generate an outline for a given research question.
        """
        self.logger.debug(f"Generating outline for: {question}")
        self.logger.debug(f"Based on {len(purposes)} research purposes")

        response = await self.lm.aforward(question)
        # Extract text from ModelResponse object
        outline: str = response.outputs[0] if hasattr(response, 'outputs') else str(response)
        parsed_outline: dict[str, Any] =  {}
        
        self.logger.debug(f"Generated outline with length: {len(outline)} characters")
        
        return {
            "markdown": outline,
            "parsed_outline": parsed_outline,
        }