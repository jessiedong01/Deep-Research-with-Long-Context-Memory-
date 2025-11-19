/**
 * Component to display detailed information about a pipeline run,
 * including an interactive visualization of the recursive research tree.
 */
import { useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { api } from "../api";
import { useWebSocket } from "../hooks/useWebSocket";
import { RecursiveGraphTree } from "./RecursiveGraphTree";
import PhaseProgress from "./PhaseProgress";
import "./RunDetail.css";

export function RunDetail() {
  const { runId } = useParams();
  const [runDetail, setRunDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [graph, setGraph] = useState(null);
  const [graphLoading, setGraphLoading] = useState(false);
  const [graphError, setGraphError] = useState(null);
  const [graphNotFound, setGraphNotFound] = useState(false);
  const [error, setError] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [phaseData, setPhaseData] = useState(null);
  const [phaseLoading, setPhaseLoading] = useState(false);

  // Connect WebSocket for real-time updates if run is active
  const { messages } = useWebSocket(
    runDetail?.metadata?.status === "running" ? runId : null
  );

  // Poll for updates if the run is in progress
  useEffect(() => {
    if (runDetail?.metadata?.status === "running") {
      const interval = setInterval(() => {
        loadRunDetail();
        // Only retry loading graph if we haven't received a 404
        if (!graphNotFound) {
          loadGraph();
        }
        // Also update phase data for three-phase runs
        if (runDetail?.metadata?.is_three_phase) {
          loadPhaseData();
        }
      }, 5000); // Refresh every 5 seconds

      return () => clearInterval(interval);
    }
  }, [
    runDetail?.metadata?.status,
    runDetail?.metadata?.is_three_phase,
    graphNotFound,
  ]);

  useEffect(() => {
    // Reset graph not found state when switching runs
    setGraphNotFound(false);
    loadRunDetail();
    loadGraph();
    loadPhaseData();
  }, [runId]);

  // Live timer for running tasks
  useEffect(() => {
    if (
      runDetail?.metadata?.status === "running" &&
      runDetail?.metadata?.started_at
    ) {
      // Calculate initial elapsed time
      const startTime = new Date(runDetail.metadata.started_at).getTime();
      const updateElapsed = () => {
        const now = Date.now();
        const elapsed = Math.floor((now - startTime) / 1000);
        setElapsedSeconds(elapsed);
      };

      // Update immediately
      updateElapsed();

      // Update every second
      const interval = setInterval(updateElapsed, 1000);

      return () => clearInterval(interval);
    } else if (runDetail?.metadata?.duration_seconds) {
      // Use the fixed duration for completed runs
      setElapsedSeconds(runDetail.metadata.duration_seconds);
    }
  }, [
    runDetail?.metadata?.status,
    runDetail?.metadata?.started_at,
    runDetail?.metadata?.duration_seconds,
  ]);

  const loadRunDetail = async () => {
    try {
      setLoading(true);
      const data = await api.fetchRunDetail(runId);
      setRunDetail(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadGraph = async () => {
    try {
      setGraphLoading(true);
      const data = await api.fetchRunGraph(runId);
      setGraph(data);
      setGraphError(null);
      setGraphNotFound(false);
    } catch (err) {
      console.error("Error loading graph:", err);
      setGraph(null);
      setGraphError(err.message);
      // If it's a 404, mark graph as not found to avoid retrying
      if (err.message.includes("404") || err.message.includes("not found")) {
        setGraphNotFound(true);
      }
    } finally {
      setGraphLoading(false);
    }
  };

  const loadPhaseData = async () => {
    try {
      setPhaseLoading(true);
      const data = await api.fetchPhaseStatus(runId);
      setPhaseData(data);
    } catch (err) {
      console.error("Error loading phase data:", err);
      setPhaseData(null);
    } finally {
      setPhaseLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "N/A";
    const date = new Date(dateStr);
    return date.toLocaleString();
  };

  const formatDuration = (seconds) => {
    if (seconds === null || seconds === undefined) return "N/A";
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
      return `${hours}h ${mins}m ${secs}s`;
    }
    return `${mins}m ${secs}s`;
  };

const formatGraphTimestamp = (timestamp) => {
  if (!timestamp) return null;
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return timestamp;
  }
  return date.toLocaleString();
};

  const getStatusBadge = (status) => {
    const statusClass = `status-badge status-${status.toLowerCase()}`;
    return <span className={statusClass}>{status}</span>;
  };

  const getStepStatusIcon = (status) => {
    switch (status) {
      case "completed":
        return "✓";
      case "in_progress":
        return null; // Will show spinner instead
      case "failed":
        return "✗";
      default:
        return "○";
    }
  };

  const derivedCurrentNodeId = useMemo(() => {
    if (!graph || !graph.graph) return null;

    const meta = graph.metadata || {};
    if (typeof meta.current_node_id === "string") {
      return meta.current_node_id;
    }

    const { nodes, root_id: rootId } = graph.graph;
    if (!nodes || !rootId) return null;

    // Prefer an in-progress node if the run is still running.
    const allNodes = Object.values(nodes);
    if (runDetail?.metadata?.status === "running") {
      const inProgress = allNodes.find(
        (node) =>
          typeof node.status === "string" &&
          node.status.toLowerCase() === "in_progress"
      );
      if (inProgress && typeof inProgress.id === "string") {
        return inProgress.id;
      }
    }

    // Otherwise, fall back to the deepest completed node if available.
    let bestId = rootId;
    let bestDepth = -1;
    for (const node of allNodes) {
      const depth = typeof node.depth === "number" ? node.depth : 0;
      const status =
        typeof node.status === "string" ? node.status.toLowerCase() : "pending";
      if (status === "complete" || status === "completed") {
        if (depth > bestDepth) {
          bestDepth = depth;
          bestId = node.id || bestId;
        }
      }
    }

    return bestId;
  }, [graph, runDetail?.metadata?.status]);

  // Get the root node and check if it has a completed report
  const rootNodeReport = useMemo(() => {
    if (!graph || !graph.graph) return null;

    const { nodes, root_id: rootId } = graph.graph;
    if (!nodes || !rootId) return null;

    const rootNode = nodes[rootId];
    if (!rootNode) return null;

    const status =
      typeof rootNode.status === "string"
        ? rootNode.status.toLowerCase()
        : "pending";

    if (status === "complete" || status === "completed") {
      return rootNode.report || null;
    }

    return null;
  }, [graph]);

  // Determine current activity message
  const getActivityMessage = () => {
    if (!graph || !graph.graph || !derivedCurrentNodeId) {
      return "Initializing pipeline...";
    }

    const node = graph.graph.nodes[derivedCurrentNodeId];
    if (!node) {
      return "Processing...";
    }

    const status =
      typeof node.status === "string" ? node.status.toLowerCase() : "pending";

    // Determine activity based on node status and context
    if (status === "in_progress") {
      if (!node.children || node.children.length === 0) {
        return "Conducting literature review...";
      }
      return "Synthesizing child results...";
    } else if (status === "pending") {
      return "Queued for exploration...";
    } else if (status === "complete" || status === "completed") {
      // Find if there are any in-progress nodes
      const nodes = Object.values(graph.graph.nodes);
      const inProgressNode = nodes.find(
        (n) =>
          typeof n.status === "string" &&
          n.status.toLowerCase() === "in_progress"
      );
      if (inProgressNode) {
        return "Processing next node...";
      }
      return "Finalizing research...";
    }

    return "Processing...";
  };

  if (loading) {
    return <div className="loading">Loading run details...</div>;
  }

  if (error) {
    return (
      <div className="error">
        <h3>Error loading run details</h3>
        <p>{error}</p>
        <Link to="/">Back to Runs List</Link>
      </div>
    );
  }

  if (!runDetail) {
    return <div className="error">Run not found</div>;
  }

  return (
    <div className="run-detail">
      <div className="run-detail-header">
        <div className="header-content">
          <Link to="/" className="back-link">
            ← Back to Runs
          </Link>
          <h1>{runDetail.metadata.topic}</h1>
          <div className="run-meta">
            {getStatusBadge(runDetail.metadata.status)}
            <span>Duration: {formatDuration(elapsedSeconds)}</span>
          </div>
        </div>
      </div>

      <div className="run-detail-content">
        <section className="run-summary-panel">
          <h2>Run Summary</h2>
          <div className="run-summary-grid">
            <div className="run-summary-item">
              <span className="label">Topic</span>
              <span className="value">{runDetail.metadata.topic}</span>
            </div>
            <div className="run-summary-item">
              <span className="label">Run ID</span>
              <span className="value monospace">
                {runDetail.metadata.run_id}
              </span>
            </div>
            <div className="run-summary-item">
              <span className="label">Status</span>
              <span className="value">
                {getStatusBadge(runDetail.metadata.status)}
              </span>
            </div>
            <div className="run-summary-item">
              <span className="label">Created</span>
              <span className="value">
                {formatDate(runDetail.metadata.created_at)}
              </span>
            </div>
            <div className="run-summary-item">
              <span className="label">Duration</span>
              <span className="value">{formatDuration(elapsedSeconds)}</span>
            </div>
            {typeof runDetail.metadata.max_retriever_calls === "number" && (
              <div className="run-summary-item">
                <span className="label">Max Retriever Calls</span>
                <span className="value">
                  {runDetail.metadata.max_retriever_calls}
                </span>
              </div>
            )}
            {typeof runDetail.metadata.max_depth === "number" && (
              <div className="run-summary-item">
                <span className="label">Max Depth</span>
                <span className="value">{runDetail.metadata.max_depth}</span>
              </div>
            )}
            {typeof runDetail.metadata.max_nodes === "number" && (
              <div className="run-summary-item">
                <span className="label">Max Nodes</span>
                <span className="value">{runDetail.metadata.max_nodes}</span>
              </div>
            )}
            {typeof runDetail.metadata.max_subtasks === "number" && (
              <div className="run-summary-item">
                <span className="label">Max Subtasks</span>
                <span className="value">{runDetail.metadata.max_subtasks}</span>
              </div>
            )}
            {graph?.metadata && (
              <>
                {typeof graph.metadata.total_nodes === "number" && (
                  <div className="run-summary-item">
                    <span className="label">Graph Nodes</span>
                    <span className="value">{graph.metadata.total_nodes}</span>
                  </div>
                )}
                {typeof graph.metadata.max_depth === "number" && (
                  <div className="run-summary-item">
                    <span className="label">Graph Max Depth</span>
                    <span className="value">{graph.metadata.max_depth}</span>
                  </div>
                )}
              </>
            )}
          </div>

          <div className="activity-indicator-card">
            <h3>Status</h3>
            <div
              className={`activity-indicator ${
                runDetail?.metadata?.status === "completed"
                  ? "activity-completed"
                  : runDetail?.metadata?.status === "failed"
                  ? "activity-failed"
                  : ""
              }`}
            >
              {runDetail?.metadata?.status === "running" ? (
                <div className="activity-spinner"></div>
              ) : runDetail?.metadata?.status === "completed" ? (
                <div className="activity-checkmark">✓</div>
              ) : runDetail?.metadata?.status === "failed" ? (
                <div className="activity-error">✗</div>
              ) : null}
              <div className="activity-message">
                {runDetail?.metadata?.status === "completed"
                  ? "Deep Research Complete"
                  : runDetail?.metadata?.status === "failed"
                  ? "Research Failed"
                  : runDetail?.metadata?.status === "running"
                  ? getActivityMessage()
                  : "Pending"}
              </div>
            </div>
          </div>
        </section>

        <section className="run-graph-panel">
          <h2>Recursive Research Tree</h2>
          <div className="graph-and-details-container">
            <div className="graph-wrapper">
              {graph?.metadata && (
                <div className="graph-refresh-meta">
                  <span>
                    Source:{" "}
                    {graph.metadata.graph_source === "snapshot"
                      ? "In-progress snapshot"
                      : "Final graph"}
                  </span>
                  {graph.metadata.snapshot_ts && (
                    <span>
                      Updated: {formatGraphTimestamp(graph.metadata.snapshot_ts)}
                    </span>
                  )}
                </div>
              )}
              <div className="graph-flow-container">
                {graphLoading ? (
                  <div className="loading">
                    <div className="spinner"></div>
                    <p>Loading graph...</p>
                  </div>
                ) : graphError ? (
                  <div className="error">
                    <h3>Graph not available</h3>
                    <p>{graphError}</p>
                  </div>
                ) : (
                  <RecursiveGraphTree
                    graph={graph?.graph}
                    currentNodeId={derivedCurrentNodeId}
                    onNodeClick={setSelectedNode}
                  />
                )}
              </div>
            </div>

            <div className="node-detail-sidebar">
              <div className="node-detail-header">
                <h3>Node Details</h3>
                {selectedNode && (
                  <button
                    className="close-detail-button"
                    onClick={() => setSelectedNode(null)}
                  >
                    ✕
                  </button>
                )}
              </div>
              <div className="node-detail-content">
                {selectedNode ? (
                  <>
                    <div className="node-detail-section">
                      <h4>Question</h4>
                      <p className="node-question-full">
                        {selectedNode.question}
                      </p>
                    </div>

                    <div className="node-detail-section">
                      <h4>Metadata</h4>
                      <div className="node-metadata-grid">
                        <div className="node-metadata-item">
                          <span className="label">Status:</span>
                          <span
                            className={`value status-${selectedNode.status}`}
                          >
                            {selectedNode.status}
                          </span>
                        </div>
                        <div className="node-metadata-item">
                          <span className="label">Depth:</span>
                          <span className="value">
                            {selectedNode.depth ?? 0}
                          </span>
                        </div>
                      </div>
                    </div>

                    {(() => {
                      const rootId = graph?.graph?.root_id;
                      const isRootNode =
                        rootId && selectedNode?.id && selectedNode.id === rootId;
                      const nodeAnswer =
                        selectedNode?.metadata?.answer ||
                        (isRootNode ? selectedNode.report : null);

                      if (!nodeAnswer) {
                        return (
                          <div className="node-detail-section">
                            <p className="section-description">
                              No textual answer stored for this node yet.
                            </p>
                          </div>
                        );
                      }

                      return (
                        <div className="node-detail-section">
                          <h4>{isRootNode ? "Final Report" : "Answer"}</h4>
                          <p className="section-description">
                            {isRootNode
                              ? "Comprehensive synthesis for the full research task."
                              : "Summary generated for this sub-question."}
                          </p>
                          <div className="node-markdown-content">
                            <ReactMarkdown>{nodeAnswer}</ReactMarkdown>
                          </div>
                        </div>
                      );
                    })()}

                    {Array.isArray(selectedNode.cited_documents) &&
                      selectedNode.cited_documents.length > 0 && (
                        <div className="node-detail-section">
                          <h4>
                            Sources ({selectedNode.cited_documents.length})
                          </h4>
                          <ul className="node-citations-list">
                            {selectedNode.cited_documents.map((doc, idx) => {
                              const title = doc.title || doc.url || `Source ${idx + 1}`;
                              return (
                                <li key={doc.url || `${selectedNode.id}-doc-${idx}`}>
                                  <div className="citation-main">
                                    <span className="citation-title">{title}</span>
                                    {doc.url && (
                                      <span className="citation-url">{doc.url}</span>
                                    )}
                                    {doc.url && (
                                      <a
                                        href={doc.url}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="citation-link"
                                      >
                                        Visit →
                                      </a>
                                    )}
                                  </div>
                                </li>
                              );
                            })}
                          </ul>
                        </div>
                      )}

                    {selectedNode.children &&
                      selectedNode.children.length > 0 && (
                        <div className="node-detail-section">
                          <h4>
                            Children Nodes ({selectedNode.children.length})
                          </h4>
                          <div className="node-children-list">
                            {selectedNode.children.map((childId) => {
                              const childNode = graph?.graph?.nodes?.[childId];
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
                  </>
                ) : (
                  <div className="node-detail-empty">
                    <svg
                      width="64"
                      height="64"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                    >
                      <circle cx="12" cy="12" r="10" />
                      <path d="M12 16v-4M12 8h.01" />
                    </svg>
                    <p>Select a Node to View More Details</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </section>

        {rootNodeReport && (
          <section className="final-report-panel">
            <h2>Final Research Report</h2>
            <div className="final-report-content">
              <ReactMarkdown>{rootNodeReport}</ReactMarkdown>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
