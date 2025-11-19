# Three-Phase Pipeline Dashboard Guide

## What's New?

The dashboard now supports the new three-phase research pipeline architecture with enhanced visualizations and real-time phase tracking.

## New Features Overview

### 1. Phase Progress Visualization

**Location:** Run Detail page, below run summary

**What it shows:**
```
🗺️ Phase 1          ⚙️ Phase 2           📄 Phase 3
DAG Generation  →  DAG Processing  →  Report Generation
   [✓ Complete]      [⏳ In Progress]     [○ Pending]
```

**Live Metrics:**
- **Phase 1:** Total nodes, max depth reached, leaf nodes
- **Phase 2:** Nodes completed out of total
- **Phase 3:** Citations count, report length

### 2. Enhanced Graph Nodes

**New Node Information:**
- **Output Format Badges:** Each node shows its expected output type
  - 🔲 `boolean` - Yes/no answers
  - 📋 `list` - List of items
  - 📊 `table_csv` - Structured data tables
  - 📄 `report` - Full text reports
  - 💬 `short_answer` - Brief text responses

- **Tooltips:** Hover over any node to see:
  - Full question text
  - Expected output format
  - Current status
  - Composition instructions (for parent nodes)

### 3. Phase-Specific Step Views

#### Phase 1: DAG Generation View
Shows the planning phase results:
```
Generation Summary
├── Total Nodes: 15
├── Max Depth: 3
└── Leaf Nodes: 8

Node Breakdown by Format
├── boolean: 4 nodes
├── list: 3 nodes
├── table_csv: 2 nodes
└── report: 6 nodes
```

#### Phase 2: DAG Processing View
Shows execution details:
```
Processing Summary
├── Nodes Completed: 12 / 15
└── Processing Time: 45.3s

Node Results
┌─────────────────────────────────────┐
│ Question: "What are the benefits?"  │
│ Format: list                        │
│ Answer: - Benefit 1                 │
│         - Benefit 2                 │
│ Citations: 📚 5                     │
└─────────────────────────────────────┘
```

#### Phase 3: Final Report View
Shows completed research:
```
Report Statistics
├── Report Length: 5,247 characters
└── Citations: 23

Report Outline
[Markdown outline display]

Final Report
[Full markdown report with formatting]
```

## Using the Dashboard

### Starting the Dashboard

1. **Terminal 1 - Start Backend:**
   ```bash
   cd dashboard/backend
   uvicorn api:app --reload
   ```

2. **Terminal 2 - Start Frontend:**
   ```bash
   cd dashboard/frontend
   npm run dev
   ```

3. **Open Browser:**
   ```
   http://localhost:5173
   ```

### Viewing a Three-Phase Run

1. **Start a new research pipeline:**
   ```bash
   cd src/presearcher
   python main.py
   ```

2. **Dashboard automatically:**
   - Detects the new run
   - Shows phase progress indicator
   - Updates in real-time (5-second polling)

3. **Navigate to run details:**
   - Click on any run from the list
   - See phase progress at the top
   - Explore the graph with enhanced nodes
   - View phase-specific step data

### Real-Time Features

**During Pipeline Execution:**
- ⏱️ Live timer updates every second
- 🔄 Phase progress updates every 5 seconds
- 🌳 Graph updates with new nodes
- 📊 Metrics refresh automatically

**Phase Transitions:**
- Progress bar advances automatically
- Current phase highlighted in blue
- Completed phases show green checkmark
- Pending phases show gray indicator

## Visual Layout

