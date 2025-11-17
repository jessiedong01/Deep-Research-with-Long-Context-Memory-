/**
 * Component to display detailed information about a pipeline run
 */
import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api";
import { StepViewer } from "./StepViewer";
import { useWebSocket } from "../hooks/useWebSocket";
import "./RunDetail.css";

export function RunDetail() {
  const { runId } = useParams();
  const [runDetail, setRunDetail] = useState(null);
  const [selectedStep, setSelectedStep] = useState(null);
  const [stepData, setStepData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [stepLoading, setStepLoading] = useState(false);
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
      }, 5000); // Refresh every 5 seconds

      return () => clearInterval(interval);
    }
  }, [runDetail?.metadata?.status]);

  useEffect(() => {
    loadRunDetail();
  }, [runId]);

  useEffect(() => {
    if (selectedStep) {
      loadStepData(selectedStep.step_name);
    }
  }, [selectedStep]);

  const loadRunDetail = async () => {
    try {
      setLoading(true);
      const data = await api.fetchRunDetail(runId);
      setRunDetail(data);

      // Select first completed step by default
      const firstCompletedStep = data.steps.find(
        (step) => step.status === "completed"
      );
      if (firstCompletedStep) {
        setSelectedStep(firstCompletedStep);
      } else if (data.steps.length > 0) {
        setSelectedStep(data.steps[0]);
      }

      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadStepData = async (stepName) => {
    try {
      setStepLoading(stepName); // Store which step is loading

      // Fetch data and ensure minimum display time for spinner
      const [data] = await Promise.all([
        api.fetchStepDetail(runId, stepName),
        new Promise((resolve) => setTimeout(resolve, 300)), // Minimum 300ms to see spinner
      ]);

      setStepData(data);
    } catch (err) {
      console.error("Error loading step data:", err);
      setStepData(null);
    } finally {
      setStepLoading(false);
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
          </div>
        </div>
      </div>

      <div className="run-detail-content">
        <aside className="steps-sidebar">
          <h2>Pipeline Steps</h2>
          <nav className="steps-nav">
            {runDetail.steps.map((step, idx) => (
              <button
                key={step.step_name}
                className={`step-nav-item ${
                  selectedStep?.step_name === step.step_name ? "active" : ""
                } status-${step.status} ${
                  stepLoading === step.step_name ? "clicking-loading" : ""
                }`}
                onClick={() => setSelectedStep(step)}
                disabled={step.status === "pending"}
              >
                <span className="step-icon">
                  {step.status === "in_progress" ||
                  stepLoading === step.step_name ? (
                    <span className="step-spinner"></span>
                  ) : (
                    getStepStatusIcon(step.status)
                  )}
                </span>
                <div className="step-info">
                  <div className="step-number">Step {step.step_number}</div>
                  <div className="step-name">
                    {step.step_name.replace(/^\d+_/, "").replace(/_/g, " ")}
                  </div>
                </div>
              </button>
            ))}
          </nav>

          <div className="timeline">
            <h3>Timeline</h3>
            <div className="timeline-items">
              {runDetail.steps
                .filter((step) => step.timestamp)
                .map((step) => (
                  <div key={step.step_name} className="timeline-item">
                    <div className="timeline-time">
                      {new Date(step.timestamp).toLocaleTimeString()}
                    </div>
                    <div className="timeline-label">
                      {step.step_name.replace(/^\d+_/, "").replace(/_/g, " ")}
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </aside>

        <main className="step-content-area">
          {stepLoading && typeof stepLoading === "string" ? (
            <div className="loading">
              <div className="spinner"></div>
              <p>Loading step data...</p>
            </div>
          ) : selectedStep && stepData ? (
            <StepViewer stepData={stepData.data} stepInfo={selectedStep} />
          ) : selectedStep?.status === "pending" ? (
            <div className="pending-message">
              <p>⏳ This step hasn't started yet.</p>
              {runDetail?.metadata?.status === "running" && (
                <p className="hint">
                  The pipeline is still running. This page will update
                  automatically.
                </p>
              )}
            </div>
          ) : (
            <div className="loading">Loading step data...</div>
          )}
        </main>
      </div>
    </div>
  );
}
