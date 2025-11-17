# Dashboard Updates - Display Both Literature Writeup and Final Report

## Overview

Modified the dashboard to display **both** the initial literature writeup and the final report for each research node, making it clear when each is generated in the pipeline.

## Changes Made

### 1. Updated Frontend Component (`RunDetail.jsx`)

#### Before
- Only displayed `literature_writeup` with a generic "Literature Writeup" heading
- No display of the `report` field

#### After
- **Literature Writeup Section** (lines 382-394)
  - Clear heading: "Literature Writeup (Before Subtasks)"
  - Added explanatory description: "Initial research synthesis from literature search, generated before decomposing into subtasks."
  - Shows the `literature_writeup` field

- **Final Report Section** (lines 407-420)
  - New heading: "Final Report (After Subtasks Complete)"
  - Added explanatory description: "Polished, structured report synthesized after all child nodes completed exploration. Includes key insights, thesis, and comprehensive findings."
  - Shows the `report` field

### 2. Updated CSS Styling (`RunDetail.css`)

Added styling for `.section-description` class (lines 338-348):
```css
.section-description {
  margin: 0 0 1rem 0;
  font-size: 0.8rem;
  color: #6b7280;
  line-height: 1.5;
  font-style: italic;
  padding: 0.5rem 0.75rem;
  background: #ffffff;
  border-left: 3px solid #3b82f6;
  border-radius: 4px;
}
```

This provides a visually distinct, italicized description box with a blue left border.

## Visual Layout in Dashboard

When you click on a node in the graph, the sidebar now displays sections in this order:

1. **Question** - The research question/topic
2. **Metadata** - Status, depth, answerability
3. **Literature Writeup (Before Subtasks)** ⬅️ *NEW LABEL + DESCRIPTION*
   - Generated immediately after literature search
   - Before subtask generation
4. **Subtasks** - List of generated subtasks (if any)
5. **Final Report (After Subtasks Complete)** ⬅️ *NEW SECTION*
   - Generated after all child nodes complete
   - Includes key insights, thesis, comprehensive synthesis
6. **Children Nodes** - Links to child nodes

## Data Fields in ResearchNode

From `src/utils/dataclass.py`:

```python
@dataclass
class ResearchNode:
    # ... other fields ...
    
    # Results attached to this node
    literature_writeup: str | None = None  # Generated BEFORE subtasks
    report: str | None = None              # Generated AFTER subtasks complete
    cited_documents: list[RetrievedDocument] = field(default_factory=list)
```

## Pipeline Timeline Per Node

```
_explore_node() execution:
    
    1. Literature Search
       ↓
       node.literature_writeup = "..." ← Dashboard shows in "Before Subtasks" section
       
    2. Is Answerable Check
    
    3. Generate Subtasks (if not answerable)
    
    4. Recursively explore child nodes
       [ALL CHILDREN COMPLETE]
       
    5. Generate Final Report
       ↓
       node.report = "..." ← Dashboard shows in "After Subtasks Complete" section
```

## Example Data

See `/output/logs/20251116_222120/recursive_graph.json` for a real example where `node_1` has both:
- `literature_writeup`: Initial synthesis about AI arms race (focusing on raw data)
- `report`: Final polished report with strategic narrative and thesis

## Testing

To test the changes:

1. **Start the dashboard backend:**
   ```bash
   cd dashboard
   python -m backend.api
   ```

2. **Start the frontend:**
   ```bash
   cd dashboard/frontend
   npm run dev
   ```

3. **View an existing run:**
   - Navigate to http://localhost:5173
   - Click on run `20251116_222120`
   - Click on the root node (`node_1`) in the graph
   - Verify you see both sections with descriptions

## Files Modified

1. `/Users/justin/Documents/GitHub/cs224v/224v-final-project/dashboard/frontend/src/components/RunDetail.jsx`
   - Added explanatory text to literature writeup section
   - Added new final report section
   
2. `/Users/justin/Documents/GitHub/cs224v/224v-final-project/dashboard/frontend/src/components/RunDetail.css`
   - Added `.section-description` styling

## No Breaking Changes

✅ All existing functionality preserved
✅ No backend changes required (fields already exist)
✅ No linting errors
✅ Backward compatible with existing data

## Benefits

1. **Clarity**: Users can now see both research outputs and understand when each was generated
2. **Debugging**: Easier to compare initial vs. final reports to understand the synthesis process
3. **Transparency**: Clear labeling shows the pipeline progression
4. **Educational**: Helps users understand the recursive research process

