"""DAG Processor Module for Deep Research Pipeline.

This module processes a complete research DAG bottom-up:
1. Topologically sorts nodes (leaves first)
2. For leaf nodes: conducts literature search and formats answer
3. For parent nodes: combines child results using composition instructions
4. Processes sibling nodes in parallel for efficiency
"""
import asyncio
from collections import deque
import dspy

from utils.dataclass import (
    LiteratureSearchAgentRequest,
    LiteratureSearchAgentResponse,
    ResearchGraph,
    ResearchNode,
    RetrievedDocument,
)
from utils.literature_search import LiteratureSearchAgent
from utils.logger import get_logger


class LeafNodeResearcher(dspy.Signature):
    """Answer a leaf node research task using literature search results.
    
    Given literature search results and the expected output format, provide an answer
    that strictly adheres to the format requirements.
    
    Format types and requirements:
    - boolean: Provide "Yes" or "No" followed by a 1-2 sentence justification
    - short_answer: Provide a concise answer in 1-3 sentences
    - list: Provide a bullet-point list (use "- " prefix for each item)
    - table_csv: Provide data in CSV format with clear column headers
    - report: Provide a detailed written report with proper structure
    
    CRITICAL: Preserve all citations from the literature search in [X] format.
    Do not add citations that aren't in the source material.
    """
    
    research_task: str = dspy.InputField(
        description="The research task or question to answer"
    )
    
    literature_search_results: str = dspy.InputField(
        description="The synthesized writeup from literature search with inline citations [1], [2], etc."
    )
    
    expected_format: str = dspy.InputField(
        description="The required output format: boolean, short_answer, list, table_csv, or report"
    )
    
    format_details: str = dspy.InputField(
        description="Specific formatting requirements for this task"
    )
    
    formatted_answer: str = dspy.OutputField(
        description="The answer in the exact required format, preserving all citations [X] from the literature search"
    )


class ParentNodeSynthesizer(dspy.Signature):
    """Synthesize answers from child nodes to answer a parent node's research task.
    
    Given the answers from all child subtasks and composition instructions, combine them
    to produce the answer for the parent task in the required format.
    
    CRITICAL RULES:
    1. Use ONLY the information from the child results - no external knowledge
    2. Follow the composition instructions exactly
    3. Preserve all citations from child results
    4. Output in the specified format
    5. If child results contradict, acknowledge and explain the contradiction
    
    Format types:
    - boolean: Yes/No with justification based on synthesis
    - short_answer: 1-3 sentence synthesis
    - list: Combined/deduplicated list from children
    - table_csv: Merged table data
    - report: Comprehensive synthesis report
    """
    
    research_task: str = dspy.InputField(
        description="The parent research task to answer"
    )
    
    child_results: str = dspy.InputField(
        description="The formatted answers from all child subtasks with their citations. "
                    "Format: 'Child 1: [question]\n[answer]\n\nChild 2: [question]\n[answer]...'"
    )
    
    composition_instructions: str = dspy.InputField(
        description="Step-by-step instructions for how to combine the child results"
    )
    
    expected_format: str = dspy.InputField(
        description="The required output format: boolean, short_answer, list, table_csv, or report"
    )
    
    format_details: str = dspy.InputField(
        description="Specific formatting requirements"
    )
    
    synthesized_answer: str = dspy.OutputField(
        description="The synthesized answer combining all child results according to composition "
                    "instructions, in the required format, preserving all citations"
    )


