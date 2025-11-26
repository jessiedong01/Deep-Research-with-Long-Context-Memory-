/**
 * Component to start a new pipeline run
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useWebSocket } from "../hooks/useWebSocket";
import { RecursiveGraphTree } from "./RecursiveGraphTree";
import "./NewRunForm.css";

export function NewRunForm() {
  const navigate = useNavigate();
  const [topic, setTopic] = useState("");
  const [maxRetrieverCalls, setMaxRetrieverCalls] = useState(1);
  const [maxDepth, setMaxDepth] = useState(2);
  const [maxNodes, setMaxNodes] = useState(50);
  const [maxSubtasks, setMaxSubtasks] = useState(10);
  const [maxRefinements, setMaxRefinements] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [runId, setRunId] = useState(null);
  const [savedDags, setSavedDags] = useState([]);
  const [savedDagsLoading, setSavedDagsLoading] = useState(true);
  const [savedDagError, setSavedDagError] = useState(null);
  const [selectedDagPath, setSelectedDagPath] = useState("");
  const [selectedDagFilename, setSelectedDagFilename] = useState("");
  const [dagPreview, setDagPreview] = useState(null);
  const [dagPreviewLoading, setDagPreviewLoading] = useState(false);
  const [dagPreviewError, setDagPreviewError] = useState(null);

  const { messages, isConnected } = useWebSocket(runId);

  useEffect(() => {
    let cancelled = false;
    async function loadSavedDags() {
      try {
        const data = await api.fetchSavedDags();
        if (!cancelled) {
          setSavedDags(data?.dags || []);
          setSavedDagError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setSavedDagError(err.message || "Failed to load saved DAGs");
        }
      } finally {
        if (!cancelled) {
          setSavedDagsLoading(false);
        }
      }
    }
    loadSavedDags();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    if (!selectedDagFilename) {
      setDagPreview(null);
      setDagPreviewError(null);
      setDagPreviewLoading(false);
      return;
    }
    async function loadPreview() {
      setDagPreviewLoading(true);
      setDagPreviewError(null);
      try {
        const data = await api.fetchSavedDagGraph(selectedDagFilename);
        if (!cancelled) setDagPreview(data);
      } catch (err) {
        if (!cancelled) {
          setDagPreviewError(err.message || "Failed to load DAG preview");
          setDagPreview(null);
        }
      } finally {
        if (!cancelled) setDagPreviewLoading(false);
      }
    }
    loadPreview();
    return () => {
      cancelled = true;
    };
  }, [selectedDagFilename]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!topic.trim()) {
      setError("Please enter a research topic");
      return;
    }
    try {
      setIsSubmitting(true);
      setError(null);
      const response = await api.startRun(
        topic,
        maxRetrieverCalls,
        maxDepth,
        maxNodes,
        maxSubtasks,
        maxRefinements,
        selectedDagPath || null
      );
      setRunId(response.run_id);
      setTimeout(() => navigate(`/runs/${response.run_id}`), 2000);
    } catch (err) {
      setError(err.message);
      setIsSubmitting(false);
    }
  };

  const latestStatus =
    messages.length > 0 ? messages[messages.length - 1] : null;

  // Rendering helpers
  const renderDagSelector = () => (
    <div className="form-group">
      <label htmlFor="savedDagSelect">Use a Saved Test DAG (optional)</label>
      {savedDagsLoading ? (
        <p className="muted">Loading saved DAGs...</p>
      ) : (
        <select
          id="savedDagSelect"
          className="dag-select"
          value={selectedDagPath}
          onChange={(e) => {
            const value = e.target.value;
            setSelectedDagPath(value);
            if (value) {
              const selected = savedDags.find((d) => d.path === value);
              setSelectedDagFilename(selected?.filename || "");
              if (selected?.topic) setTopic(selected.topic);
            } else {
              setSelectedDagFilename("");
            }
          }}
          disabled={isSubmitting || savedDags.length === 0}
        >
          <option value="">Generate a new DAG</option>
          {savedDags.map((dag) => (
            <option key={dag.path} value={dag.path}>
              {dag.timestamp || dag.filename} — {dag.topic || "Untitled"} (
              {dag.total_nodes ?? "?"} nodes)
            </option>
          ))}
        </select>
      )}
      {savedDagError && <p className="error-text">{savedDagError}</p>}
      <p className="muted">
        Selecting a saved DAG skips Phase 1 and reuses the decomposition from
        the Test DAG page.
      </p>
    </div>
  );

  const renderConfigFields = () => (
    <>
      <div className="form-group">
        <label htmlFor="topic">Research Topic *</label>
        <textarea
          id="topic"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="Enter your research question or topic..."
          rows={3}
          required
          disabled={isSubmitting}
        />
      </div>
      <div className="form-row">
        <div className="form-group small">
          <label htmlFor="maxRetrieverCalls">Max Retriever Calls</label>
          <input
            type="number"
            id="maxRetrieverCalls"
            value={maxRetrieverCalls}
            onChange={(e) =>
              setMaxRetrieverCalls(parseInt(e.target.value, 10) || 1)
            }
            min={1}
            max={20}
            disabled={isSubmitting}
          />
        </div>
        <div className="form-group small">
          <label htmlFor="maxDepth">Max Depth</label>
          <input
            type="number"
            id="maxDepth"
            value={maxDepth}
            onChange={(e) => setMaxDepth(parseInt(e.target.value, 10) || 0)}
            min={0}
            max={5}
            disabled={isSubmitting}
          />
        </div>
        <div className="form-group small">
          <label htmlFor="maxNodes">Max Nodes</label>
          <input
            type="number"
            id="maxNodes"
            value={maxNodes}
            onChange={(e) => setMaxNodes(parseInt(e.target.value, 10) || 1)}
            min={1}
            max={200}
            disabled={isSubmitting}
          />
        </div>
        <div className="form-group small">
          <label htmlFor="maxSubtasks">Max Subtasks</label>
          <input
            type="number"
            id="maxSubtasks"
            value={maxSubtasks}
            onChange={(e) => setMaxSubtasks(parseInt(e.target.value, 10) || 1)}
            min={1}
            max={20}
            disabled={isSubmitting}
          />
        </div>
        <div className="form-group small">
          <label htmlFor="maxRefinements">Max Refinements</label>
          <input
            type="number"
            id="maxRefinements"
            value={maxRefinements}
            onChange={(e) =>
              setMaxRefinements(parseInt(e.target.value, 10) || 0)
            }
            min={0}
            max={5}
            disabled={isSubmitting}
          />
        </div>
      </div>
    </>
  );

  const renderDagPreview = () => {
    if (!selectedDagPath) return null;
    return (
      <section className="dag-preview-section">
        <header className="dag-preview-header">
          <h2>DAG Preview</h2>
          {dagPreview?.metadata?.topic && <p>{dagPreview.metadata.topic}</p>}
          {dagPreview?.metadata?.total_nodes != null && (
            <span className="pill">
              {dagPreview.metadata.total_nodes} nodes
            </span>
          )}
        </header>
        <div className="dag-preview-graph">
          {dagPreviewLoading ? (
            <p className="muted center">Loading preview...</p>
          ) : dagPreviewError ? (
            <p className="error-text center">{dagPreviewError}</p>
          ) : dagPreview?.graph ? (
            <RecursiveGraphTree graph={dagPreview.graph} />
          ) : (
            <p className="muted center">No preview available</p>
          )}
        </div>
      </section>
    );
  };

  const renderSubmittingState = () => (
    <div className="submitting-state">
      <div className="spinner" />
      <h2>Pipeline Starting...</h2>
      <p>
        Run ID: <code>{runId}</code>
      </p>
      {isConnected && (
        <div className="connection-badge">
          <span className="dot" />
          Connected
        </div>
      )}
      {latestStatus && (
        <div className="latest-update">
          <strong>{latestStatus.type}:</strong>{" "}
          {latestStatus.data?.message || JSON.stringify(latestStatus.data)}
        </div>
      )}
      {messages.length > 0 && (
        <div className="activity-log">
          <h3>Activity Log</h3>
          <ul>
            {messages.slice(-8).map((msg, idx) => (
              <li key={idx}>
                <span className="time">
                  {new Date(msg.timestamp).toLocaleTimeString()}
                </span>
                <span className="type">{msg.type}</span>
                <span className="text">
                  {msg.data?.message || JSON.stringify(msg.data)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
      <p className="muted">Redirecting to run details shortly...</p>
    </div>
  );

  return (
    <div className={`new-run-page ${selectedDagPath ? "with-preview" : ""}`}>
      {isSubmitting ? (
        renderSubmittingState()
      ) : (
        <>
          <div className="form-panel">
            <h1>Start New Pipeline Run</h1>
            <form onSubmit={handleSubmit} className="run-form">
              {renderDagSelector()}
              {!selectedDagPath && renderConfigFields()}
              {error && <p className="error-text">{error}</p>}
              <div className="form-actions">
                <button
                  type="button"
                  className="btn secondary"
                  onClick={() => navigate("/")}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn primary"
                  disabled={isSubmitting}
                >
                  Start Pipeline
                </button>
              </div>
            </form>
          </div>
          {renderDagPreview()}
        </>
      )}
    </div>
  );
}
