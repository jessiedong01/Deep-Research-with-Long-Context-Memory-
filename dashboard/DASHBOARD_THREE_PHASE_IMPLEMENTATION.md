# Dashboard Three-Phase Pipeline Implementation

## Overview

Successfully implemented dashboard support for the new three-phase research pipeline architecture. The dashboard now displays and visualizes the three distinct phases: DAG Generation, DAG Processing, and Report Generation.

## Backend Changes

### 1. Data Models (`dashboard/backend/models.py`)

**Added:**
- `PipelinePhase` enum with values: `DAG_GENERATION`, `DAG_PROCESSING`, `REPORT_GENERATION`
- `PhaseInfo` model for phase-specific information (status, timestamps, metrics)
- `PhaseStatusResponse` model for phase status API responses

**Updated `RunMetadata`:**
- Added `current_phase: Optional[PipelinePhase]`
- Added `phases_complete: list[PipelinePhase]`
- Added `is_three_phase: bool` flag to distinguish new vs legacy runs

**Updated `WebSocketMessage`:**
- Extended type to include `"phase_transition"` events

### 2. Scanner (`dashboard/backend/scanner.py`)

**Added Methods:**
- `_detect_three_phase_run()` - Detects if a run uses the new three-phase architecture
- `_detect_phases()` - Returns current phase and list of completed phases

**Updated Methods:**
- `_parse_run_directory()` - Now detects and sets phase information
- `_parse_steps()` - Recognizes new step files:
  - `00_dag_generation.json`
  - `01_dag_processed.json`
  - `02_final_report.json`

**Phase Detection Logic:**
- Checks for presence of new phase step files
- Determines current phase based on completed steps
- Maintains backward compatibility with legacy runs

### 3. API Endpoints (`dashboard/backend/api.py`)

**New Endpoint:**
```python
GET /api/runs/{run_id}/phases
```
Returns `PhaseStatusResponse` with:
- Current phase
- List of completed phases with metrics
- Phase timestamps and durations

**Updated Endpoint:**
```python
GET /api/runs/{run_id}/status
```
Now includes phase information for three-phase runs:
- `is_three_phase`
- `current_phase`
- `phases_complete`

## Frontend Changes

### 4. New Component: PhaseProgress (`PhaseProgress.jsx`)

**Features:**
- Visual three-step progress indicator
- Shows completion status for each phase (pending/in-progress/completed)
- Displays phase-specific metrics:
  - **Phase 1:** Total nodes, max depth, leaf nodes
  - **Phase 2:** Nodes completed/total
  - **Phase 3:** Citation count
- Animated progress indicators
- Responsive design for mobile

**Styling (`PhaseProgress.css`):**
- Color-coded phases (green=completed, blue=in-progress, gray=pending)
- Animated pulse effect for active phase
- Connector lines between phases

### 5. Updated Component: RecursiveGraphTree (`RecursiveGraphTree.jsx`)

**Changes:**
- **Removed:** `is_answerable` field references
- **Added:** `expected_output_format` display with icons:
  - 🔲 boolean
  - 📋 list
  - 📊 table_csv
  - 📄 report
  - 💬 short_answer
- **Added:** Tooltip showing:
  - Question
  - Output format
  - Status
  - Composition instructions (truncated)
- **Added:** Format badge on each node

**Styling (`RecursiveGraphTree.css`):**
- New `.format-badge` class with light blue background

### 6. Updated Component: StepViewer (`StepViewer.jsx`)

**New Renderers:**

**`renderDAGGeneration()`** - Phase 1 Display
- Total nodes, max depth, leaf nodes
- Breakdown by output format type
- Root question

**`renderDAGProcessed()`** - Phase 2 Display
- Nodes completed vs total
- Processing time
- Individual node results with:
  - Question
  - Format badge
  - Answer (with markdown rendering)
  - Citation count

**`renderThreePhaseFinalReport()`** - Phase 3 Display
- Report statistics (length, citations)
- Report outline
- Final report with full markdown rendering

