/**
 * Component to display detailed information about a pipeline run,
 * including an interactive visualization of the recursive research tree.
 */
import { useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api";
import { useWebSocket } from "../hooks/useWebSocket";
import { RecursiveGraphTree } from "./RecursiveGraphTree";
import "./RunDetail.css";

export function RunDetail() {
  const { runId } = useParams();
  const [runDetail, setRunDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [graph, setGraph] = useState(null);
  const [graphLoading, setGraphLoading] = useState(false);
  const [graphError, setGraphError] = useState(null);
  const [error, setError] = useState(null);

  // Connect WebSocket for real-time updates if run is active
  const { messages } = useWebSocket(
    runDetail?.metadata?.status === "running" ? runId : null
  );

  // Poll for updates if the run is in progress
  useEffect(() => {
    if (runDetail?.metadata?.status === "running") {
      const interval = setInterval(() => {
        loadRunDetail();
        loadGraph();
      }, 5000); // Refresh every 5 seconds

      return () => clearInterval(interval);
    }
  }, [runDetail?.metadata?.status]);

  useEffect(() => {
    loadRunDetail();
    loadGraph();
  }, [runId]);

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
    } catch (err) {
      console.error("Error loading graph:", err);
      setGraph(null);
      setGraphError(err.message);
    } finally {
      setGraphLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "N/A";
    const date = new Date(dateStr);
    return date.toLocaleString();
  };

  const formatDuration = (seconds) => {
    if (!seconds) return "N/A";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}m ${secs}s`;
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
        typeof node.status === "string"
          ? node.status.toLowerCase()
          : "pending";
      if (status === "complete" || status === "completed") {
        if (depth > bestDepth) {
          bestDepth = depth;
          bestId = node.id || bestId;
        }
      }
    }

    return bestId;
  }, [graph, runDetail?.metadata?.status]);

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
            {runDetail.metadata.status === "running" && (
              <span className="live-indicator">
                <span className="pulse"></span>
                Live - Updating every 5s
              </span>
            )}
            <span className="run-id">Run ID: {runDetail.metadata.run_id}</span>
            <span>Created: {formatDate(runDetail.metadata.created_at)}</span>
            <span>
              Duration: {formatDuration(runDetail.metadata.duration_seconds)}
            </span>
            {typeof runDetail.metadata.max_retriever_calls === "number" && (
              <span>
                Max Retriever Calls: {runDetail.metadata.max_retriever_calls}
              </span>
            )}
            {typeof runDetail.metadata.max_depth === "number" && (
              <span>Max Depth: {runDetail.metadata.max_depth}</span>
            )}
            {typeof runDetail.metadata.max_nodes === "number" && (
              <span>Max Nodes: {runDetail.metadata.max_nodes}</span>
            )}
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
              <span className="value">
                {formatDuration(runDetail.metadata.duration_seconds)}
              </span>
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
            {graph?.metadata && (
              <>
                {typeof graph.metadata.total_nodes === "number" && (
                  <div className="run-summary-item">
                    <span className="label">Graph Nodes</span>
                    <span className="value">
                      {graph.metadata.total_nodes}
                    </span>
                  </div>
                )}
                {typeof graph.metadata.max_depth === "number" && (
                  <div className="run-summary-item">
                    <span className="label">Graph Max Depth</span>
                    <span className="value">
                      {graph.metadata.max_depth}
                    </span>
                  </div>
                )}
              </>
            )}
          </div>

          <div className="current-node-card">
            <h3>Current Node</h3>
            {graph && derivedCurrentNodeId && graph.graph?.nodes ? (
              (() => {
                const node = graph.graph.nodes[derivedCurrentNodeId];
                if (!node) {
                  return <p className="current-node-empty">Unknown node.</p>;
                }
                const status =
                  typeof node.status === "string"
                    ? node.status.toLowerCase()
                    : "pending";
                return (
                  <div className="current-node-details">
                    <div className="current-node-title">{node.question}</div>
                    <div className="current-node-meta">
                      <span>Node ID: {node.id}</span>
                      <span>Depth: {node.depth ?? 0}</span>
                      <span>Status: {status}</span>
                      {typeof node.is_answerable === "boolean" && (
                        <span>
                          Answerable:{" "}
                          {node.is_answerable ? "Yes" : "No"}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })()
            ) : graphLoading ? (
              <p className="current-node-empty">Loading graph...</p>
            ) : (
              <p className="current-node-empty">
                Current node information is not available yet.
              </p>
            )}
          </div>
        </section>

        <section className="run-graph-panel">
          <h2>Recursive Research Tree</h2>
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
            />
          )}
        </section>
      </div>
    </div>
  );
}
