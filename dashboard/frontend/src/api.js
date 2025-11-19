/**
 * API client for the dashboard backend
 */

const API_BASE_URL = 'http://localhost:8000';

export const api = {
  /**
   * Fetch all pipeline runs
   */
  async fetchRuns() {
    const response = await fetch(`${API_BASE_URL}/api/runs`);
    if (!response.ok) {
      throw new Error('Failed to fetch runs');
    }
    return response.json();
  },

  /**
   * Fetch details for a specific run
   */
  async fetchRunDetail(runId) {
    const response = await fetch(`${API_BASE_URL}/api/runs/${runId}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch run ${runId}`);
    }
    return response.json();
  },

  /**
   * Fetch data for a specific step in a run
   */
  async fetchStepDetail(runId, stepName) {
    const response = await fetch(`${API_BASE_URL}/api/runs/${runId}/step/${stepName}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch step ${stepName}`);
    }
    return response.json();
  },

  /**
   * Start a new pipeline run
   */
  async startRun(topic, maxRetrieverCalls = 1, maxDepth = 2, maxNodes = 50, maxSubtasks = 10) {
    const response = await fetch(`${API_BASE_URL}/api/runs/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        topic,
        max_retriever_calls: maxRetrieverCalls,
        max_depth: maxDepth,
        max_nodes: maxNodes,
        max_subtasks: maxSubtasks,
      }),
    });
    if (!response.ok) {
      throw new Error('Failed to start run');
    }
    return response.json();
  },

  /**
   * Fetch the current status of a run
   */
  async fetchRunStatus(runId) {
    const response = await fetch(`${API_BASE_URL}/api/runs/${runId}/status`);
    if (!response.ok) {
      throw new Error(`Failed to fetch status for run ${runId}`);
    }
    return response.json();
  },

  /**
   * Create a WebSocket connection for real-time updates
   */
  createWebSocket(runId) {
    return new WebSocket(`ws://localhost:8000/ws/${runId}`);
  },

  /**
   * Fetch the recursive research graph for a specific run
   */
  async fetchRunGraph(runId) {
    const response = await fetch(`${API_BASE_URL}/api/runs/${runId}/graph`);
    if (!response.ok) {
      throw new Error(`Failed to fetch graph for run ${runId}`);
    }
    return response.json();
  },

  /**
   * Fetch phase status for a three-phase pipeline run
   */
  async fetchPhaseStatus(runId) {
    const response = await fetch(`${API_BASE_URL}/api/runs/${runId}/phases`);
    if (!response.ok) {
      throw new Error(`Failed to fetch phase status for run ${runId}`);
    }
    return response.json();
  },
};

