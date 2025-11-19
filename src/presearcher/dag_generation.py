"""DAG Generation Module for Deep Research Pipeline.

This module generates a complete research DAG upfront before any actual research is conducted.
Each node in the DAG contains:
1. A research task/subtask
2. The expected output format for that task
3. A list of child tasks (if any)
4. Instructions for how to combine child results
"""
import dspy

from utils.dataclass import (
    LiteratureSearchAgentRequest,
    LiteratureSearchAgentResponse,
    PresearcherAgentRequest,
    ResearchGraph,
    ResearchNode,
    _normalize_question,
)
from utils.literature_search import LiteratureSearchAgent
from utils.logger import get_logger


class ExpectedOutputFormatSignature(dspy.Signature):
    """Determine the best output format for a research task.
    
    The goal is to pick the most appropriate format for answering this specific research question.
    Prefer structured or short formats over full reports when possible, as they are more precise
    and easier to compose.
    
    Common format types:
    - boolean: Yes/No answer with brief (1-2 sentence) justification
    - short_answer: A concise answer in 1-3 sentences
    - list: A bullet-point list of items (e.g., countries, technologies, key points)
    - table_csv: Structured tabular data in CSV format (for comparisons, metrics, timelines)
    - report: A detailed written report (only when the question requires extensive discussion)
    
    Choose the simplest format that fully addresses the question. For example:
    - "Is X better than Y?" → boolean
    - "What are the main applications of X?" → list
    - "Compare X, Y, and Z on metrics A, B, C" → table_csv
    - "Explain the history and implications of X" → report
    """
    
    research_task: str = dspy.InputField(
        description="The research task or question to analyze"
    )
    
    context_summary: str = dspy.InputField(
        description="A brief summary of what is known about this task from a quick literature search"
    )
    
    format_type: str = dspy.OutputField(
        description="The output format type. Must be exactly one of: boolean, short_answer, list, table_csv, report"
    )
    
    format_details: str = dspy.OutputField(
        description="Specific details about how to format the answer. For example: "
                    "'A yes/no with justification', 'A list of 5-10 key applications', "
                    "'CSV with columns: Country, GDP, Population, Year', etc."
    )


class DAGDecompositionSignature(dspy.Signature):
    """Decide whether to decompose a research task into subtasks.
    
    Given a research task and quick literature search results, decide if this task should be
    broken down into subtasks or if it can be answered directly from literature search.
    
    Decompose when:
    - The task is complex and has multiple distinct aspects that need separate investigation
    - The quick literature search shows the topic is broad and multifaceted
    - Breaking into subtasks would lead to more focused, higher-quality research
    
    Do NOT decompose when:
    - The task is already specific and focused
    - The quick literature search shows sufficient information is readily available
    - We've reached reasonable depth or node limits
    - Further decomposition would be redundant or too granular
    
    CRITICAL: Each subtask MUST be phrased as a completely standalone, independent question.
    - DO NOT reference other subtasks (e.g., avoid "these indicators", "the countries mentioned above")
    - Include ALL necessary context directly within each subtask
    - Each subtask should be researchable independently without any other information
    """
    
    research_task: str = dspy.InputField(
        description="The research task or question to potentially decompose"
    )
    
    quick_search_summary: str = dspy.InputField(
        description="Summary of findings from a quick literature search on this task"
    )
    
    current_depth: int = dspy.InputField(
        description="Current depth in the DAG (root is 0)"
    )
    
    max_depth: int = dspy.InputField(
        description="Maximum allowed depth"
    )
    
    remaining_nodes: int = dspy.InputField(
        description="Number of nodes remaining in the budget before hitting max_nodes limit"
    )
    
    max_subtasks: int = dspy.InputField(
        description="Maximum number of subtasks to generate for this node"
    )
    
    should_decompose: bool = dspy.OutputField(
        description="Whether this task should be decomposed into subtasks. Consider depth/node limits carefully."
    )
    
    subtasks: list[str] = dspy.OutputField(
        description="List of subtasks (empty if should_decompose is False). Each subtask MUST be a completely "
                    "standalone question with all necessary context included. DO NOT reference other subtasks. "
                    "DO NOT exceed max_subtasks."
    )
    
    composition_instructions: str = dspy.OutputField(
        description="Step-by-step instructions for how to combine the answers to these subtasks (and ONLY these "
                    "subtasks, without any external information) to answer the original research task. Be explicit "
                    "about which subtask answers to use and how to synthesize them. Empty if should_decompose is False."
    )


