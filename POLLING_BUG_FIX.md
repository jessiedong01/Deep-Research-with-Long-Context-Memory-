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

Added two new status detection mechanisms:

```python
# Check if recursive_graph.json exists - indicates recursive pipeline completion
elif (run_dir / "recursive_graph.json").exists():
    status = RunStatus.COMPLETED
    completed_at = datetime.fromisoformat(last_log['timestamp'])

# Check if run is stale (no updates in last 10 minutes) - mark as failed
else:
    last_update = datetime.fromisoformat(last_log['timestamp'])
    time_since_update = datetime.now() - last_update
    if time_since_update.total_seconds() > 600:  # 10 minutes
        status = RunStatus.FAILED
        completed_at = last_update
```

**Benefits:**
- Properly detects completion of recursive pipeline runs
- Automatically marks stale runs as failed after 10 minutes of inactivity
- Prevents infinite polling of abandoned runs

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

