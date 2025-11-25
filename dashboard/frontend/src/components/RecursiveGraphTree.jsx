import { useEffect, useMemo } from "react";
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import "./RecursiveGraphTree.css";
import dagre from "dagre";

// Map output format to icon
const getOutputFormatIcon = (format) => {
  const formatIcons = {
    boolean: "🔲",
    list: "📋",
    table_csv: "📊",
    report: "📄",
    short_answer: "💬",
  };
  return formatIcons[format] || "❓";
};

// Custom node component
function ResearchNode({ data, selected }) {
  const {
    question,
    status,
    depth,
    expectedOutputFormat,
    compositionInstructions,
    directCitations,
    childrenCitations,
    onClick,
    nodeId,
    currentNodeId,
    refinementIteration,
  } = data;

  const isCurrent = nodeId === currentNodeId;
  const isActive = status === "in_progress";
  const isRefining = status === "refining";
  const isRefinementChild = refinementIteration > 0;

  const statusColors = {
    complete: { bg: "#ecfdf5", border: "#10b981", text: "#059669" },
    completed: { bg: "#ecfdf5", border: "#10b981", text: "#059669" },
    in_progress: { bg: "#fef3c7", border: "#f59e0b", text: "#d97706" },
    refining: { bg: "#ede9fe", border: "#8b5cf6", text: "#7c3aed" },
    pending: { bg: "#f9fafb", border: "#d1d5db", text: "#6b7280" },
    failed: { bg: "#fef2f2", border: "#ef4444", text: "#dc2626" },
  };

  const colors = statusColors[status] || statusColors.pending;
  const displayStatus =
    status === "completed"
      ? "complete"
      : status === "pending"
      ? "not started"
      : status;

  // Truncate question to fit in node
  const truncatedQuestion =
    question.length > 60 ? question.substring(0, 57) + "..." : question;

  // Build tooltip content
  const tooltipContent = [
    `Question: ${question}`,
    `Format: ${expectedOutputFormat || "N/A"}`,
    `Status: ${displayStatus}`,
  ];
  if (compositionInstructions) {
    const truncated =
      compositionInstructions.length > 100
        ? compositionInstructions.substring(0, 100) + "..."
        : compositionInstructions;
    tooltipContent.push(`Composition: ${truncated}`);
  }

  return (
    <div
      className={`research-node ${selected ? "selected" : ""} ${
        isActive ? "node-active" : ""
      } ${isCurrent ? "node-current" : ""}`}
      style={{
        backgroundColor: colors.bg,
        borderColor: colors.border,
      }}
      onClick={onClick}
      title={tooltipContent.join("\n")}
    >
      <Handle
        type="target"
        position={Position.Left}
        isConnectable={false}
        style={{ opacity: 0 }}
      />
      <div className="node-header">
        {isActive && <div className="spinner-icon" />}
        {isRefining && <span className="refining-icon" title="Refining: filling information gaps">🔄</span>}
        {isRefinementChild && <span className="refinement-child-icon" title={`Added in refinement iteration ${refinementIteration}`}>🔁</span>}
        <span
          className="status-badge"
          style={{
            backgroundColor: colors.text,
          }}
        >
          {displayStatus.replace("_", " ")}
        </span>
      </div>
      <div className="node-content">
        <div className="node-question">{truncatedQuestion}</div>
        <div className="node-meta">
          <span>Depth {depth}</span>
          {expectedOutputFormat && (
            <>
              <span className="divider">•</span>
              <span
                className="format-badge"
                title={expectedOutputFormat}
              >
                {getOutputFormatIcon(expectedOutputFormat)} {expectedOutputFormat}
              </span>
            </>
          )}
          {(directCitations > 0 || childrenCitations > 0) && (
            <>
              <span className="divider">•</span>
              <span 
                className="citation-badge" 
                title={`Sources: ${directCitations} direct${childrenCitations > 0 ? ` (+ ${childrenCitations} from children)` : ''}`}
              >
                📚 {directCitations}
                {childrenCitations > 0 && ` (+${childrenCitations})`}
              </span>
            </>
          )}
        </div>
      </div>
      <Handle
        type="source"
        position={Position.Right}
        isConnectable={false}
        style={{ opacity: 0 }}
      />
    </div>
  );
}

const nodeTypes = {
  research: ResearchNode,
};

