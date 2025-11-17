import asyncio
import json
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
from presearcher.hierarchical_presearcher import HierarchicalPresearcher
from utils.dataclass import (
    PresearcherAgentRequest,
    PresearcherAgentResponse,
)


async def main():
    mode = input("Mode [flat/hierarchical]? ").strip().lower() or "flat"
    presearcher_agent = await init_presearcher_agent()

    user_task = input("Enter research topic: ").strip()
    if not user_task:
        raise ValueError("Research topic required")

    if mode == "hierarchical":
        hierarchical_agent = HierarchicalPresearcher(
            ansatz_agent=presearcher_agent.ansatz_agent,
            literature_search_agent=presearcher_agent.literature_search_agent,
            strong_lm=presearcher_agent.strong_lm,
        )
        await hierarchical_agent.run(user_task, max_depth=2, max_children=2)
    else:
        response = await presearcher_agent.aforward(
            PresearcherAgentRequest(topic=user_task, max_retriever_calls=1)
        )
        Path("output").mkdir(exist_ok=True)
        with open("output/results.json", "w") as f:
            json.dump(response.to_dict(), f, indent=2)



if __name__ == "__main__":
    asyncio.run(main())