class DAGProcessor:
    """Processes a research DAG bottom-up from leaves to root.
    
    This processor:
    1. Topologically sorts the DAG to identify processing order
    2. Processes leaf nodes with literature searches
    3. Processes parent nodes by synthesizing child results
    4. Processes sibling nodes in parallel where possible
    5. Updates node status and saves intermediate results
    """
    
    def __init__(
        self,
        literature_search_agent: LiteratureSearchAgent,
        lm: dspy.LM,
    ):
        self.literature_search_agent = literature_search_agent
        self.lm = lm
        self.logger = get_logger()
        
        self.leaf_researcher = dspy.Predict(LeafNodeResearcher)
        self.parent_synthesizer = dspy.Predict(ParentNodeSynthesizer)
    
    async def process_dag(
        self,
        graph: ResearchGraph,
        max_retriever_calls: int = 3,
    ) -> ResearchGraph:
        """Process the entire DAG bottom-up.
        
        Args:
            graph: The research graph to process (should be generated by DAGGenerationAgent)
            max_retriever_calls: Max retriever calls per literature search
            
        Returns:
            The same graph with all nodes processed and answers populated
        """
        self.logger.info("Starting DAG processing")
        self.logger.info(f"Total nodes to process: {len(graph.nodes)}")
        
        # Get processing order (leaves to root)
        processing_layers = self._topological_sort_by_layers(graph)
        
        self.logger.info(f"Processing order: {len(processing_layers)} layers")
        for i, layer in enumerate(processing_layers):
            self.logger.info(f"  Layer {i}: {len(layer)} nodes at depth {graph.nodes[layer[0]].depth if layer else 'N/A'}")
        
        # Process each layer
        for layer_idx, node_ids in enumerate(processing_layers):
            self.logger.info(f"Processing layer {layer_idx} with {len(node_ids)} nodes")
            
            # Process all nodes in this layer in parallel
            tasks = []
            for node_id in node_ids:
                task = self._process_node(graph, node_id, max_retriever_calls)
                tasks.append(task)
            
            # Wait for all nodes in this layer to complete
            await asyncio.gather(*tasks)
            
            self.logger.info(f"Layer {layer_idx} complete")
            
            # Save snapshot after each layer
            self._save_graph_snapshot(graph)
        
        self.logger.info("DAG processing complete")
        
        # Save final processed graph
        self.logger.save_intermediate_result(
            "01_dag_processed",
            graph.to_dict(),
            {
                "total_nodes": len(graph.nodes),
                "completed_nodes": len([n for n in graph.nodes.values() if n.status == "complete"]),
            }
        )
        
        return graph
    
    def _topological_sort_by_layers(self, graph: ResearchGraph) -> list[list[str]]:
        """Sort nodes into layers for bottom-up processing.
        
        Returns a list of layers, where each layer is a list of node IDs.
        Layers are ordered from leaves (layer 0) to root (last layer).
        Nodes in the same layer can be processed in parallel.
        
        Args:
            graph: The research graph
            
        Returns:
            List of layers, each layer is a list of node IDs
        """
        # Calculate in-degree (number of children) for each node
        in_degree = {node_id: len(node.children) for node_id, node in graph.nodes.items()}
        
        # Find all leaf nodes (in-degree 0)
        current_layer = [node_id for node_id, degree in in_degree.items() if degree == 0]
        
        layers = []
        processed = set()
        
        while current_layer:
            layers.append(current_layer)
            processed.update(current_layer)
            
            # Find next layer: nodes whose children are all processed
            next_layer = []
            for node_id in graph.nodes:
                if node_id in processed:
                    continue
                
                node = graph.nodes[node_id]
                # Check if all children are processed
                if all(child_id in processed for child_id in node.children):
                    next_layer.append(node_id)
            
            current_layer = next_layer
        
        return layers
    
    async def _process_node(
        self,
        graph: ResearchGraph,
        node_id: str,
        max_retriever_calls: int,
    ) -> None:
        """Process a single node: either research (leaf) or synthesize (parent).
        
        Args:
            graph: The research graph
            node_id: ID of the node to process
            max_retriever_calls: Max retriever calls for literature search
        """
        node = graph.nodes[node_id]
        node.status = "in_progress"
        
        self.logger.debug(f"Processing node {node_id}: {node.question}")
        
        try:
            if not node.children:
                # Leaf node: conduct literature search and format answer
                await self._process_leaf_node(node, max_retriever_calls)
            else:
                # Parent node: synthesize child results
                await self._process_parent_node(graph, node)
            
            node.status = "complete"
            self.logger.debug(f"Node {node_id} complete")
        
        except Exception as e:
            self.logger.error(f"Failed to process node {node_id}: {e}")
            node.status = "failed"
            node.report = f"ERROR: Processing failed: {str(e)}"
    
    async def _process_leaf_node(
        self,
        node: ResearchNode,
        max_retriever_calls: int,
    ) -> None:
        """Process a leaf node by conducting literature search.
        
        Args:
            node: The leaf node to process
            max_retriever_calls: Max retriever calls
        """
        self.logger.debug(f"Leaf node {node.id}: conducting literature search")
        
        # Conduct literature search
        lit_request = LiteratureSearchAgentRequest(
            topic=node.question,
            max_retriever_calls=max_retriever_calls,
            guideline="Comprehensive search to answer the research question",
            with_synthesis=True,
        )
        
        lit_response = await self.literature_search_agent.aforward(lit_request)
        
        # Store literature results
        node.literature_writeup = lit_response.writeup
        node.cited_documents = list(lit_response.cited_documents)
        
        # Format answer according to expected format
        format_details = node.metadata.get("format_details", "")
        
        try:
            researcher_result = await self.leaf_researcher.aforward(
                research_task=node.question,
                literature_search_results=lit_response.writeup,
                expected_format=node.expected_output_format or "report",
                format_details=format_details,
                lm=self.lm,
            )
            
            node.report = researcher_result.formatted_answer
            self.logger.debug(f"Leaf node {node.id}: formatted answer as {node.expected_output_format}")
        
        except Exception as e:
            self.logger.warning(f"Failed to format answer for {node.id}, using raw literature writeup: {e}")
            node.report = lit_response.writeup
    
    async def _process_parent_node(
        self,
        graph: ResearchGraph,
        node: ResearchNode,
    ) -> None:
        """Process a parent node by synthesizing child results.
        
        Args:
            graph: The research graph
            node: The parent node to process
        """
        self.logger.debug(f"Parent node {node.id}: synthesizing {len(node.children)} children")
        
        # Gather child results
        child_results_text = []
        all_cited_docs = []
        
        for i, child_id in enumerate(node.children, 1):
            child = graph.nodes[child_id]
            child_result = f"Child {i}: {child.question}\n"
            child_result += f"Answer:\n{child.report or 'No answer available'}\n"
            child_results_text.append(child_result)
            
            # Collect cited documents from children
            all_cited_docs.extend(child.cited_documents)
        
        combined_child_results = "\n".join(child_results_text)
        
        # Synthesize using composition instructions
        format_details = node.metadata.get("format_details", "")
        composition_instr = node.composition_instructions or "Combine the child results to answer the parent question."
        
        try:
            synthesis_result = await self.parent_synthesizer.aforward(
                research_task=node.question,
                child_results=combined_child_results,
                composition_instructions=composition_instr,
                expected_format=node.expected_output_format or "report",
                format_details=format_details,
                lm=self.lm,
            )
            
            node.report = synthesis_result.synthesized_answer
            node.cited_documents = all_cited_docs  # Inherit citations from children
            
            self.logger.debug(f"Parent node {node.id}: synthesis complete")
        
        except Exception as e:
            self.logger.warning(f"Failed to synthesize for {node.id}, using concatenation: {e}")
            # Fallback: just concatenate child results
            node.report = f"# {node.question}\n\n" + combined_child_results
            node.cited_documents = all_cited_docs
    
    def _save_graph_snapshot(self, graph: ResearchGraph) -> None:
        """Save a snapshot of the graph state for real-time visualization.
        
        Args:
            graph: The research graph
        """
        try:
            completed = len([n for n in graph.nodes.values() if n.status == "complete"])
            in_progress = len([n for n in graph.nodes.values() if n.status == "in_progress"])
            
            self.logger.save_intermediate_result(
                "dag_processing_snapshot",
                graph.to_dict(),
                {
                    "total_nodes": len(graph.nodes),
                    "completed": completed,
                    "in_progress": in_progress,
                }
            )
        except Exception as e:
            self.logger.warning(f"Failed to save graph snapshot: {e}")

