import { useMemo, useState } from 'react';
import { api } from '../api';
import { RecursiveGraphTree } from './RecursiveGraphTree';
import './DAGTestPage.css';

export function DAGTestPage() {
  const [topic, setTopic] = useState('');
  const [maxDepth, setMaxDepth] = useState(2);
  const [maxNodes, setMaxNodes] = useState(30);
  const [maxSubtasks, setMaxSubtasks] = useState(5);
  const [graphResponse, setGraphResponse] = useState(null);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!topic.trim()) {
      setError('Please enter a research question.');
      return;
    }

    setLoading(true);
    setError(null);
    setGraphResponse(null);
    setSelectedNodeId(null);

    try {
      const response = await api.generateTestDag(
        topic.trim(),
        Number(maxDepth),
        Number(maxNodes),
        Number(maxSubtasks)
      );
      setGraphResponse(response);
      const rootId = response?.graph?.root_id;
      if (rootId) {
        setSelectedNodeId(rootId);
      }
    } catch (err) {
      setError(err.message || 'Failed to generate DAG.');
    } finally {
      setLoading(false);
    }
  };

  const graphData = graphResponse?.graph;
  const nodeMap = graphData?.nodes || {};

  const selectedNode = useMemo(() => {
    if (!selectedNodeId) return null;
    return nodeMap[selectedNodeId] || null;
  }, [nodeMap, selectedNodeId]);

  const handleNodeClick = (node) => {
    if (!node?.id) {
      return;
    }
    setSelectedNodeId(node.id);
  };

  const handleChildSelect = (nodeId) => {
    if (nodeId) {
      setSelectedNodeId(nodeId);
    }
  };

  const metadata = graphResponse?.metadata || {};

  return (
    <div className="dag-test-page">
      <div className="dag-form-card">
        <h1>DAG Generation Sandbox</h1>
        <p className="helper-text">
          Generate a planning DAG directly from the new single-shot phase. Use this page to
          iterate on prompts and constraints before running the full pipeline.
        </p>

        <form className="dag-form" onSubmit={handleSubmit}>
          <label>
            Research question
            <textarea
              value={topic}
              onChange={(event) => setTopic(event.target.value)}
              placeholder="e.g., How can advanced battery chemistries accelerate grid-scale storage deployments?"
              rows={4}
              required
            />
          </label>

          <div className="form-grid">
            <label>
              Max depth
              <input
                type="number"
                min={1}
                max={5}
                value={maxDepth}
                onChange={(event) => setMaxDepth(event.target.value)}
              />
            </label>
            <label>
              Max nodes
              <input
                type="number"
                min={1}
                max={100}
                value={maxNodes}
                onChange={(event) => setMaxNodes(event.target.value)}
              />
            </label>
            <label>
              Max subtasks
              <input
                type="number"
                min={1}
                max={10}
                value={maxSubtasks}
                onChange={(event) => setMaxSubtasks(event.target.value)}
              />
            </label>
          </div>

          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Generating...' : 'Generate DAG'}
          </button>
        </form>

        {error && <div className="error-banner">{error}</div>}
      </div>

      {graphResponse && (
        <div className="dag-result-card">
          <div className="result-header">
            <div>
              <h2>Generated Tree</h2>
              <p className="helper-text">
                {metadata.total_nodes || 0} nodes • Requested depth {metadata.max_depth_requested} • Requested nodes {metadata.max_nodes_requested}
              </p>
            </div>
            <div className="metadata-badges">
              <span className="badge">Source: {metadata.graph_source || 'test_dag_generation'}</span>
            </div>
          </div>

          <div className="dag-result-body">
            <div className="dag-graph-flow">
              <RecursiveGraphTree
                graph={graphResponse.graph}
                currentNodeId={selectedNodeId}
                onNodeClick={handleNodeClick}
              />
            </div>

            <div className="dag-node-details">
              <div className="node-detail-header">
                <h3>Node Details</h3>
                {selectedNode && (
                  <button
                    className="close-detail-button"
                    onClick={() => setSelectedNodeId(null)}
                    type="button"
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
                        {selectedNode.question || selectedNode.id}
                      </p>
                    </div>

                    {selectedNode.composition_instructions && (
                      <div className="node-detail-section">
                        <h4>Composition Instructions</h4>
                        <p>{selectedNode.composition_instructions}</p>
                      </div>
                    )}

                    {Array.isArray(selectedNode.children) &&
                      selectedNode.children.length > 0 && (
                        <div className="node-detail-section">
                          <h4>
                            Children ({selectedNode.children.length})
                          </h4>
                          <div className="node-children-list">
                            {selectedNode.children.map((childId) => (
                              <button
                                key={childId}
                                className="child-node-button"
                                type="button"
                                onClick={() => handleChildSelect(childId)}
                              >
                                {nodeMap[childId]?.question || childId}
                              </button>
                            ))}
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
                    <p>Select a node in the tree to inspect its details.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
