# Max Subtasks (Beams) Control Feature

## Overview

Added user control for the maximum number of **subtasks (beams)** per parent node in the recursive research tree. This parameter controls how many child nodes can be generated when a parent node is decomposed into subtasks.

**Parameter Name**: `max_subtasks`
**Default Value**: 10
**Range**: 1-20 (frontend limits)

## What Changed

### ✅ Backend Changes

#### 1. **Data Model** (`src/utils/dataclass.py`)
- Added `max_subtasks: int = 10` field to `PresearcherAgentRequest` dataclass
- Documentation: "Maximum number of subtasks (child nodes) to generate per parent node."

#### 2. **Core Pipeline** (`src/presearcher/presearcher.py`)
- Changed hardcoded `max_subtasks=10` to use `request.max_subtasks`
- Added `max_subtasks` to run configuration logging (saved to `00_run_config.json`)

#### 3. **CLI Interface** (`src/presearcher/main.py`)
- Added interactive prompt for `max_subtasks` parameter
- Includes it in pipeline configuration logging
- Default: 10

```python
max_subtasks = int(input(f"Max subtasks per node (default {max_subtasks}): ").strip() or max_subtasks)
```

#### 4. **Dashboard Backend**

**Models** (`dashboard/backend/models.py`):
- Added `max_subtasks: Optional[int] = None` to `RunMetadata`
- Added `max_subtasks: int = 10` to `StartRunRequest`

**Scanner** (`dashboard/backend/scanner.py`):
- Parses `max_subtasks` from `00_run_config.json`
- Includes it in `RunMetadata` construction

**API** (`dashboard/backend/api.py`):
- Passes `max_subtasks` from request to runner

**Runner** (`dashboard/backend/runner.py`):
- Accepts `max_subtasks` parameter in `start_run()` method
- Stores it in active run info
- Passes it to `PresearcherAgentRequest`
- Logs it in pipeline configuration

### ✅ Frontend Changes

#### 1. **New Run Form** (`dashboard/frontend/src/components/NewRunForm.jsx`)
- Added `maxSubtasks` state variable (default: 10)
- Added new input field:
  - **Label**: "Max Subtasks per Node"
  - **Type**: Number
  - **Range**: 1-20
  - **Help Text**: "Maximum number of child nodes (beams) to generate per parent node (1-20)."
- Passes `maxSubtasks` to API call

#### 2. **API Client** (`dashboard/frontend/src/api.js`)
- Updated `startRun()` function signature to accept `maxSubtasks` parameter
- Includes `max_subtasks` in request body

#### 3. **Run Detail View** (`dashboard/frontend/src/components/RunDetail.jsx`)
- Displays `max_subtasks` in run header metadata
- Displays `max_subtasks` in run summary grid

## Files Modified

### Backend (Python)
1. `src/utils/dataclass.py` - Added field to dataclass
2. `src/presearcher/presearcher.py` - Use dynamic value, log to config
3. `src/presearcher/main.py` - CLI prompt for parameter
4. `dashboard/backend/models.py` - API models
5. `dashboard/backend/scanner.py` - Parse from logs
6. `dashboard/backend/api.py` - Pass to runner
7. `dashboard/backend/runner.py` - Accept and use parameter

### Frontend (JavaScript/React)
8. `dashboard/frontend/src/components/NewRunForm.jsx` - Form input
9. `dashboard/frontend/src/api.js` - API call update
10. `dashboard/frontend/src/components/RunDetail.jsx` - Display in UI

## How It Works

### Pipeline Flow

```
User Input (CLI or Dashboard Form)
    ↓
max_subtasks = 10 (default)
    ↓
PresearcherAgentRequest(max_subtasks=10)
    ↓
PresearcherAgent.aforward()
    ↓
Saved to 00_run_config.json
    ↓
For each node exploration:
    ↓
SubtaskGenerationAgent.aforward(max_subtasks=request.max_subtasks)
    ↓
Generates up to max_subtasks child nodes per parent
```