// Layout algorithm using dagre
const getLayoutedElements = (nodes, edges, direction = "LR") => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const nodeWidth = 240;
  const nodeHeight = 120;

  dagreGraph.setGraph({
    rankdir: direction,
    nodesep: 80,
    ranksep: 150,
  });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};

/**
 * RecursiveGraphTree
 *
 * Visualizes the ResearchGraph structure using ReactFlow.
 *
 * Props:
 * - graph: { root_id: string, nodes: Record<string, ResearchNodeJson> }
 * - currentNodeId?: string | null
 * - onNodeClick?: (node) => void - callback when a node is clicked
 */
export function RecursiveGraphTree({
  graph,
  currentNodeId = null,
  onNodeClick = null,
}) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Transform graph data to ReactFlow format
  const { reactFlowNodes, reactFlowEdges } = useMemo(() => {
    if (!graph || !graph.root_id || !graph.nodes) {
      return { reactFlowNodes: [], reactFlowEdges: [] };
    }

    const { root_id: rootId, nodes: graphNodes } = graph;
    const reactFlowNodes = [];
    const reactFlowEdges = [];
    const visited = new Set();

    const processNode = (nodeId) => {
      if (visited.has(nodeId)) return;
      visited.add(nodeId);

      const node = graphNodes[nodeId];
      if (!node) return;

      const status = (node.status || "pending").toLowerCase();

      // Calculate citation counts
      // Only leaf nodes have direct citations; intermediate nodes inherit from children
      const isLeaf = !Array.isArray(node.children) || node.children.length === 0;
      const directCitations = isLeaf ? (node.cited_documents?.length || 0) : 0;
      
      // Calculate children's citations (recursive)
      let childrenCitations = 0;
      if (Array.isArray(node.children)) {
        const countChildCitations = (childNodeId) => {
          const childNode = graphNodes[childNodeId];
          if (!childNode) return 0;
          const childIsLeaf = !Array.isArray(childNode.children) || childNode.children.length === 0;
          let count = childIsLeaf ? (childNode.cited_documents?.length || 0) : 0;
          if (childNode.children) {
            childNode.children.forEach(cid => {
              count += countChildCitations(cid);
            });
          }
          return count;
        };
        node.children.forEach(childId => {
          childrenCitations += countChildCitations(childId);
        });
      }

      // Create ReactFlow node
      reactFlowNodes.push({
        id: nodeId,
        type: "research",
        data: {
          question: node.question || nodeId,
          status,
          depth: node.depth ?? 0,
          expectedOutputFormat: node.expected_output_format,
          compositionInstructions: node.composition_instructions,
          directCitations,
          childrenCitations,
          refinementIteration: node.metadata?.refinement_iteration || 0,
          fullData: node,
          nodeId,
          currentNodeId,
          onClick: () => {
            if (onNodeClick) {
              onNodeClick(node);
            }
          },
        },
        position: { x: 0, y: 0 }, // Will be set by layout algorithm
      });

      // Create edges to children
      if (Array.isArray(node.children)) {
        node.children.forEach((childId) => {
          const edgeColor =
            status === "complete" || status === "completed"
              ? "#10b981"
              : "#64748b";
          reactFlowEdges.push({
            id: `${nodeId}-${childId}`,
            source: nodeId,
            target: childId,
            type: "smoothstep",
            animated: status === "in_progress",
            style: {
              stroke: edgeColor,
              strokeWidth: 2.5,
              strokeDasharray: "5,5",
            },
            markerEnd: {
              type: "arrowclosed",
              color: edgeColor,
            },
          });

          processNode(childId);
        });
      }
    };

    processNode(rootId);

    return { reactFlowNodes, reactFlowEdges };
  }, [graph, onNodeClick]);

  // Apply layout when data changes
  useEffect(() => {
    if (reactFlowNodes.length > 0) {
      const { nodes: layoutedNodes, edges: layoutedEdges } =
        getLayoutedElements(reactFlowNodes, reactFlowEdges);
      setNodes(layoutedNodes);
      setEdges(layoutedEdges);
    }
  }, [reactFlowNodes, reactFlowEdges, setNodes, setEdges]);

  if (!graph || !graph.root_id || !graph.nodes) {
    return (
      <div className="graph-empty">
        <p>Graph not available for this run yet.</p>
      </div>
    );
  }

  return (
    <div className="recursive-graph-container">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.1}
        maxZoom={1.5}
        defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={16}
          size={1}
          color="#d1d5db"
        />
        <Controls />
      </ReactFlow>
    </div>
  );
}
