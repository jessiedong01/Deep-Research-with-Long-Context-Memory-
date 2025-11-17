import asyncio
import json
from pathlib import Path
from datetime import datetime

from presearcher.ansatz import AnsatzAgent
from presearcher.report_generation import ReportGenerationAgent
from utils.dataclass import LiteratureSearchAgentRequest, ReportGenerationRequest
from utils.literature_search import LiteratureSearchAgent


class HierarchicalPresearcher:
    """Hierarchical version of the Presearcher that recursively builds a research tree."""

    def __init__(self, ansatz_agent: AnsatzAgent, literature_search_agent: LiteratureSearchAgent, strong_lm):
        self.ansatz_agent = ansatz_agent
        self.literature_search_agent = literature_search_agent
        self.report_generation_agent = ReportGenerationAgent(literature_search_agent, strong_lm)
        self.strong_lm = strong_lm
        self.output_path = Path("output/tree_state.json")
        self.tree = {"topic": None, "children": []}

    async def _save_tree(self):
        self.output_path.parent.mkdir(exist_ok=True)
        with open(self.output_path, "w") as f:
            json.dump(self.tree, f, indent=2)

    async def _expand_node(self, node, depth=0, max_depth=2, max_children=2):
        topic = node["topic"]
        print(f"{'  '*depth}Expanding node: {topic}")

        literature_search_request = LiteratureSearchAgentRequest(
            topic=topic,
            max_retriever_calls=1,
            guideline="Conduct a survey. Stop when information gain is low.",
            with_synthesis=False,
        )
        literature_search_results = await self.literature_search_agent.aforward(literature_search_request)

        report_request = ReportGenerationRequest(
            topic=topic,
            literature_search=literature_search_results,
            is_answerable=True,
        )
        report_response = await self.report_generation_agent.aforward(report_request)
        node["report"] = report_response.report
        node["timestamp"] = datetime.utcnow().isoformat()

        await self._save_tree()

        if depth < max_depth:
            sub_needs = await self.ansatz_agent.aforward(topic, k=max_children)
            node["children"] = [{"topic": s, "children": []} for s in sub_needs]

            for child in node["children"]:
                await self._expand_node(child, depth + 1, max_depth, max_children)
                await self._save_tree()

    async def run(self, root_topic: str, max_depth: int = 2, max_children: int = 2):
        print(f"Starting hierarchical presearch for: {root_topic}")
        self.tree["topic"] = root_topic
        await self._expand_node(self.tree, 0, max_depth, max_children)
        await self._save_tree()
        print("Hierarchical research complete.")
