/**
 * Component to start a new pipeline run
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useWebSocket } from '../hooks/useWebSocket';
import './NewRunForm.css';

export function NewRunForm() {
  const navigate = useNavigate();
  const [topic, setTopic] = useState('');
  const [maxRetrieverCalls, setMaxRetrieverCalls] = useState(1);
  const [maxDepth, setMaxDepth] = useState(2);
  const [maxNodes, setMaxNodes] = useState(50);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [runId, setRunId] = useState(null);
  
  const { messages, isConnected } = useWebSocket(runId);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!topic.trim()) {
      setError('Please enter a research topic');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      
      const response = await api.startRun(
        topic,
        maxRetrieverCalls,
        maxDepth,
        maxNodes
      );
      setRunId(response.run_id);
      
      // After a brief delay, redirect to the run detail page
      setTimeout(() => {
        navigate(`/runs/${response.run_id}`);
      }, 2000);
      
    } catch (err) {
      setError(err.message);
      setIsSubmitting(false);
    }
  };

  const getLatestStatus = () => {
    if (messages.length === 0) return null;
    const latestMessage = messages[messages.length - 1];
    return latestMessage;
  };

  const latestStatus = getLatestStatus();

  return (
    <div className="new-run-form-container">
      <div className="new-run-form-card">
        <h1>Start New Pipeline Run</h1>
        
        {!isSubmitting ? (
          <form onSubmit={handleSubmit} className="new-run-form">
            <div className="form-group">
              <label htmlFor="topic">Research Topic *</label>
              <textarea
                id="topic"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="Enter your research question or topic..."
                rows={4}
                required
                disabled={isSubmitting}
              />
              <span className="form-help">
                What would you like the pipeline to research?
              </span>
            </div>

            <div className="form-group">
              <label htmlFor="maxRetrieverCalls">
                Max Retriever Calls
              </label>
              <input
                type="number"
                id="maxRetrieverCalls"
                value={maxRetrieverCalls}
                onChange={(e) => setMaxRetrieverCalls(parseInt(e.target.value, 10))}
                min={1}
                max={20}
                disabled={isSubmitting}
              />
              <span className="form-help">
                Maximum number of retrieval operations (1-20)
              </span>
            </div>

            <div className="form-group">
              <label htmlFor="maxDepth">
                Max Recursion Depth
              </label>
              <input
                type="number"
                id="maxDepth"
                value={maxDepth}
                onChange={(e) =>
                  setMaxDepth(
                    Number.isNaN(parseInt(e.target.value, 10))
                      ? 0
                      : parseInt(e.target.value, 10)
                  )
                }
                min={0}
                max={5}
                disabled={isSubmitting}
              />
              <span className="form-help">
                How many levels of subtask decomposition (0 = no subtasks).
              </span>
            </div>

            <div className="form-group">
              <label htmlFor="maxNodes">
                Max DAG Nodes
              </label>
              <input
                type="number"
                id="maxNodes"
                value={maxNodes}
                onChange={(e) =>
                  setMaxNodes(
                    Number.isNaN(parseInt(e.target.value, 10))
                      ? 1
                      : parseInt(e.target.value, 10)
                  )
                }
                min={1}
                max={200}
                disabled={isSubmitting}
              />
              <span className="form-help">
                Global cap on number of research tasks explored in the DAG.
              </span>
            </div>

            {error && (
              <div className="form-error">
                <strong>Error:</strong> {error}
              </div>
            )}

            <div className="form-actions">
              <button
                type="button"
                onClick={() => navigate('/')}
                className="btn-secondary"
                disabled={isSubmitting}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn-primary"
                disabled={isSubmitting}
              >
                Start Pipeline
              </button>
            </div>
          </form>
        ) : (
          <div className="pipeline-starting">
            <div className="spinner"></div>
            <h2>Pipeline Starting...</h2>
            <p>Run ID: <code>{runId}</code></p>
            
            {isConnected && (
              <div className="connection-status">
                <span className="status-indicator connected"></span>
                Connected to pipeline
              </div>
            )}

            {latestStatus && (
              <div className="latest-status">
                <h3>Latest Update:</h3>
                <div className="status-message">
                  <span className="status-type">{latestStatus.type}</span>
                  {latestStatus.data?.message && (
                    <span className="status-text">{latestStatus.data.message}</span>
                  )}
                </div>
              </div>
            )}

            {messages.length > 0 && (
              <div className="log-messages">
                <h3>Activity Log:</h3>
                <div className="log-list">
                  {messages.slice(-10).map((msg, idx) => (
                    <div key={idx} className={`log-entry log-${msg.type}`}>
                      <span className="log-time">
                        {new Date(msg.timestamp).toLocaleTimeString()}
                      </span>
                      <span className="log-type">{msg.type}</span>
                      <span className="log-message">
                        {msg.data?.message || JSON.stringify(msg.data)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <p className="redirect-notice">
              You will be redirected to the run details page shortly...
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