```
┌─────────────────────────────────────────────────────┐
│ Run Detail: "Research Topic"                       │
│ Status: Running    Duration: 2m 15s                │
├─────────────────────────────────────────────────────┤
│ Run Summary                                         │
│ • Topic, Status, Created, Duration                  │
│ • Max Depth, Max Nodes, Max Retriever Calls        │
├─────────────────────────────────────────────────────┤
│ Phase Progress (NEW!)                               │
│ [Phase 1 ✓] → [Phase 2 ⏳] → [Phase 3 ○]          │
│ Nodes: 15  │  Completed: 8/15  │  Citations: -    │
├─────────────────────────────────────────────────────┤
│ Research Graph                                      │
│                  [Root Node]                        │
│                  📄 report                          │
│                  ↙        ↘                         │
│         [Child 1]        [Child 2]                  │
│         📋 list          🔲 boolean                 │
├─────────────────────────────────────────────────────┤
│ Pipeline Steps                                      │
│ ✓ 00_dag_generation     - DAG Generation           │
│ ⏳ 01_dag_processed      - DAG Processing (current) │
│ ○ 02_final_report       - Final Report             │
├─────────────────────────────────────────────────────┤
│ Selected Step View                                  │
│ [Phase-specific content display]                    │
└─────────────────────────────────────────────────────┘
```

## Comparing Legacy vs Three-Phase Runs

### Legacy Runs
- Show traditional 5-step pipeline
- Steps: Purpose → Outline → Search → Report → Final
- No phase progress indicator
- Standard node display

### Three-Phase Runs (NEW!)
- Show 3-phase architecture
- Phases: DAG Gen → Processing → Report
- **Phase progress bar visible**
- **Enhanced nodes with format badges**
- **Phase-specific step views**

**Dashboard automatically detects run type!**

## Key Differences in Display

### Node Display

**Legacy:**
```
┌─────────────────┐
│ Question...     │
│ Depth: 2        │
│ • Answerable    │
└─────────────────┘
```

**Three-Phase:**
```
┌─────────────────┐
│ Question...     │
│ Depth: 2        │
│ 📋 list         │
└─────────────────┘
```

### Step Views

**Legacy:**
- Purpose Generation
- Outline Generation
- Literature Search
- Report Generation
- Final Report

**Three-Phase:**
- **DAG Generation** (with format breakdown)
- **DAG Processing** (with node results)
- **Final Report** (with outline + report)

## Troubleshooting

### Phase Progress Not Showing
- **Check:** Is this a three-phase run?
- **Solution:** Only new runs created with the three-phase pipeline show phase progress

### Nodes Missing Format Badges
- **Check:** Is this a legacy run?
- **Solution:** Format badges only appear on three-phase runs with `expected_output_format` field

### Phase Data Not Updating
- **Check:** Is polling working?
- **Solution:** Refresh the page, check backend logs for errors

## API Endpoints

New endpoints available:

```
GET /api/runs/{run_id}/phases
→ Returns phase status and metrics

GET /api/runs/{run_id}/status
→ Now includes is_three_phase and phase info

GET /api/runs/{run_id}/graph
→ Graph nodes now include expected_output_format
```

## Tips for Best Experience

1. **Keep Dashboard Open:** Real-time updates work best with dashboard open
2. **Use Latest Runs:** Three-phase features only work with new pipeline runs
3. **Check Phase Progress:** Quick overview of pipeline execution state
4. **Explore Nodes:** Hover for detailed information
5. **View Step Data:** Click steps to see phase-specific breakdowns

## Example Workflow

1. **Start Pipeline:**
   ```bash
   python src/presearcher/main.py
   ```

2. **Watch Dashboard:**
   - Phase 1 completes: ✓ DAG Generated (15 nodes)
   - Phase 2 starts: ⏳ Processing nodes...
   - Phase 2 progress: 5/15 → 10/15 → 15/15
   - Phase 3 starts: ⏳ Generating report...
   - Phase 3 completes: ✓ Report ready!

3. **Explore Results:**
   - View graph with all nodes colored green
   - Read phase 2 step to see individual answers
   - Read phase 3 step for final report
   - Check citations and metrics

## Summary

The three-phase dashboard provides:

✅ **Clear Phase Visualization** - Know exactly where pipeline is
✅ **Enhanced Node Information** - See output formats at a glance
✅ **Real-Time Progress** - Watch execution unfold
✅ **Detailed Phase Views** - Dive deep into each phase
✅ **Backward Compatible** - Legacy runs still work perfectly

**Enjoy exploring your research with the enhanced dashboard!** 🚀

