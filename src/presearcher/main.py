import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to Python path to enable absolute imports
# This ensures presearcher and utils packages can be imported
src_path = Path(__file__).resolve().parent.parent
src_path_str = str(src_path)
if src_path_str not in sys.path:
    sys.path.insert(0, src_path_str)

# Now we can use absolute imports
from presearcher.init_pipeline import init_presearcher_agent
from utils.dataclass import (
    PresearcherAgentRequest,
    PresearcherAgentResponse,
)
from utils.logger import init_logger


async def main():
    # Initialize logging at the start
    logger = init_logger(name="presearcher", log_dir="output/logs")
    logger.info("=" * 80)
    logger.info("Presearcher Pipeline Starting")
    logger.info("=" * 80)
    
    # Initialize the presearcher agent
    logger.info("Initializing presearcher agent...")
    presearcher_agent = init_presearcher_agent()
    logger.info("Presearcher agent initialized successfully")

    # Prompt the user for a research task to use as the query/topic
    user_task = input("Please enter your research task or topic: ").strip()
    if not user_task:
        raise ValueError("Research task or topic is required")
    
    logger.info(f"User research task: {user_task}")
    
    # Configuration
    max_retriever_calls = 1
    logger.info(f"Pipeline configuration: max_retriever_calls={max_retriever_calls}")

    # Run the presearcher pipeline
    presearcher_response: PresearcherAgentResponse = await presearcher_agent.aforward(
        PresearcherAgentRequest(topic=user_task, max_retriever_calls=max_retriever_calls)
    )

    # Save results
    os.makedirs("output", exist_ok=True)
    output_file = "output/results.json"
    
    logger.info(f"Saving final results to {output_file}")
    with open(output_file, "w") as f:
        json.dump(presearcher_response.to_dict(), f, indent=2)
    
    logger.info("=" * 80)
    logger.info(f"Pipeline completed successfully! Results saved to {output_file}")
    logger.info(f"Intermediate results and logs saved to output/logs/")
    logger.info("=" * 80)



if __name__ == "__main__":
    asyncio.run(main())
