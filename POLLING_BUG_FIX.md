# Polling Bug Fix

## Problem Description

The dashboard had a bug where API calls would continue after a pipeline finished or failed, causing:
1. Continuous polling of completed or stale runs
2. Repeated 404 errors for runs without graph data
3. Unnecessary server load and log spam

## Root Causes

### 1. **Incomplete Run Detection**
The scanner (`scanner.py`) failed to detect when runs completed or became stale:
- Only checked for `05_final_report.json` (old pipeline structure)
- Didn't recognize `recursive_graph.json` (new recursive pipeline)
- Didn't detect abandoned/crashed runs (no updates for extended periods)

### 2. **Aggressive Graph Polling**
The frontend (`RunDetail.jsx`) would:
- Poll for graph data every 5 seconds while run status is "running"
- Continue polling even after receiving 404 errors
- Never cache 404 responses to avoid repeated failures

### 3. **Stale Run Status**
Runs that crashed or were interrupted would remain in "running" state indefinitely, causing the frontend to poll forever.

## Solutions Implemented

### Backend Fix: Scanner Status Detection

**File:** `dashboard/backend/scanner.py`

**Issue Found:** The initial fix incorrectly checked for `recursive_graph.json` existence immediately, but this file is created at the START of every run (for real-time updates), causing runs to be prematurely marked as completed.

**Updated Fix:** Reordered status detection logic to prioritize explicit completion messages and time-based checks:

```python
last_update = datetime.fromisoformat(last_log['timestamp'])
time_since_update = datetime.now() - last_update

# Check if pipeline completed successfully (most reliable indicator)
if any("Pipeline completed successfully" in log.get('message', '') for log in log_lines):
    status = RunStatus.COMPLETED
    completed_at = datetime.fromisoformat(last_log['timestamp'])
# Check if there's an error
elif any("error" in log.get('level', '').lower() for log in log_lines):
    status = RunStatus.FAILED
    completed_at = datetime.fromisoformat(last_log['timestamp'])
# Check if run is stale (no updates in last 10 minutes) - mark as failed
elif time_since_update.total_seconds() > 600:  # 10 minutes
    status = RunStatus.FAILED
    completed_at = last_update
# For older runs (>2 minutes since last update), check if final files exist
# This handles cases where completion message was missed but run finished
elif time_since_update.total_seconds() > 120:  # 2 minutes
    if (run_dir / "05_final_report.json").exists() or (run_dir / "recursive_graph.json").exists():
        status = RunStatus.COMPLETED
        completed_at = last_update
# Otherwise, keep as RUNNING (recursive_graph.json is created at start for real-time updates)
```

**Benefits:**
- Prioritizes explicit completion messages over file existence
- Automatically marks stale runs as failed after 10 minutes of inactivity
- Only uses file-based completion detection for runs idle >2 minutes
- Prevents premature completion detection for active runs
- Allows real-time graph updates without affecting run status

### Frontend Fix: Smart Graph Polling

**File:** `dashboard/frontend/src/components/RunDetail.jsx`

Added 404 tracking to avoid repeated graph requests:

```javascript
const [graphNotFound, setGraphNotFound] = useState(false);

// In polling logic:
if (runDetail?.metadata?.status === "running") {
  const interval = setInterval(() => {
    loadRunDetail();
    // Only retry loading graph if we haven't received a 404
    if (!graphNotFound) {
      loadGraph();
    }
  }, 5000);
}

// In loadGraph:
catch (err) {
  setGraphError(err.message);
  // If it's a 404, mark graph as not found to avoid retrying
  if (err.message.includes("404") || err.message.includes("not found")) {
    setGraphNotFound(true);
  }
}
```

**Benefits:**
- Stops polling for graphs that don't exist
- Reduces 404 errors and server load
- Resets state when navigating to different runs

## Testing

To verify the fixes work:

1. **Stale Run Detection:**
   - Run `20251117_000007` should now show as "failed" instead of "running"
   - Frontend should stop polling after status changes to "failed"

2. **Completed Run Detection:**
   - Runs `20251117_001016` and `20251117_002743` should show as "completed"
   - Frontend should stop polling once status is "completed"

3. **404 Handling:**
   - Viewing a run without a graph should show error message
   - No repeated 404 requests in server logs
   - Polling continues for run status but not graph data

## Impact

- **Server Load:** Significantly reduced API call volume
- **Log Clarity:** Eliminated spam from repeated 404 errors
- **User Experience:** Accurate status display for all runs
- **Resource Usage:** Reduced unnecessary WebSocket connections and polling

## Future Improvements

1. Consider adding a "cancelled" status for manually stopped runs
2. Make the stale timeout configurable (currently hardcoded to 10 minutes)
3. Add backend cleanup to archive old runs after a certain period
4. Implement exponential backoff for transient errors vs. giving up on 404s

