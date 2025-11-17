import { useEffect, useMemo, useState, useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import "./RecursiveGraphTree.css";
import ReactMarkdown from "react-markdown";
import dagre from "dagre";

// Custom node component
function ResearchNode({ data, selected }) {
  const { question, status, depth, isAnswerable, onClick } = data;
  
  const statusColors = {
    complete: { bg: "#ecfdf5", border: "#10b981", text: "#059669" },
    completed: { bg: "#ecfdf5", border: "#10b981", text: "#059669" },
    in_progress: { bg: "#fffbeb", border: "#f59e0b", text: "#d97706" },
    pending: { bg: "#f9fafb", border: "#d1d5db", text: "#6b7280" },
    failed: { bg: "#fef2f2", border: "#ef4444", text: "#dc2626" },
  };

  const colors = statusColors[status] || statusColors.pending;
  const displayStatus = status === "completed" ? "complete" : status;
  
  // Truncate question to fit in node
  const truncatedQuestion = question.length > 60 ? question.substring(0, 57) + "..." : question;

  return (
    <div
      className={`research-node ${selected ? "selected" : ""}`}
      style={{
        backgroundColor: colors.bg,
        borderColor: colors.border,
      }}
      onClick={onClick}
    >
      <div className="node-header">
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
          {typeof isAnswerable === "boolean" && (
            <span className="divider">•</span>
          )}
          {typeof isAnswerable === "boolean" && (
            <span>{isAnswerable ? "Answerable" : "Not answerable"}</span>
          )}
        </div>
      </div>
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
 */
export function RecursiveGraphTree({ graph, currentNodeId = null }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState(null);

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

      // Create ReactFlow node
      reactFlowNodes.push({
        id: nodeId,
        type: "research",
        data: {
          question: node.question || nodeId,
          status,
          depth: node.depth ?? 0,
          isAnswerable: node.is_answerable,
          fullData: node,
          onClick: () => {
            setSelectedNode(node);
          },
        },
        position: { x: 0, y: 0 }, // Will be set by layout algorithm
      });

      // Create edges to children
      if (Array.isArray(node.children)) {
        node.children.forEach((childId) => {
          reactFlowEdges.push({
            id: `${nodeId}-${childId}`,
            source: nodeId,
            target: childId,
            type: "smoothstep",
            animated: status === "in_progress",
            style: {
              stroke: status === "complete" || status === "completed" ? "#10b981" : "#94a3b8",
              strokeWidth: 2,
            },
            markerEnd: {
              type: "arrowclosed",
              color: status === "complete" || status === "completed" ? "#10b981" : "#94a3b8",
            },
          });

          processNode(childId);
        });
      }
    };

    processNode(rootId);

    return { reactFlowNodes, reactFlowEdges };
  }, [graph]);

  // Apply layout when data changes
  useEffect(() => {
    if (reactFlowNodes.length > 0) {
      const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
        reactFlowNodes,
        reactFlowEdges
      );
      setNodes(layoutedNodes);
      setEdges(layoutedEdges);
    }
  }, [reactFlowNodes, reactFlowEdges, setNodes, setEdges]);

  const handleClosePanel = useCallback(() => {
    setSelectedNode(null);
  }, []);

  if (!graph || !graph.root_id || !graph.nodes) {
    return (
      <div className="graph-empty">
        <p>Graph not available for this run yet.</p>
      </div>
    );
  }

  return (
    <div className="recursive-graph-container">
      <div className={`graph-view ${selectedNode ? "with-panel" : ""}`}>
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
          <Background color="#e5e7eb" gap={16} />
          <Controls />
          <MiniMap
            nodeColor={(node) => {
              const status = node.data.status;
              const colors = {
                complete: "#10b981",
                completed: "#10b981",
                in_progress: "#f59e0b",
                pending: "#d1d5db",
                failed: "#ef4444",
              };
              return colors[status] || "#d1d5db";
            }}
            maskColor="rgba(0, 0, 0, 0.05)"
          />
        </ReactFlow>
      </div>

      {selectedNode && (
        <div className="detail-panel">
          <div className="detail-panel-header">
            <h3>Node Details</h3>
            <button className="close-button" onClick={handleClosePanel}>
              ✕
            </button>
          </div>
          <div className="detail-panel-content">
            <div className="detail-section">
              <h4>Question</h4>
              <p className="question-full">{selectedNode.question}</p>
            </div>

            <div className="detail-section">
              <h4>Metadata</h4>
              <div className="metadata-grid">
                <div className="metadata-item">
                  <span className="label">Status:</span>
                  <span className={`value status-${selectedNode.status}`}>
                    {selectedNode.status}
                  </span>
                </div>
                <div className="metadata-item">
                  <span className="label">Depth:</span>
                  <span className="value">{selectedNode.depth ?? 0}</span>
                </div>
                {typeof selectedNode.is_answerable === "boolean" && (
                  <div className="metadata-item">
                    <span className="label">Answerable:</span>
                    <span className="value">
                      {selectedNode.is_answerable ? "Yes" : "No"}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {selectedNode.literature_writeup && (
              <div className="detail-section">
                <h4>Literature Writeup</h4>
                <div className="markdown-content">
                  <ReactMarkdown>{selectedNode.literature_writeup}</ReactMarkdown>
                </div>
              </div>
            )}

            {selectedNode.subtasks && selectedNode.subtasks.length > 0 && (
              <div className="detail-section">
                <h4>Subtasks ({selectedNode.subtasks.length})</h4>
                <ul className="subtasks-list">
                  {selectedNode.subtasks.map((subtask, index) => (
                    <li key={index}>{subtask}</li>
                  ))}
                </ul>
              </div>
            )}

            {selectedNode.children && selectedNode.children.length > 0 && (
              <div className="detail-section">
                <h4>Children Nodes ({selectedNode.children.length})</h4>
                <div className="children-list">
                  {selectedNode.children.map((childId) => {
                    const childNode = graph.nodes[childId];
                    return (
                      <button
                        key={childId}
                        className="child-node-button"
                        onClick={() => setSelectedNode(childNode)}
                      >
                        {childNode?.question || childId}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
