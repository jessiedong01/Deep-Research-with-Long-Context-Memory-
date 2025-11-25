"""DAG Processor Module for Deep Research Pipeline.

This module processes a complete research DAG bottom-up:
1. Topologically sorts nodes (leaves first)
2. For leaf nodes: conducts literature search and formats answer
3. For parent nodes: combines child results using composition instructions
4. Processes sibling nodes in parallel for efficiency
"""
import asyncio
from collections import deque
from collections.abc import Callable
from datetime import datetime
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
    - boolean: Provide "Yes." or "No." followed by a single sentence justification with citations.
    - short_answer/list/report: Provide 3-5 bullet points (`- ` prefix) summarizing key takeaways with citations.
    - table_csv/json: Provide structured data (CSV or JSON) with inline citations in headers or cells.
    
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
    - boolean: Output \"Yes.\" or \"No.\" plus one bullet with justification and citations.
    - short_answer/list/report: Output 3-5 bullets combining child findings, each with citations.
    - table_csv/json: Merge structured data while preserving child citations.
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


class CompositionValidator(dspy.Signature):
    """Validate whether a composed answer sufficiently addresses the research question.
    
    Given the original research question and the composed answer from child nodes,
    determine if there are any critical information gaps that would prevent
    fully answering the question.
    
    Be conservative: only flag gaps that are truly critical to answering the question.
    Minor details or tangential topics should NOT be flagged as gaps.
    """
    
    research_question: str = dspy.InputField(
        description="The research question that needs to be answered"
    )
    
    composed_answer: str = dspy.InputField(
        description="The answer composed from child node results"
    )
    
    is_sufficient: bool = dspy.OutputField(
        description="True if the answer adequately addresses the research question, False if critical gaps exist"
    )
    
    missing_topics: str = dspy.OutputField(
        description="If not sufficient, a comma-separated list of 1-3 specific missing topics that would fill the gaps. Empty string if sufficient."
    )


class GapFiller(dspy.Signature):
    """Generate targeted sub-questions to fill identified information gaps.
    
    Given a research question and identified missing topics, generate specific
    sub-questions that can be answered via literature search to fill those gaps.
    
    Each sub-question should be:
    - Specific and answerable via literature search
    - Directly relevant to filling the identified gap
    - Self-contained (doesn't require context from other questions)
    """
    
    research_question: str = dspy.InputField(
        description="The parent research question"
    )
    
    missing_topics: str = dspy.InputField(
        description="Comma-separated list of missing topics to address"
    )
    
    sub_questions: str = dspy.OutputField(
        description="Newline-separated list of 1-3 specific sub-questions to fill the gaps"
    )


