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


async def main():
    presearcher_agent = await init_presearcher_agent()

    # Prompt the user for a research task to use as the query/topic
    user_task = input("Please enter your research task or topic: ").strip()
    if not user_task:
        raise ValueError("Research task or topic is required")

    presearcher_response: PresearcherAgentResponse = await presearcher_agent.aforward(
        PresearcherAgentRequest(topic=user_task, max_retriever_calls=1)
    )

    os.makedirs("output", exist_ok=True)

    with open("output/results.json", "w") as f:
        json.dump(presearcher_response.to_dict(), f, indent=2)



if __name__ == "__main__":
    asyncio.run(main())