**Styling (`StepViewer.css`):**
- `.format-breakdown` - Grid layout for format counts
- `.node-result-card` - Card styling for individual node results
- `.node-format-badge` - Badge styling for output formats
- `.outline-content` - Styled container for report outlines

### 7. Updated Component: RunDetail (`RunDetail.jsx`)

**Changes:**
- **Added:** Import for `PhaseProgress` component
- **Added:** State for `phaseData` and `phaseLoading`
- **Added:** `loadPhaseData()` function to fetch phase status
- **Updated:** Polling to include phase data updates
- **Integrated:** `PhaseProgress` component in summary panel
  - Shows only for three-phase runs (`is_three_phase`)
  - Auto-updates during pipeline execution

### 8. Updated API Client (`api.js`)

**New Function:**
```javascript
async fetchPhaseStatus(runId)
```
- Fetches phase status from `/api/runs/{run_id}/phases`
- Returns phase information and metrics

## Data Flow

1. **Pipeline Execution:**
   - New pipeline saves phase-specific JSON files
   - Each phase file includes metadata (nodes, depth, citations, etc.)

2. **Backend Scanner:**
   - Detects presence of phase files
   - Determines current phase and completed phases
   - Includes phase info in run metadata

3. **API Layer:**
   - Serves phase status through dedicated endpoint
   - Includes phase info in run status responses

4. **Frontend Display:**
   - Fetches phase data on load and during polling
   - PhaseProgress component visualizes pipeline progress
   - StepViewer renders phase-specific data
   - RecursiveGraphTree shows enhanced node information

## Backward Compatibility

- Legacy runs without phase files are detected automatically
- `is_three_phase` flag controls visibility of phase-specific UI
- Old step names (01_purpose_generation, etc.) still supported
- Graceful handling of missing phase data

## Key Features

1. **Real-time Updates:**
   - Phase progress updates during pipeline execution
   - Live metrics displayed for each phase
   - WebSocket support for instant updates

2. **Enhanced Visualization:**
   - Clear visual distinction between phases
   - Output format icons for better understanding
   - Composition instructions in node tooltips

3. **Comprehensive Metrics:**
   - Phase-specific statistics
   - Node-level result display
   - Citation tracking throughout pipeline

4. **Improved UX:**
   - Clear progress indication
   - Detailed phase breakdowns
   - Mobile-responsive design

## Testing

All components tested for:
- ✅ No linter errors
- ✅ TypeScript/JSX syntax correctness
- ✅ Proper prop passing
- ✅ Responsive design
- ✅ Backward compatibility with legacy runs

## Files Modified

**Backend:**
- `dashboard/backend/models.py`
- `dashboard/backend/scanner.py`
- `dashboard/backend/api.py`

**Frontend:**
- `dashboard/frontend/src/components/PhaseProgress.jsx` (new)
- `dashboard/frontend/src/components/PhaseProgress.css` (new)
- `dashboard/frontend/src/components/RecursiveGraphTree.jsx`
- `dashboard/frontend/src/components/RecursiveGraphTree.css`
- `dashboard/frontend/src/components/StepViewer.jsx`
- `dashboard/frontend/src/components/StepViewer.css`
- `dashboard/frontend/src/components/RunDetail.jsx`
- `dashboard/frontend/src/api.js`

## Next Steps

To use the updated dashboard:

1. **Start Backend:**
   ```bash
   cd dashboard/backend
   uvicorn api:app --reload
   ```

2. **Start Frontend:**
   ```bash
   cd dashboard/frontend
   npm install  # if not already installed
   npm run dev
   ```

3. **Run Pipeline:**
   ```bash
   cd src/presearcher
   python main.py
   ```

4. **View Dashboard:**
   Open `http://localhost:5173` in your browser

The dashboard will automatically detect three-phase runs and display the new phase progress visualization!

## Summary

Successfully implemented comprehensive dashboard support for the three-phase research pipeline. The dashboard now provides:

- Clear visualization of pipeline phases
- Enhanced node information with output formats
- Phase-specific metrics and progress tracking
- Real-time updates during execution
- Full backward compatibility with legacy runs

All implementation requirements from the plan have been completed! 🎉