class DAGProcessor:
    """Processes a research DAG bottom-up from leaves to root.
    
    This processor:
    1. Topologically sorts the DAG to identify processing order
    2. Processes leaf nodes with literature searches
    3. Processes parent nodes by synthesizing child results
    4. Processes sibling nodes in parallel where possible
    5. Updates node status and saves intermediate results
    6. Optionally refines parent nodes by adding new children when gaps are detected
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
        self.composition_validator = dspy.Predict(CompositionValidator)
        self.gap_filler = dspy.Predict(GapFiller)
        self._node_results: dict[str, str] = {}
        self._on_graph_update: Callable[[dict, dict], None] | None = None
    
    async def process_dag(
        self,
        graph: ResearchGraph,
        max_retriever_calls: int = 3,
        max_refinements: int = 1,
        on_graph_update: Callable[[dict, dict], None] | None = None,
    ) -> tuple[ResearchGraph, dict[str, str]]:
        """Process the entire DAG bottom-up.
        
        Args:
            graph: The research graph to process (should be generated by DAGGenerationAgent)
            max_retriever_calls: Max retriever calls per literature search
            max_refinements: Max refinement iterations per parent node (0 = disabled)
            
        Returns:
            The same graph with all nodes processed and answers populated
        """
        self.logger.info("Starting DAG processing")
        self._node_results = {}
        self._max_retriever_calls = max_retriever_calls
        self._max_refinements = max_refinements
        self._on_graph_update = on_graph_update
        self.logger.info(f"Total nodes to process: {len(graph.nodes)}")
        self.logger.info(f"Max refinements per node: {max_refinements}")
        
        # Get processing order (leaves to root)
        processing_layers = self._topological_sort_by_layers(graph)
        
        self.logger.info(f"Processing order: {len(processing_layers)} layers")
        for i, layer in enumerate(processing_layers):
            self.logger.info(f"  Layer {i}: {len(layer)} nodes at depth {graph.nodes[layer[0]].depth if layer else 'N/A'}")
        
        # Process each layer
        for layer_idx, node_ids in enumerate(processing_layers):
            self.logger.info(f"Processing layer {layer_idx} with {len(node_ids)} nodes")
            
            # Mark nodes as in_progress and save snapshot BEFORE processing
            for node_id in node_ids:
                graph.nodes[node_id].status = "in_progress"
            self._save_graph_snapshot(graph)
            
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
        
        return graph, dict(self._node_results)
    
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
        
        self.logger.debug(f"Processing node {node_id}: {node.question}")
        
        result_text = ""
        try:
            if not node.children:
                # Leaf node: conduct literature search and format answer
                result_text = await self._process_leaf_node(
                    node,
                    max_retriever_calls,
                )
            else:
                # Parent node: synthesize child results
                result_text = await self._process_parent_node(graph, node)
            
            self._node_results[node_id] = result_text
            node.metadata = dict(node.metadata)
            node.metadata["answer"] = result_text
            if graph.root_id and node_id == graph.root_id:
                node.report = result_text
            else:
                node.report = None
            node.literature_writeup = None
            node.status = "complete"
            self.logger.debug(f"Node {node_id} complete")
        
        except Exception as e:
            self.logger.error(f"Failed to process node {node_id}: {e}")
            node.status = "failed"
            error_text = f"ERROR: Processing failed: {str(e)}"
            self._node_results[node_id] = error_text
            node.metadata = dict(node.metadata)
            node.metadata["answer"] = error_text
            if graph.root_id and node_id == graph.root_id:
                node.report = error_text
            else:
                node.report = None
            node.literature_writeup = None
    
    async def _process_leaf_node(
        self,
        node: ResearchNode,
        max_retriever_calls: int,
    ) -> str:
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
            
            formatted_answer = researcher_result.formatted_answer
            self.logger.debug(f"Leaf node {node.id}: formatted answer as {node.expected_output_format}")
        
        except Exception as e:
            self.logger.warning(f"Failed to format answer for {node.id}, using raw literature writeup: {e}")
            formatted_answer = lit_response.writeup or "No answer available"
        
        # Handle empty answers
        if not formatted_answer or not formatted_answer.strip():
            return "No answer available."
        return formatted_answer.strip()
    
    async def _process_parent_node(
        self,
        graph: ResearchGraph,
        node: ResearchNode,
    ) -> str:
        """Process a parent node by synthesizing child results with optional refinement.
        
        Implements post-composition validation: after synthesizing, check if the answer
        is sufficient. If gaps are found and refinement budget remains, generate new
        leaf children to fill gaps, process them, and re-compose.
        
        Args:
            graph: The research graph
            node: The parent node to process
        """
        self.logger.debug(f"Parent node {node.id}: synthesizing {len(node.children)} children")
        
        max_refinements = getattr(self, '_max_refinements', 1)
        max_retriever_calls = getattr(self, '_max_retriever_calls', 3)
        
        for iteration in range(max_refinements + 1):
            # Gather child results
            child_results_text = []
            all_cited_docs = []
            
            for i, child_id in enumerate(node.children, 1):
                child = graph.nodes[child_id]
                child_result = f"Child {i}: {child.question}\n"
                child_answer = self._node_results.get(child_id, "No answer available")
                child_result += f"Answer:\n{child_answer}\n"
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
                
                synthesized = synthesis_result.synthesized_answer
                node.cited_documents = all_cited_docs
                self.logger.debug(f"Parent node {node.id}: synthesis complete (iteration {iteration})")
            
            except Exception as e:
                self.logger.warning(f"Failed to synthesize for {node.id}, using concatenation: {e}")
                synthesized = f"# {node.question}\n\n" + combined_child_results
                node.cited_documents = all_cited_docs
            
            # If no more refinement budget, return current result
            if iteration >= max_refinements:
                self.logger.debug(f"Parent node {node.id}: refinement budget exhausted")
                break
            
            # Validate the composed answer for gaps
            try:
                validation = await self.composition_validator.aforward(
                    research_question=node.question,
                    composed_answer=synthesized or "",
                    lm=self.lm,
                )
                
                is_sufficient = validation.is_sufficient
                missing_topics = validation.missing_topics.strip() if validation.missing_topics else ""
                
                if is_sufficient or not missing_topics:
                    self.logger.debug(f"Parent node {node.id}: answer is sufficient, no refinement needed")
                    break
                
                self.logger.info(f"Parent node {node.id}: gaps detected - {missing_topics}")
                
            except Exception as e:
                self.logger.warning(f"Validation failed for {node.id}, skipping refinement: {e}")
                break
            
            # Generate new sub-questions to fill gaps
            try:
                gap_result = await self.gap_filler.aforward(
                    research_question=node.question,
                    missing_topics=missing_topics,
                    lm=self.lm,
                )
                
                sub_questions = [q.strip() for q in gap_result.sub_questions.strip().split('\n') if q.strip()]
                if not sub_questions:
                    self.logger.debug(f"Parent node {node.id}: no sub-questions generated")
                    break
                
                # Limit to 2 new children per refinement
                sub_questions = sub_questions[:2]
                self.logger.info(f"Parent node {node.id}: adding {len(sub_questions)} new children for refinement")
                
            except Exception as e:
                self.logger.warning(f"Gap filling failed for {node.id}: {e}")
                break
            
            # Set node status to "refining" and save snapshot so frontend can show indicator
            node.status = "refining"
            self._save_graph_snapshot(graph)
            
            # Create and process new leaf children
            for sub_q in sub_questions:
                new_node = graph.get_or_create_node(
                    question=sub_q,
                    parent_id=node.id,
                    depth=node.depth + 1,
                )
                new_node.expected_output_format = "report"
                new_node.metadata["refinement_iteration"] = iteration + 1
                new_node.metadata["parent_node"] = node.id
                
                # Process the new leaf node immediately
                self.logger.debug(f"Processing refinement child {new_node.id}: {sub_q}")
                new_node.status = "in_progress"
                
                try:
                    result_text = await self._process_leaf_node(new_node, max_retriever_calls)
                    self._node_results[new_node.id] = result_text
                    new_node.metadata["answer"] = result_text
                    new_node.status = "complete"
                except Exception as e:
                    self.logger.error(f"Failed to process refinement child {new_node.id}: {e}")
                    new_node.status = "failed"
                    self._node_results[new_node.id] = f"ERROR: {e}"
            
            # Save snapshot after adding new nodes
            self._save_graph_snapshot(graph)
        
        # Handle empty answers
        if not synthesized or not synthesized.strip():
            return "No answer available."
        return synthesized.strip()
    
    def _save_graph_snapshot(self, graph: ResearchGraph) -> None:
        """Save a snapshot of the graph state for real-time visualization.
        
        Args:
            graph: The research graph
        """
        try:
            completed = len([n for n in graph.nodes.values() if n.status == "complete"])
            in_progress = len([n for n in graph.nodes.values() if n.status == "in_progress"])
            
            metadata = {
                "total_nodes": len(graph.nodes),
                "completed": completed,
                "in_progress": in_progress,
                "source": "snapshot",
                "snapshot_ts": datetime.utcnow().isoformat(),
            }
            
            self.logger.save_intermediate_result(
                "dag_processing_snapshot",
                graph.to_dict(),
                metadata,
            )
            
            # Notify via callback if provided (for WebSocket updates)
            if self._on_graph_update is not None:
                try:
                    self._on_graph_update(graph.to_dict(), metadata)
                except Exception as cb_err:
                    self.logger.warning(f"Graph update callback failed: {cb_err}")
        except Exception as e:
            self.logger.warning(f"Failed to save graph snapshot: {e}")