class DAGGenerationAgent:
    """Generates a complete research DAG upfront using breadth-first expansion.
    
    This agent:
    1. Starts with a root question
    2. For each node, does a quick literature search
    3. Determines the expected output format for that node
    4. Decides whether to decompose into subtasks
    5. Continues breadth-first until reaching depth/node limits
    6. Returns a complete DAG with all nodes in "pending" status
    """
    
    def __init__(
        self,
        literature_search_agent: LiteratureSearchAgent,
        lm: dspy.LM,
    ):
        self.literature_search_agent = literature_search_agent
        self.lm = lm
        self.logger = get_logger()
        
        self.format_predictor = dspy.Predict(ExpectedOutputFormatSignature)
        self.decomposition_predictor = dspy.Predict(DAGDecompositionSignature)
    
    async def generate_dag(
        self,
        request: PresearcherAgentRequest,
    ) -> ResearchGraph:
        """Generate a complete research DAG upfront.
        
        Uses breadth-first expansion with deterministic limit enforcement to ensure
        we don't exceed max_depth or max_nodes constraints.
        
        Args:
            request: PresearcherAgentRequest with topic and constraints
            
        Returns:
            Complete ResearchGraph with all nodes in "pending" status
        """
        self.logger.info(f"Starting DAG generation for topic: {request.topic}")
        self.logger.info(f"Constraints: max_depth={request.max_depth}, max_nodes={request.max_nodes}, max_subtasks={request.max_subtasks}")
        
        # Initialize graph with root node
        graph = ResearchGraph()
        root_node = graph.get_or_create_node(
            question=request.topic,
            parent_id=None,
            depth=0
        )
        
        self.logger.info(f"Created root node: {root_node.id}")
        
        # Process nodes level by level (breadth-first)
        current_depth = 0
        while current_depth < request.max_depth and len(graph.nodes) < request.max_nodes:
            # Get all nodes at current depth that haven't been processed yet
            nodes_at_depth = [
                node for node in graph.nodes.values()
                if node.depth == current_depth and node.expected_output_format is None
            ]
            
            if not nodes_at_depth:
                # No more nodes to process at this depth
                self.logger.info(f"No more nodes at depth {current_depth}, moving to next depth")
                current_depth += 1
                continue
            
            self.logger.info(f"Processing {len(nodes_at_depth)} nodes at depth {current_depth}")
            
            for node in nodes_at_depth:
                if len(graph.nodes) >= request.max_nodes:
                    self.logger.warning(f"Reached max_nodes limit ({request.max_nodes}), stopping expansion")
                    break
                
                await self._process_node(
                    graph=graph,
                    node=node,
                    request=request,
                    current_depth=current_depth,
                )
            
            current_depth += 1
        
        self.logger.info(f"DAG generation complete: {len(graph.nodes)} nodes across {current_depth} depths")
        
        # Log summary
        self.logger.save_intermediate_result(
            "00_dag_generation",
            graph.to_dict(),
            {
                "total_nodes": len(graph.nodes),
                "max_depth_reached": max(n.depth for n in graph.nodes.values()),
                "leaf_nodes": len([n for n in graph.nodes.values() if not n.children]),
            }
        )
        
        return graph
    
    async def _process_node(
        self,
        graph: ResearchGraph,
        node: ResearchNode,
        request: PresearcherAgentRequest,
        current_depth: int,
    ) -> None:
        """Process a single node: determine output format and optionally decompose.
        
        Args:
            graph: The research graph being built
            node: The node to process
            request: Original request with constraints
            current_depth: Current depth in the DAG
        """
        self.logger.debug(f"Processing node {node.id}: {node.question}")
        
        # Step 1: Quick literature search to inform decisions
        lit_search_request = LiteratureSearchAgentRequest(
            topic=node.question,
            max_retriever_calls=1,  # Quick search
            guideline="Quick overview to inform task decomposition",
            with_synthesis=True,
        )
        
        try:
            lit_search_response = await self.literature_search_agent.aforward(lit_search_request)
            search_summary = lit_search_response.writeup[:500]  # Use first 500 chars as summary
        except Exception as e:
            self.logger.warning(f"Literature search failed for node {node.id}: {e}")
            search_summary = "No literature search results available"
        
        # Step 2: Determine expected output format
        try:
            format_result = await self.format_predictor.aforward(
                research_task=node.question,
                context_summary=search_summary,
                lm=self.lm,
            )
            node.expected_output_format = format_result.format_type.strip().lower()
            
            # Validate format type
            valid_formats = ["boolean", "short_answer", "list", "table_csv", "report"]
            if node.expected_output_format not in valid_formats:
                self.logger.warning(f"Invalid format '{node.expected_output_format}', defaulting to 'report'")
                node.expected_output_format = "report"
            
            # Store format details in metadata
            node.metadata["format_details"] = format_result.format_details
            
            self.logger.debug(f"Node {node.id} output format: {node.expected_output_format}")
        
        except Exception as e:
            self.logger.error(f"Failed to determine output format for node {node.id}: {e}")
            node.expected_output_format = "report"  # Default fallback
        
        # Step 3: Decide whether to decompose
        # Don't decompose if we're at max depth or near max nodes
        can_decompose = (
            current_depth < request.max_depth - 1  # Leave room for children
            and len(graph.nodes) < request.max_nodes - 1  # Leave room for at least one child
        )
        
        if not can_decompose:
            self.logger.debug(f"Node {node.id} cannot decompose (depth or node limits)")
            return
        
        remaining_nodes = request.max_nodes - len(graph.nodes)
        
        try:
            decomp_result = await self.decomposition_predictor.aforward(
                research_task=node.question,
                quick_search_summary=search_summary,
                current_depth=current_depth,
                max_depth=request.max_depth,
                remaining_nodes=remaining_nodes,
                max_subtasks=request.max_subtasks,
                lm=self.lm,
            )
            
            should_decompose = decomp_result.should_decompose
            subtasks = decomp_result.subtasks or []
            composition_instructions = decomp_result.composition_instructions or ""
            
            if should_decompose and subtasks:
                self.logger.debug(f"Node {node.id} decomposing into {len(subtasks)} subtasks")
                
                # Limit subtasks to available node budget
                max_children = min(len(subtasks), request.max_subtasks, remaining_nodes)
                subtasks = subtasks[:max_children]
                
                # Store composition instructions
                node.composition_instructions = composition_instructions
                node.subtasks = subtasks
                
                # Create child nodes
                ancestor_questions = set()
                ancestor_questions.add(node.normalized_question or _normalize_question(node.question))
                
                for subtask in subtasks:
                    if len(graph.nodes) >= request.max_nodes:
                        break
                    
                    # Prevent cycles: don't create a child that's identical to an ancestor
                    normalized_subtask = _normalize_question(subtask)
                    if normalized_subtask in ancestor_questions:
                        self.logger.debug(f"Skipping subtask (cycle detected): {subtask}")
                        continue
                    
                    child_node = graph.get_or_create_node(
                        question=subtask,
                        parent_id=node.id,
                        depth=current_depth + 1,
                    )
                    
                    self.logger.debug(f"Created child node {child_node.id} for parent {node.id}")
            else:
                self.logger.debug(f"Node {node.id} will not decompose")
        
        except Exception as e:
            self.logger.error(f"Failed to decompose node {node.id}: {e}")
            # If decomposition fails, just leave the node as a leaf

