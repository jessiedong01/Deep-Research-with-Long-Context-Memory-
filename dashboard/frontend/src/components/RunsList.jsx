/**
 * Component to display a list of all pipeline runs
 */
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import './RunsList.css';

export function RunsList() {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentTime, setCurrentTime] = useState(Date.now());

  useEffect(() => {
    loadRuns();
  }, []);

  // Update current time every second for live duration counting
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(Date.now());
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const loadRuns = async () => {
    try {
      setLoading(true);
      const data = await api.fetchRuns();
      setRuns(data.runs);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleString();
  };

  const formatDuration = (run) => {
    // For running tasks, calculate live duration from created_at
    if (run.status === 'running' && run.created_at) {
      const startTime = new Date(run.created_at).getTime();
      const elapsed = Math.floor((currentTime - startTime) / 1000);
      const mins = Math.floor(elapsed / 60);
      const secs = Math.floor(elapsed % 60);
      return `${mins}m ${secs}s`;
    }
    
    // For completed/failed tasks, use the fixed duration_seconds
    if (!run.duration_seconds) return 'N/A';
    const mins = Math.floor(run.duration_seconds / 60);
    const secs = Math.floor(run.duration_seconds % 60);
    return `${mins}m ${secs}s`;
  };

  const getStatusBadge = (status) => {
    const statusClass = `status-badge status-${status.toLowerCase()}`;
    return <span className={statusClass}>{status}</span>;
  };

  if (loading) {
    return <div className="loading">Loading runs...</div>;
  }

  if (error) {
    return (
      <div className="error">
        <h3>Error loading runs</h3>
        <p>{error}</p>
        <button onClick={loadRuns}>Retry</button>
      </div>
    );
  }

  return (
    <div className="runs-list">
      <div className="runs-header">
        <h1>Pipeline Runs</h1>
        <Link to="/new" className="btn-primary">
          New Run
        </Link>
      </div>

      {runs.length === 0 ? (
        <div className="empty-state">
          <p>No pipeline runs found.</p>
          <Link to="/new" className="btn-primary">
            Start your first run
          </Link>
        </div>
      ) : (
        <div className="table-container">
          <table className="runs-table">
            <thead>
              <tr>
                <th>Status</th>
                <th>Topic</th>
                <th>Run ID</th>
                <th>Created</th>
                <th>Duration</th>
                <th>Current Step</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.run_id}>
                  <td>{getStatusBadge(run.status)}</td>
                  <td className="topic-cell" title={run.topic}>
                    {run.topic}
                  </td>
                  <td className="run-id-cell">{run.run_id}</td>
                  <td>{formatDate(run.created_at)}</td>
                  <td>
                    <div className="duration-cell">
                      {formatDuration(run)}
                      {run.status === 'running' && (
                        <span className="duration-spinner"></span>
                      )}
                    </div>
                  </td>
                  <td>{run.current_step || 'N/A'}</td>
                  <td>
                    <Link to={`/runs/${run.run_id}`} className="btn-link">
                      View Details
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

