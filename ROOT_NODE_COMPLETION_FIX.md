# Root Node Completion Status Fix

## Problem

The frontend dashboard was incorrectly marking research tasks as "Complete" even though the recursive research tree had not been fully explored. This occurred because the backend's status detection logic was flawed.

### Root Cause

In `dashboard/backend/scanner.py`, the `_parse_run_directory` method determined run completion status as follows:

```python
# OLD BUGGY CODE (lines 105-108)
elif time_since_update.total_seconds() > 120:  # 2 minutes
    if (run_dir / "05_final_report.json").exists() or (run_dir / "recursive_graph.json").exists():
        status = RunStatus.COMPLETED
        completed_at = last_update
```

**The bug**: The logic marked a run as `COMPLETED` if `recursive_graph.json` existed, but this file is created at the **start** of the run and updated throughout execution for real-time visualization. Simply checking for file existence is insufficient.

### Example

Run `20251117_012840` had:

- ✅ `recursive_graph.json` file exists
- ❌ Root node status: `"in_progress"` (not complete)
- ❌ Tree not fully explored
- **Result**: Incorrectly marked as "Complete" ❌

## Solution

The fix checks the **actual status of the root node** in the recursive graph, not just whether the file exists.

### Changes Made

1. **Added `_is_root_node_completed` method** (lines 60-93):

   - Reads and parses `recursive_graph.json`
   - Extracts the root node from the graph
   - Checks if root node status is `"complete"` or `"completed"`
   - Returns `False` if file missing, unparseable, or root incomplete

2. **Updated status detection logic** (lines 138-144):
   ```python
   # NEW FIXED CODE
   elif time_since_update.total_seconds() > 120:  # 2 minutes
       # Check if the root node in recursive_graph.json is completed
       if self._is_root_node_completed(run_dir):
           status = RunStatus.COMPLETED
           completed_at = last_update
   ```

### Algorithm

The new `_is_root_node_completed` method:

1. Checks if `recursive_graph.json` exists
2. Parses the JSON structure
3. Extracts `data.root_id` and `data.nodes`
4. Retrieves the root node using `nodes[root_id]`
5. Checks if `root_node.status.lower()` is in `['complete', 'completed']`
6. Returns `True` only if root is genuinely complete

## Verification

Tested with actual log data:

| Run ID          | Root Status   | Completion Message | Correctly Marked |
| --------------- | ------------- | ------------------ | ---------------- |
| 20251117_012840 | `in_progress` | ❌ No              | ✅ RUNNING       |
| 20251117_011417 | `complete`    | ✅ Yes             | ✅ COMPLETED     |
| 20251117_005039 | `complete`    | ✅ Yes             | ✅ COMPLETED     |
| 20251117_002743 | `complete`    | ✅ Yes             | ✅ COMPLETED     |

## Impact

- ✅ Tasks only marked "Complete" when root node is actually finished
- ✅ Real-time status accurately reflects tree exploration progress
- ✅ Prevents premature completion marking
- ✅ Maintains correct status for in-progress recursive research

## Files Modified

- `dashboard/backend/scanner.py`:
  - Added `_is_root_node_completed()` method
  - Updated status detection logic in `_parse_run_directory()`