### Example: Impact on Tree Structure

**max_subtasks = 3**:
```
Root
├── Child 1
├── Child 2
└── Child 3
```

**max_subtasks = 10**:
```
Root
├── Child 1
├── Child 2
├── Child 3
├── Child 4
├── Child 5
├── Child 6
├── Child 7
├── Child 8
├── Child 9
└── Child 10
```

## Usage Examples

### 1. CLI (Interactive Mode)

```bash
$ python -m presearcher.main

Please enter your research task or topic: What are the best practices in machine learning?
Would you like to configure advanced parameters? (y/N): y
Max retriever calls (default 1): 1
Max depth (default 2): 2
Max nodes (default 50): 50
Max subtasks per node (default 10): 5  ← User sets to 5
```

### 2. Dashboard Form

1. Navigate to "Start New Run"
2. Enter research topic
3. Scroll to "Max Subtasks per Node"
4. Set value (1-20)
5. Click "Start Pipeline"

### 3. Programmatic (Python)

```python
from presearcher.init_pipeline import init_presearcher_agent
from utils.dataclass import PresearcherAgentRequest

agent = init_presearcher_agent()
response = await agent.aforward(
    PresearcherAgentRequest(
        topic="AI safety research",
        max_subtasks=5,  # Control beam width
        max_depth=2,
        max_nodes=20
    )
)
```

## Benefits

1. **Breadth Control**: Users can control how many alternative paths are explored per node
2. **Resource Management**: Lower values reduce computational cost
3. **Depth vs Breadth Trade-off**: Balance between exploring many options (high max_subtasks) vs going deeper (high max_depth)
4. **Experimentation**: Users can test different beam widths to optimize results

## Trade-offs

| Setting | Pros | Cons |
|---------|------|------|
| **Low (1-3)** | Focused exploration, lower cost | May miss important alternative angles |
| **Medium (5-10)** | Balanced breadth and depth | Moderate resource usage |
| **High (15-20)** | Comprehensive coverage | High computational cost, may hit max_nodes limit quickly |

## Configuration Strategy

**For focused research** (specific question):
- `max_subtasks = 3-5`
- `max_depth = 3`
- `max_nodes = 30`

**For exploratory research** (broad topic):
- `max_subtasks = 8-12`
- `max_depth = 2`
- `max_nodes = 100`

**For quick testing**:
- `max_subtasks = 2`
- `max_depth = 1`
- `max_nodes = 10`

## Testing

✅ No linting errors
✅ All files compile successfully
✅ Parameter flows through entire stack:
  - CLI ✓
  - Dashboard Form ✓
  - Backend API ✓
  - Runner ✓
  - Pipeline ✓
  - Subtask Generation ✓

## Visual Changes

### Dashboard Form (Before)
```
[Research Topic Input]
[Max Retriever Calls: 1]
[Max Recursion Depth: 2]
[Max DAG Nodes: 50]
[Start Pipeline Button]
```

### Dashboard Form (After)
```
[Research Topic Input]
[Max Retriever Calls: 1]
[Max Recursion Depth: 2]
[Max DAG Nodes: 50]
[Max Subtasks per Node: 10]  ← NEW!
[Start Pipeline Button]
```

### Run Detail View
Now displays in metadata:
```
Max Retriever Calls: 1
Max Depth: 2
Max Nodes: 50
Max Subtasks: 10  ← NEW!
```

## Backward Compatibility

✅ **Fully backward compatible**
- Default value of 10 matches previous hardcoded value
- Old runs without this parameter will still display correctly (shows nothing if missing)
- No breaking changes to existing APIs

## Future Enhancements

Potential improvements:
1. **Adaptive beams**: Dynamically adjust based on answerability
2. **Per-depth control**: Different max_subtasks for each depth level
3. **Analytics**: Track correlation between max_subtasks and result quality
4. **Recommendations**: Suggest optimal max_subtasks based on topic complexity

